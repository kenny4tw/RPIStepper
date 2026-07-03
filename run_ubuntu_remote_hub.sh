#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 http://<rpi-ip>:5055/stepper"
  exit 1
fi

cd "$(dirname "$0")"

if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

export API_ONLY_MODE=false
export COMMAND_FILE_WATCH_ENABLED=false
export STEPPER_REMOTE_URL="$1"

python3 dashboard_server.py
