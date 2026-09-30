#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="/etc/default/itops"
APPLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=true ;;
    --env-file) ENV_FILE="$2"; shift ;;
    *) echo "Option inconnue : $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Executer avec sudo pour lire ${ENV_FILE}." >&2
  exit 1
fi
if [[ ! -r "${ENV_FILE}" ]]; then
  echo "Fichier d'environnement introuvable ou illisible : ${ENV_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"
for variable in NMP_MARIADB_HOST NMP_MARIADB_PORT NMP_MARIADB_USER NMP_MARIADB_PASSWORD NMP_MARIADB_DATABASE; do
  if [[ -z "${!variable:-}" ]]; then
    echo "Variable MariaDB absente du fichier d'environnement : ${variable}" >&2
    exit 1
  fi
done

MARIADB_CLIENT="${NMP_MARIADB_BIN_DIR:-/usr/bin}/mariadb"
if [[ ! -x "${MARIADB_CLIENT}" ]]; then
  MARIADB_CLIENT="${NMP_MARIADB_BIN_DIR:-/usr/bin}/mysql"
fi
if [[ ! -x "${MARIADB_CLIENT}" ]]; then
  echo "Client MariaDB introuvable dans ${NMP_MARIADB_BIN_DIR:-/usr/bin}." >&2
  exit 1
fi

MIGRATION_PATH="${APP_DIR}/deployment/sql/20260930_supprimer_relations_agents_copieurs.sql"
if [[ ! -r "${MIGRATION_PATH}" ]]; then
  echo "Migration introuvable : ${MIGRATION_PATH}" >&2
  exit 1
fi

MARIADB_ARGS=(
  "--host=${NMP_MARIADB_HOST}"
  "--port=${NMP_MARIADB_PORT}"
  "--user=${NMP_MARIADB_USER}"
  "--database=${NMP_MARIADB_DATABASE}"
  "--default-character-set=utf8mb4"
  "--batch"
  "--raw"
)

export MYSQL_PWD="${NMP_MARIADB_PASSWORD}"
trap 'unset MYSQL_PWD' EXIT

echo "Cible MariaDB : ${NMP_MARIADB_HOST}:${NMP_MARIADB_PORT} / ${NMP_MARIADB_DATABASE}"
echo "Relations historiques detectees :"
"${MARIADB_CLIENT}" "${MARIADB_ARGS[@]}" <<'SQL'
SELECT r.id, r.source_service_code, r.target_service_code, r.display_label, r.is_active,
       COUNT(l.id) AS link_count
FROM custom_service_relations r
LEFT JOIN custom_service_relation_links l ON l.relation_id = r.id
WHERE r.target_service_code = 'utilisateurs'
  AND r.source_service_code IN ('copieur', 'code_copieur')
  AND r.display_label = 'Agents'
GROUP BY r.id, r.source_service_code, r.target_service_code, r.display_label, r.is_active
ORDER BY r.id;
SQL

if [[ "${APPLY}" != true ]]; then
  echo "Aucune modification appliquee. Apres la sauvegarde complete ITops, relancer avec --apply."
  exit 0
fi

echo "Execution de la migration..."
"${MARIADB_CLIENT}" "${MARIADB_ARGS[@]}" < "${MIGRATION_PATH}"
echo "Migration terminee."
