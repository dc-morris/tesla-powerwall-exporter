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
  --exclude='data/refresh_token' \
  ./ "${REMOTE}:${REMOTE_DIR}/"

echo "Decrypting secrets..."
ssh "${REMOTE}" "cd ${REMOTE_DIR} \
  && SOPS_AGE_KEY_FILE=~/age-key.txt sops -d --input-type dotenv --output-type dotenv .env.enc > .env \
  && mkdir -p data \
  && SOPS_AGE_KEY_FILE=~/age-key.txt sops -d --input-type binary --output-type binary data/refresh_token.enc > data/refresh_token"

echo "Starting container..."
ssh "${REMOTE}" "cd ${REMOTE_DIR} && docker compose down && docker compose up --build -d"

sleep 3
ssh "${REMOTE}" "cd ${REMOTE_DIR} && docker compose ps"
