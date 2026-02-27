#!/usr/bin/env bash
set -euo pipefail

REMOTE="${DEPLOY_HOST:-macmini.lan}"
REMOTE_DIR="~/tesla-powerwall-exporter"

echo "Deploying to ${REMOTE}..."

rsync -av \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='.env' \
  --exclude='data' \
  ./ "${REMOTE}:${REMOTE_DIR}/"

ssh "${REMOTE}" "cd ${REMOTE_DIR} && docker compose up --build -d"

echo "Deployed. Waiting for container to start..."
sleep 3
ssh "${REMOTE}" "cd ${REMOTE_DIR} && docker compose ps"
