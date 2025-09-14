#!/usr/bin/env bash
# Simple rsync rotated backup script.
# Usage: tools/backup_rsync.sh /source /mnt/backup drive_label

set -euo pipefail

SRC=${1:-}
DEST_ROOT=${2:-}
LABEL=${3:-backup}

if [[ -z "$SRC" || -z "$DEST_ROOT" ]]; then
  echo "Usage: $0 /source /mnt/backup label" >&2
  exit 2
fi

TIMESTAMP=$(date +%Y%m%d-%H%M)
DEST=${DEST_ROOT}/${LABEL}-${TIMESTAMP}

echo "Backing up $SRC -> $DEST"
mkdir -p "$DEST"
rsync -aAX --delete --exclude='node_modules' --exclude='.cache' "$SRC/" "$DEST/"
echo "Backup complete"
