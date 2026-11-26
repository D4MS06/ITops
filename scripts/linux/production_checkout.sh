#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-${APP_DIR:-/opt/itops}}"

if ! git -C "${APP_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Depot Git introuvable dans ${APP_DIR}."
  exit 1
fi

if [ -n "$(git -C "${APP_DIR}" status --porcelain --untracked-files=no)" ]; then
  echo "Des fichiers suivis ont ete modifies. Extraction de production annulee."
  exit 1
fi

# Read the committed manifest before changing the checkout, including on a sparse clone.
PATTERNS="$(git -C "${APP_DIR}" show HEAD:scripts/linux/production.sparse-checkout)"
if [ -z "${PATTERNS}" ]; then
  echo "La liste des fichiers de production est vide."
  exit 1
fi

printf '%s\n' "${PATTERNS}" | git -C "${APP_DIR}" sparse-checkout set --no-cone --stdin
echo "Extraction de production activee dans ${APP_DIR}."
