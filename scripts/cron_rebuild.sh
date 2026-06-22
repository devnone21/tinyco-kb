#!/usr/bin/env bash
# cron_rebuild.sh — Host-side cron-driven rebuild.
# Detects changes in src/content/ and triggers rebuild.sh only when needed.
#
# Install (on the LXC host, as root):
#   chmod +x /opt/kb-site/scripts/cron_rebuild.sh
#   cat > /etc/cron.d/kb-rebuild <<'EOF'
#   */5 * * * * root /opt/kb-site/scripts/cron_rebuild.sh >> /var/log/kb-rebuild.log 2>&1
#   EOF
#
set -euo pipefail

SITE_DIR="${KB_SITE_DIR:-/opt/kb-site}"
STATE_DIR="${KB_STATE_DIR:-/var/lib/kb-site}"
CONTENT_DIR="$SITE_DIR/src/content"
MARKER="$STATE_DIR/last-mtime"
LOG="$STATE_DIR/rebuild.log"

mkdir -p "$STATE_DIR"

if [[ ! -d "$CONTENT_DIR" ]]; then
  echo "[$(date -Iseconds)] content dir missing: $CONTENT_DIR" >> "$LOG"
  exit 0
fi

# Find newest mtime under content/ (any depth, .md/.mdx files)
current=$(find "$CONTENT_DIR" -type f \( -name '*.md' -o -name '*.mdx' \) -printf '%T@\n' \
          | sort -nr | head -1 || echo 0)

previous=$(cat "$MARKER" 2>/dev/null || echo 0)

# Compare with tiny epsilon (float precision)
if awk -v a="$current" -v b="$previous" 'BEGIN{exit !(a>b)}'; then
  echo "[$(date -Iseconds)] change detected (mtime $previous → $current) — rebuilding" >> "$LOG"
  echo "$current" > "$MARKER"
  bash "$SITE_DIR/rebuild.sh" >> "$LOG" 2>&1
else
  echo "[$(date -Iseconds)] no change (mtime $current) — skip" >> "$LOG"
fi
