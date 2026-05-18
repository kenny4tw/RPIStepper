# RPIStepper

A Raspberry Pi 3 B+ stepper motor controller for Adafruit Motor HAT (PID 2348) with dual limit switch support, JSON-file control, and a local dashboard.

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

### 7. (Optional) Run on Boot

See [Setup as Systemd Service](#setup-as-systemd-service) below.

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

### JSON File Control

The server watches `command.json` continuously. Write a new command with a new `id` value each time.

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
