#!/usr/bin/env bash
set -euo pipefail

# Install a systemd timer to run the repo-ingest one-shot service on a schedule

SCHEDULE=${SCHEDULE:-daily}  # e.g., 'hourly', 'daily', 'weekly', or systemd calendar expression

sudo tee /etc/systemd/system/repo-ingest.timer >/dev/null <<TIMER
[Unit]
Description=Run repo-ingest service on a schedule

[Timer]
# Common presets: OnCalendar=daily | hourly | weekly; or "*-*-* 03:15:00"
OnCalendar=${SCHEDULE}
Persistent=true

[Install]
WantedBy=timers.target
TIMER

sudo systemctl daemon-reload
sudo systemctl enable --now repo-ingest.timer

echo "repo-ingest.timer enabled (OnCalendar=${SCHEDULE}). View: systemctl list-timers repo-ingest.timer"

