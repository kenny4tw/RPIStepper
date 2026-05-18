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
sudo apt-get install python3-pip
sudo apt-get install python3-gpiozero
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. GPIO Configuration

Edit `config.py` to match your HAT pinout:
- Stepper motor control pins (step, direction, enable)
- Limit switch input pins

### 4. Run the Program

```bash
python3 stepper_controller.py
```

## Usage

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

## Configuration

See `config.py` for GPIO pin mappings and stepper motor parameters.

## License

MIT
