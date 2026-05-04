#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Ce script doit etre execute en root."
  exit 1
fi

REPO_URL="${REPO_URL:-https://github.com/D4MS06/ITops.git}"
BRANCH="${BRANCH:-pre-release/0.9}"
APP_DIR="${APP_DIR:-/opt/itops}"
APP_USER="${APP_USER:-root}"
APP_GROUP="${APP_GROUP:-root}"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8080}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-itops}"
DB_PASSWORD="${DB_PASSWORD:-ChangeMoiFort!}"
DB_NAME="${DB_NAME:-itops}"
REVERSE_PROXY_TYPE="${REVERSE_PROXY_TYPE:-aucun}"
PUBLIC_URL="${PUBLIC_URL:-}"

CONFIG_DIR="/etc/itops"
LOG_DIR="/var/log/itops"
DATA_DIR="/var/lib/itops"
ENV_FILE="/etc/default/itops"
SETUP_STATE_FILE="${CONFIG_DIR}/setup_installation.json"
SETUP_TOKEN_FILE="${CONFIG_DIR}/setup.token"
HEBERGEMENT_CONFIG_FILE="${CONFIG_DIR}/hebergement_web.json"
SERVICE_FILE="/etc/systemd/system/itops.service"

echo "[1/8] Installation des prerequis systeme"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3 python3-venv python3-pip mariadb-server curl caddy nginx openssl
systemctl enable --now mariadb
systemctl disable --now nginx caddy >/dev/null 2>&1 || true

echo "[2/8] Preparation des dossiers"
mkdir -p "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}" /opt
chmod 750 "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}"

echo "[3/8] Recuperation du code"
if [ -d "${APP_DIR}/.git" ]; then
  git -C "${APP_DIR}" fetch --all --prune
  git -C "${APP_DIR}" checkout "${BRANCH}"
  git -C "${APP_DIR}" pull --ff-only origin "${BRANCH}"
else
  git clone "${REPO_URL}" "${APP_DIR}"
  git -C "${APP_DIR}" checkout "${BRANCH}"
fi

echo "[4/8] Installation Python"
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "[5/8] Configuration MariaDB"
mysql -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'${DB_HOST}' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'${DB_HOST}' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'${DB_HOST}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

echo "[6/8] Ecriture des fichiers de configuration"
SETUP_TOKEN="$("${APP_DIR}/.venv/bin/python" - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
printf "%s\n" "${SETUP_TOKEN}" > "${SETUP_TOKEN_FILE}"
chmod 600 "${SETUP_TOKEN_FILE}"
cat > "${SETUP_STATE_FILE}" <<JSON
{
  "completed": false,
  "completed_at": "",
  "completed_by": "",
  "reverse_proxy_type": "",
  "public_url": ""
}
JSON
chmod 640 "${SETUP_STATE_FILE}"

cat > "${HEBERGEMENT_CONFIG_FILE}" <<JSON
{
  "hote_ecoute": "${APP_HOST}",
  "port_ecoute": ${APP_PORT},
  "demarrage_auto_service": true,
  "utiliser_url_publique_reverse_proxy": $( [ -n "${PUBLIC_URL}" ] && echo "true" || echo "false" ),
  "url_publique": "${PUBLIC_URL}",
  "reverse_proxy_actif": $( [ "${REVERSE_PROXY_TYPE}" = "aucun" ] && echo "false" || echo "true" ),
  "reverse_proxy_type": "${REVERSE_PROXY_TYPE}"
}
JSON
chmod 640 "${HEBERGEMENT_CONFIG_FILE}"

cat > "${ENV_FILE}" <<EOF
NMP_DB_BACKEND='mariadb'
NMP_MARIADB_HOST='${DB_HOST}'
NMP_MARIADB_PORT='${DB_PORT}'
NMP_MARIADB_USER='${DB_USER}'
NMP_MARIADB_PASSWORD='${DB_PASSWORD}'
NMP_MARIADB_DATABASE='${DB_NAME}'
NMP_HEBERGEMENT_CONFIG='${HEBERGEMENT_CONFIG_FILE}'
NMP_SETUP_CONFIG='${SETUP_STATE_FILE}'
NMP_SETUP_TOKEN_FILE='${SETUP_TOKEN_FILE}'
NMP_INSTALL_ENV_PATH='${ENV_FILE}'
EOF
chmod 600 "${ENV_FILE}"

echo "[7/8] Installation service systemd"
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=ITops Web Service
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStartPre=/bin/sh -c 'if [ -f "${SETUP_STATE_FILE}" ] && grep -q "\"completed\"[[:space:]]*:[[:space:]]*true" "${SETUP_STATE_FILE}"; then for i in $$(seq 1 30); do mysqladmin ping -h"$${NMP_MARIADB_HOST:-127.0.0.1}" -P"$${NMP_MARIADB_PORT:-3306}" --silent >/dev/null 2>&1 && break; sleep 1; done; mysql -h"$${NMP_MARIADB_HOST:-127.0.0.1}" -P"$${NMP_MARIADB_PORT:-3306}" -u"$${NMP_MARIADB_USER:-itops}" --password="$${NMP_MARIADB_PASSWORD:-}" -D"$${NMP_MARIADB_DATABASE:-itops}" -e "SELECT 1" >/dev/null; fi'
ExecStart=${APP_DIR}/.venv/bin/python main.py --mode server --host ${APP_HOST} --port ${APP_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "[8/8] Activation du service"
systemctl daemon-reload
systemctl enable --now itops
sleep 1
if ! systemctl is-active --quiet itops; then
  echo "Le service itops n'est pas actif apres installation."
  systemctl --no-pager --full status itops || true
  journalctl -u itops -n 120 --no-pager || true
  exit 1
fi
systemctl --no-pager --full status itops

IP_CANDIDATE="$(hostname -I | awk '{print $1}')"
echo ""
echo "Installation technique terminee."
echo "Wizard web: http://${IP_CANDIDATE}:${APP_PORT}/setup"
echo "Token setup : ${SETUP_TOKEN}"
echo "Apres finalisation wizard, redemarre: systemctl restart itops"
