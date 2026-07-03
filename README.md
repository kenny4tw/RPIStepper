# RPIStepper

A Raspberry Pi 3 B+ stepper motor controller for Adafruit Motor HAT (PID 2348) with dual limit switch support, JSON-file control, and a local dashboard.

Default runtime mode is tuned for smoother motion on Raspberry Pi:
- `API_ONLY_MODE=true`
- `COMMAND_FILE_WATCH_ENABLED=false`

## Hardware Requirements

- Raspberry Pi 3 B/B+
- Stepper Motor HAT (based on 2348 driver)
- 1x NEMA 17 or compatible stepper motor
- 2x Limit switches (normally open)
- 5V power supply

## Features

- Single stepper motor control on Motor HAT M1/M2 or M3/M4
- Dual limit switch monitoring
- JSON command-file control (`command.json`)
- Unified web dashboard hub with named paths (`/stepper`, `/radarsensor`, `/opta`)
- Real-time status display (position, limits, speed, style)

## Setup

### 1. Prerequisites

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv python3-lgpio
```

`python3-lgpio` must be installed via apt — it requires native build tools (`swig`) that are not available in a plain pip environment.

### 2. Clone Repository

```bash
git clone https://github.com/kenny4tw/RPIStepper.git
cd RPIStepper
```

### 3. Create Virtual Environment

Create the venv with `--system-site-packages` so it can access `lgpio` installed by apt:

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

Note: Uses `rpi-lgpio` as a drop-in replacement for `RPi.GPIO`, compatible with Python 3.13. The underlying `lgpio` library is provided by the system package installed in step 1.

### 5. GPIO Configuration

Edit `config.py` to match your HAT pinout:
- Stepper motor control pins (step, direction, enable)
- Limit switch input pins

### 6. Run the Program

```bash
python3 dashboard_server.py
```

Then open:

```text
http://localhost:5055
```

Dashboard paths:

```text
http://<host>:5055/stepper
http://<host>:5055/radarsensor
http://<host>:5055/opta
```

Set upstream URLs for embedded RadarSensor/Opta dashboards with environment variables:

```bash
export RADAR_DASHBOARD_URL="http://127.0.0.1:5060"
export OPTA_DASHBOARD_URL="http://127.0.0.1:5070"
```

To control a stepper connected to a different machine (for example RPi from Ubuntu hub), set:

```bash
export STEPPER_REMOTE_URL="http://<rpi-ip>:5055/stepper"
```

Then all `/stepper` commands on the current server are forwarded to that remote RPi API.

### 7. (Optional) Run on Boot

See [Setup as Systemd Service](#setup-as-systemd-service) below.

### 8. Performance Tuning (Adafruit Motor HAT)

For smoother/faster motion with this HAT, apply these in order:

1. Set I2C bus to 400kHz (Fast Mode)
2. Use realistic per-style step-rate caps in `config.py`
3. Reduce safety polling overhead (`SAFETY_CHECK_EVERY_DRIVER_STEPS`)

Enable I2C 400kHz manually:

```bash
sudo sed -i 's/^dtparam=i2c_arm_baudrate=.*/dtparam=i2c_arm_baudrate=400000/' /boot/firmware/config.txt || \
echo 'dtparam=i2c_arm_baudrate=400000' | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

After reboot, run:

```bash
cd ~/RPIStepper
source venv/bin/activate
python3 dashboard_server.py
```

## Setup as Systemd Service

To run RPIStepper automatically on boot:

```bash
# Update service file paths
sudo nano /etc/systemd/system/rpistepper.service
```

Update these lines to match your venv path:
```ini
ExecStart=/home/pi/RPIStepper/venv/bin/python3 /home/pi/RPIStepper/dashboard_server.py
Environment="PATH=/home/pi/RPIStepper/venv/bin"
```

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rpistepper.service
sudo systemctl start rpistepper.service
```

## Usage

### Dashboard Control

Run server:

```bash
python3 dashboard_server.py
```

Open dashboard in browser:

```text
http://localhost:5055/stepper
```

Hub page (all dashboards):

```text
http://localhost:5055/
```

### Run Ubuntu Hub + RPi Stepper Backend

RPi machine (with Motor HAT connected):

```bash
cd ~/RPIStepper
source venv/bin/activate
export API_ONLY_MODE=true
export COMMAND_FILE_WATCH_ENABLED=false
python3 dashboard_server.py
```

Ubuntu machine (main dashboard UI):

```bash
cd ~/Documents/RPIStepper
source venv/bin/activate
export STEPPER_REMOTE_URL="http://<rpi-ip>:5055/stepper"
python3 dashboard_server.py
```

Or use helper scripts:

RPi:

```bash
./run_rpi_api_only.sh
```

Ubuntu:

```bash
./run_ubuntu_remote_hub.sh http://<rpi-ip>:5055/stepper
```

Open on Ubuntu:

```text
http://<ubuntu-ip>:5055/stepper
```

In API-only mode on RPi:
- UI routes (`/`, `/stepper`, `/radarsensor`, `/opta`) are disabled
- API routes remain available (`/api/*`, `/stepper/api/*`)
- Local command-file watcher can be disabled for lower overhead

### JSON File Control

The server watches `command.json` continuously. Write a new command with a new `id` value each time.

Note: For lowest jitter on Raspberry Pi, prefer HTTP API control and keep
`COMMAND_FILE_WATCH_ENABLED=false`.

Example commands:

```json
{
	"id": 101,
	"command": "move_forward",
	"steps": 400
}
```

```json
{
	"id": 102,
	"command": "move_backward",
	"steps": 200
}
```

```json
{
	"id": 103,
	"command": "set_speed",
	"rpm": 80
}
```

```json
{
	"id": 104,
	"command": "set_style",
	"style": "MICROSTEP"
}
```

```json
{
	"id": 105,
	"command": "home",
	"max_steps": 3000
}
```

### API Control

Status:

```bash
curl http://localhost:5055/stepper/api/status
```

Command:

```bash
curl -X POST http://localhost:5055/stepper/api/command \
	-H "Content-Type: application/json" \
	-d '{"command":"move_forward","steps":200}'
```

This is the recommended control path for low-overhead operation.

### Monitoring Stop Causes On RPi

Lightweight monitoring workflow:

1. Start RPIStepper on the Pi in API-only mode.
2. Run live service logs to capture stop reasons and scheduler jitter warnings:

```bash
./monitor_rpi_motion.sh
```

3. In another terminal, watch process and system pressure while moving:

```bash
PID=$(pgrep -f dashboard_server.py | head -n 1)
top -H -p "$PID"
```

```bash
pidstat -t -p "$PID" 1
```

```bash
vmstat 1
```

```bash
vcgencmd get_throttled
vcgencmd measure_temp
```

New runtime diagnostics are also exposed by `GET /stepper/api/status` in:
- `diagnostics.jitter`
- `diagnostics.last_move`

## Fast + Smooth Checklist (Motor HAT)

For best practical motion quality with this architecture:

1. Run RPi in API-only mode (`API_ONLY_MODE=true`, `COMMAND_FILE_WATCH_ENABLED=false`)
2. Set I2C to 400kHz (`dtparam=i2c_arm_baudrate=400000`, reboot required)
3. Keep realistic style-specific caps in `config.py`
4. Keep `HOLD_POSITION_BETWEEN_MOVES=True` for repeated command stability
5. Use `DOUBLE` for stronger torque and lower effective step-rate than `INTERLEAVE`/`MICROSTEP`
6. Tune `MAX_DRIVER_STEPS_PER_SEC_DOUBLE` upward in small steps (for example +50 each pass)
7. Use solid motor supply and shared ground with RPi (power issues look like random jerk/missed steps)

If you need significantly faster smooth motion than this can provide, move to a step/dir driver with hardware-timed pulses.

### Remote JSON Control (LabVIEW cRIO)

1. In `/stepper` dashboard, enable switch: **Remote JSON Control (LabVIEW/cRIO)**
2. Send commands to remote endpoint:

```bash
curl -X POST http://localhost:5055/stepper/api/remote-command \
	-H "Content-Type: application/json" \
	-d '{"command":"move_forward","steps":200}'
```

If the switch is off, remote commands are rejected with HTTP 403.

### Python Controller Usage

Make sure your virtual environment is activated:

```bash
source venv/bin/activate
```

Then run:

```python
from stepper_controller import StepperController

controller = StepperController()
controller.move_forward(steps=100)
controller.move_backward(steps=50)
controller.stop()

# Check limit switches
print(controller.limit_switch_1_pressed())
print(controller.limit_switch_2_pressed())
```

Or run examples:

```bash
python3 example.py basic      # Basic movement
python3 example.py limit      # Limit switch test
python3 example.py home       # Homing sequence
python3 example.py continuous # Continuous operation
```

## Configuration

See `config.py` for GPIO pin mappings and stepper motor parameters.

Important for Adafruit Motor HAT 2348:
- `MOTOR_PORT = 1` uses M1+M2
- `MOTOR_PORT = 2` uses M3+M4

Performance-related settings in `config.py`:
- `MIN_STEP_DELAY_SEC`
- `MAX_DRIVER_STEPS_PER_SEC_SINGLE`
- `MAX_DRIVER_STEPS_PER_SEC_DOUBLE`
- `MAX_DRIVER_STEPS_PER_SEC_INTERLEAVE`
- `MAX_DRIVER_STEPS_PER_SEC_MICROSTEP`
- `SAFETY_CHECK_EVERY_DRIVER_STEPS`
- `PERFORMANCE_PROFILE_DEFAULT`

Optional A/B test backend in `config.py`:
- `USE_LEGACY_MOTORHAT_STEP`

When enabled, movement commands use legacy `step(numsteps, direction, style)` calls from
`Adafruit_MotorHAT` (if installed). This can be useful for comparing motion feel.

Install legacy package for testing:

```bash
source venv/bin/activate
pip install Adafruit-MotorHAT
```

Limitations of legacy step backend:
- No mid-move stop or limit switch checks during a blocking `step(...)` call
- If `AUTO_STOP_AT_LIMIT=True`, controller falls back to scheduler path automatically

Runtime performance profile command:

```bash
curl -X POST http://localhost:5055/stepper/api/command \
	-H "Content-Type: application/json" \
	-d '{"command":"set_performance_profile","profile":"balanced"}'
```

Valid profiles: `safe`, `balanced`, `aggressive`.

The Ubuntu dashboard includes this profile selector in the stepper control row.

## Troubleshooting

If dependency install fails for GPIO libraries:

```bash
# Install the system GPIO library first (required)
sudo apt-get update
sudo apt-get install -y python3-lgpio

# Recreate venv with system site-packages access
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## License

MIT
