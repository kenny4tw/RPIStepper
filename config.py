"""
Configuration for Adafruit DC & Stepper Motor HAT (PCA9685/TB6612) on Raspberry Pi
"""

# Limit Switch Input Pins (BCM numbering)
LIMIT_SWITCH_1_PIN = 23    # GPIO23 - End limit switch (left/bottom)
LIMIT_SWITCH_2_PIN = 24    # GPIO24 - End limit switch (right/top)

# Stepper Motor Parameters
MOTOR_PORT = 1             # 1 = M1+M2, 2 = M3+M4
MOTOR_STEPS_PER_REV = 200  # Standard NEMA 17: 1.8° per step = 200 steps/rev
MOTOR_STYLE = 'INTERLEAVE' # 'SINGLE', 'DOUBLE', 'INTERLEAVE', or 'MICROSTEP'
MOTOR_SPEED_RPM = 60       # Target speed in RPM

# Motion smoothing
ACCEL_RAMP_ENABLED = True   # Apply linear acceleration/deceleration ramp
ACCEL_RAMP_STEPS = 40       # Ramp length in full motor steps (not microsteps)
ACCEL_START_FACTOR = 2.5    # Start/end delay multiplier vs cruise speed

# Control Modes
ENABLE_LIMIT_SWITCHES = True
AUTO_STOP_AT_LIMIT = True  # Stop motor when limit switch is pressed
