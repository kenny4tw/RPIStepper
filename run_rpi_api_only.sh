#!/bin/bash
set -e

# Run the stepper host on Raspberry Pi with minimum background load.
cd "$(dirname "$0")"

if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

export API_ONLY_MODE=true
export COMMAND_FILE_WATCH_ENABLED=false
unset STEPPER_REMOTE_URL

python3 dashboard_server.py
