#!/usr/bin/env bash
# generate-lockfile.sh — produce package-lock.json for reproducible CI builds.
#
# Why: the Dockerfile now falls back to `npm install` if no lockfile exists,
# which works but isn't strictly reproducible. For best CI hygiene, run this
# once locally, commit the resulting package-lock.json, and switch the
# Dockerfile back to `npm ci`.
#
# Usage:
#   bash scripts/generate-lockfile.sh
#   git add package-lock.json
#   git commit -m "chore: add package-lock.json for reproducible builds"
#
# Optional: bump all deps to latest within their semver range first:
#   npm update
#   bash scripts/generate-lockfile.sh

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f package.json ]]; then
  echo "ERROR: package.json not found in $(pwd)" >&2
  exit 1
fi

echo ">>> installing with npm@$(npm -v)"
npm install --package-lock-only --no-audit --no-fund

echo
echo ">>> done. verify:"
ls -la package-lock.json
echo
echo "Next:"
echo "  git add package-lock.json"
echo "  git commit -m 'chore: add package-lock.json'"
echo "  # (optional) edit Dockerfile: 'npm install' → 'npm ci'"
