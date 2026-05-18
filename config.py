"""
GPIO Configuration for RPIStepper HAT on Raspberry Pi 3 B/B+

Adjust these pin numbers according to your HAT pinout.
Using BCM (Broadcom) GPIO numbering.
"""

# Stepper Motor Control Pins (adjust to your HAT)
STEPPER_STEP_PIN = 17      # GPIO17 - Step signal
STEPPER_DIR_PIN = 27       # GPIO27 - Direction signal (HIGH=forward, LOW=backward)
STEPPER_ENABLE_PIN = 22    # GPIO22 - Enable/Disable motor

# Limit Switch Input Pins
LIMIT_SWITCH_1_PIN = 23    # GPIO23 - End limit switch (left/bottom)
LIMIT_SWITCH_2_PIN = 24    # GPIO24 - End limit switch (right/top)

# Stepper Motor Parameters
STEP_DELAY = 0.001         # Delay between steps in seconds (1000 µs = 1ms)
MICROSTEP_MODE = 1         # 1=full step, 2=half step, 4=quarter step, 8=eighth step
MOTOR_SPEED_RPM = 60       # Target speed in RPM

# Stepper Motor Specifications
STEPS_PER_REVOLUTION = 200 # Standard NEMA 17: 1.8° per step = 200 steps/rev
MICROSTEPS_PER_STEP = MICROSTEP_MODE

# Control Modes
ENABLE_LIMIT_SWITCHES = True
AUTO_STOP_AT_LIMIT = True  # Stop motor when limit switch is pressed
