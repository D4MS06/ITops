#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Ce script doit etre execute en root."
  exit 1
fi

APP_DIR="${APP_DIR:-/opt/itops}"
BRANCH="${BRANCH:-pre-release/1.0}"
SERVICE_NAME="${SERVICE_NAME:-itops}"
STORAGE_HELPER="${STORAGE_HELPER:-/usr/local/sbin/itops-storage-helper}"
STORAGE_SUDOERS="${STORAGE_SUDOERS:-/etc/sudoers.d/itops-storage-helper}"
VISUDO_BIN="${VISUDO_BIN:-/usr/sbin/visudo}"

if [ ! -d "${APP_DIR}/.git" ]; then
  echo "Repository introuvable dans ${APP_DIR}"
  exit 1
fi

echo "[1/6] Mise a jour du code (${BRANCH})"
git -C "${APP_DIR}" fetch --all --prune
git -C "${APP_DIR}" checkout "${BRANCH}"
git -C "${APP_DIR}" pull --ff-only origin "${BRANCH}"

echo "[2/6] Mise a jour des prerequis et du helper stockage"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y cifs-utils
APP_USER="${APP_USER:-$(systemctl show "${SERVICE_NAME}" -p User --value 2>/dev/null || true)}"
APP_USER="${APP_USER:-root}"
if [ -z "${APP_USER}" ]; then
  APP_USER="root"
fi
if [ "${APP_USER}" != "root" ]; then
  apt-get install -y sudo
fi
install -o root -g root -m 0750 "${APP_DIR}/scripts/linux/itops_storage_helper.py" "${STORAGE_HELPER}"
if [ "${APP_USER}" != "root" ]; then
  cat > "${STORAGE_SUDOERS}" <<EOF
${APP_USER} ALL=(root) NOPASSWD: ${STORAGE_HELPER} *
EOF
  chmod 0440 "${STORAGE_SUDOERS}"
  "${VISUDO_BIN}" -cf "${STORAGE_SUDOERS}" >/dev/null
else
  rm -f "${STORAGE_SUDOERS}"
fi
mkdir -p /mnt/itops-storage /etc/itops/smb
chmod 0750 /mnt/itops-storage
chmod 0700 /etc/itops/smb
if [ -f /etc/default/itops ]; then
  if ! grep -q '^NMP_STORAGE_HELPER=' /etc/default/itops; then
    printf "NMP_STORAGE_HELPER='%s'\n" "${STORAGE_HELPER}" >> /etc/default/itops
  fi
  if ! grep -q '^NMP_APP_USER=' /etc/default/itops; then
    printf "NMP_APP_USER='%s'\n" "${APP_USER}" >> /etc/default/itops
  fi
fi

echo "[3/6] Mise a jour des dependances Python"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "[4/6] Redemarrage du service"
systemctl daemon-reload
systemctl restart "${SERVICE_NAME}"

echo "[5/6] Verification et logs"
systemctl --no-pager --full status "${SERVICE_NAME}" || true
journalctl -u "${SERVICE_NAME}" -n 80 --no-pager || true

echo "[6/6] Healthcheck"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:8080/health"; then
    echo ""
    exit 0
  fi
  sleep 1
done
echo "Healthcheck indisponible apres 30 secondes."
systemctl --no-pager --full status "${SERVICE_NAME}" || true
journalctl -u "${SERVICE_NAME}" -n 120 --no-pager || true
exit 1
