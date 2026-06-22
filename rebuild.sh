#!/usr/bin/env bash
# Rebuild & restart the KB site after content/scripts change.
# Usage:  ./rebuild.sh        (run from kb-site/ on the host)
set -euo pipefail

cd "$(dirname "$0")"

echo "[rebuild] pulling latest content..."
git pull --rebase --autostash || true

echo "[rebuild] building container..."
docker compose build --pull

echo "[rebuild] restarting..."
docker compose up -d

echo "[rebuild] cleaning dangling images..."
docker image prune -f >/dev/null

echo "[rebuild] done. Status:"
docker compose ps
