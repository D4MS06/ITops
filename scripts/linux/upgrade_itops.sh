#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Ce script doit etre execute en root."
  exit 1
fi

APP_DIR="${APP_DIR:-/opt/itops}"
BRANCH="${BRANCH:-pre-release/1.0}"
SERVICE_NAME="${SERVICE_NAME:-itops}"

if [ ! -d "${APP_DIR}/.git" ]; then
  echo "Repository introuvable dans ${APP_DIR}"
  exit 1
fi

echo "[1/5] Mise a jour du code (${BRANCH})"
git -C "${APP_DIR}" fetch --all --prune
git -C "${APP_DIR}" checkout "${BRANCH}"
git -C "${APP_DIR}" pull --ff-only origin "${BRANCH}"

echo "[2/5] Mise a jour des dependances Python"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "[3/5] Redemarrage du service"
systemctl daemon-reload
systemctl restart "${SERVICE_NAME}"

echo "[4/5] Verification et logs"
systemctl --no-pager --full status "${SERVICE_NAME}" || true
journalctl -u "${SERVICE_NAME}" -n 80 --no-pager || true

echo "[5/5] Healthcheck"
curl -fsS "http://127.0.0.1:8080/health" && echo ""
