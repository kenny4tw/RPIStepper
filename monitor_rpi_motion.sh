#!/bin/bash
set -e

# Lightweight monitoring for motion-stop root cause analysis on Raspberry Pi.
# Usage:
#   ./monitor_rpi_motion.sh
# Optional:
#   SERVICE=rpistepper.service ./monitor_rpi_motion.sh

SERVICE="${SERVICE:-rpistepper.service}"
PID="$(pgrep -f dashboard_server.py | head -n 1 || true)"

echo "Service: $SERVICE"
if [ -n "$PID" ]; then
  echo "Detected dashboard_server.py PID: $PID"
else
  echo "dashboard_server.py PID not found yet (service may still be starting)"
fi
echo

echo "=== Live service log (jitter + command traces) ==="
echo "Press Ctrl+C to stop"
if command -v stdbuf >/dev/null 2>&1; then
  journalctl -u "$SERVICE" -f -n 50 | stdbuf -oL cat
else
  journalctl -u "$SERVICE" -f -n 50
fi
