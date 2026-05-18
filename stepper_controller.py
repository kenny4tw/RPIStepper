"""
RPIStepper - Adafruit Motor HAT (PCA9685/TB6612) Stepper Controller for Raspberry Pi

Controls a single stepper motor via Adafruit Motor HAT (I2C) with dual limit switch monitoring.
"""

import time
import board
import digitalio
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
from config import (
    LIMIT_SWITCH_1_PIN,
    LIMIT_SWITCH_2_PIN,
    MOTOR_PORT,
    MOTOR_STEPS_PER_REV,
    MOTOR_STYLE,
    MOTOR_SPEED_RPM,
    ENABLE_LIMIT_SWITCHES,
    AUTO_STOP_AT_LIMIT
)

_STYLE_MAP = {
    'SINGLE': stepper.SINGLE,
    'DOUBLE': stepper.DOUBLE,
    'INTERLEAVE': stepper.INTERLEAVE,
    'MICROSTEP': stepper.MICROSTEP
}

class StepperController:
    """Controls a stepper motor with Adafruit Motor HAT and optional limit switch support."""

    def __init__(self):
        self.kit = MotorKit()
        self.motor = self.kit.stepper1 if MOTOR_PORT == 1 else self.kit.stepper2
        self.motor.rpm = MOTOR_SPEED_RPM
        self.current_position = 0
        self.is_moving = False
        self._setup_limit_switches()

    def _setup_limit_switches(self):
        if ENABLE_LIMIT_SWITCHES:
            self.limit1 = digitalio.DigitalInOut(getattr(board, f"D{LIMIT_SWITCH_1_PIN}"))
            self.limit1.direction = digitalio.Direction.INPUT
            self.limit1.pull = digitalio.Pull.UP
            self.limit2 = digitalio.DigitalInOut(getattr(board, f"D{LIMIT_SWITCH_2_PIN}"))
            self.limit2.direction = digitalio.Direction.INPUT
            self.limit2.pull = digitalio.Pull.UP
        else:
            self.limit1 = None
            self.limit2 = None

    def move_forward(self, steps):
        """Move stepper forward by specified number of steps."""
        print(f"[MOVE] Moving forward {steps} steps...")
        style = _STYLE_MAP.get(MOTOR_STYLE.upper(), stepper.INTERLEAVE)
        for i in range(steps):
            if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT and self.limit_switch_2_pressed():
                print("[LIMIT] Limit switch 2 triggered - stopping motor")
                break
            self.motor.onestep(direction=stepper.FORWARD, style=style)
            self.current_position += 1
            time.sleep(0.005)
        self.release()
        return True

    def move_backward(self, steps):
        """Move stepper backward by specified number of steps."""
        print(f"[MOVE] Moving backward {steps} steps...")
        style = _STYLE_MAP.get(MOTOR_STYLE.upper(), stepper.INTERLEAVE)
        for i in range(steps):
            if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT and self.limit_switch_1_pressed():
                print("[LIMIT] Limit switch 1 triggered - stopping motor")
                break
            self.motor.onestep(direction=stepper.BACKWARD, style=style)
            self.current_position -= 1
            time.sleep(0.005)
        self.release()
        return True

    def stop(self):
        self.release()
        print("[MOVE] Motor stopped")

    def home(self, max_steps=2000):
        """Move to home position using limit switch 1 (left/bottom)."""
        print("[HOME] Homing to limit switch 1...")
        style = _STYLE_MAP.get(MOTOR_STYLE.upper(), stepper.INTERLEAVE)
        steps = 0
        while steps < max_steps:
            if self.limit_switch_1_pressed():
                print("[HOME] Home position reached")
                self.current_position = 0
                self.release()
                return True
            self.motor.onestep(direction=stepper.BACKWARD, style=style)
            self.current_position -= 1
            time.sleep(0.005)
            steps += 1
        print("[HOME] Home position search failed - limit not found")
        self.release()
        return False

    def limit_switch_1_pressed(self):
        if not ENABLE_LIMIT_SWITCHES or self.limit1 is None:
            return False
        return not self.limit1.value  # Active LOW

    def limit_switch_2_pressed(self):
        if not ENABLE_LIMIT_SWITCHES or self.limit2 is None:
            return False
        return not self.limit2.value  # Active LOW

    def get_status(self):
        return {
            "position": self.current_position,
            "limit_switch_1": self.limit_switch_1_pressed(),
            "limit_switch_2": self.limit_switch_2_pressed(),
            "moving": self.is_moving
        }

    def release(self):
        self.motor.release()

    def cleanup(self):
        print("[GPIO] Cleaning up...")
        self.release()

def main():
    try:
        controller = StepperController()

        print("\n=== Test 1: Basic Movement ===")
        controller.move_forward(100)
        time.sleep(1)
        controller.move_backward(100)
        time.sleep(1)

        print("\n=== Test 2: Limit Switch Status ===")
        status = controller.get_status()
        print(f"Limit Switch 1: {status['limit_switch_1']}")
        print(f"Limit Switch 2: {status['limit_switch_2']}")

        # print("\n=== Test 3: Homing ===")
        # controller.home()

        print("\n=== Tests Complete ===")

    except KeyboardInterrupt:
        print("\n[USER] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        controller.cleanup()

if __name__ == "__main__":
    main()
