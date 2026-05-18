# RPIStepper

A Raspberry Pi 3 B+ stepper motor controller with dual limit switch support.

## Hardware Requirements

- Raspberry Pi 3 B/B+
- Stepper Motor HAT (based on 2348 driver)
- 1x NEMA 17 or compatible stepper motor
- 2x Limit switches (normally open)
- 5V power supply

## Features

- Single stepper motor control (forward/backward/stop)
- Dual limit switch monitoring
- GPIO-based control and sensing
- Real-time status display

## Setup

### 1. Prerequisites

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv
```

### 2. Clone Repository

```bash
git clone https://github.com/kenny4tw/RPIStepper.git
cd RPIStepper
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. GPIO Configuration

Edit `config.py` to match your HAT pinout:
- Stepper motor control pins (step, direction, enable)
- Limit switch input pins

### 6. Run the Program

```bash
python3 stepper_controller.py
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
ExecStart=/home/pi/RPIStepper/venv/bin/python3 /home/pi/RPIStepper/stepper_controller.py
Environment="PATH=/home/pi/RPIStepper/venv/bin"
```

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rpistepper.service
sudo systemctl start rpistepper.service
```

## Usage

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

## License

MIT
