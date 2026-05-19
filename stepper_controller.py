"""
RPIStepper - Adafruit Motor HAT (PCA9685/TB6612) Stepper Controller for Raspberry Pi

Controls a single stepper motor via Adafruit Motor HAT (I2C) with dual limit switch monitoring.
"""

import time
import threading
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
    ACCEL_RAMP_ENABLED,
    ACCEL_RAMP_STEPS,
    ACCEL_START_FACTOR,
    ENABLE_LIMIT_SWITCHES,
    AUTO_STOP_AT_LIMIT
)

_STYLE_MAP = {
    'SINGLE': stepper.SINGLE,
    'DOUBLE': stepper.DOUBLE,
    'INTERLEAVE': stepper.INTERLEAVE,
    'MICROSTEP': stepper.MICROSTEP
}

_STYLE_FACTOR = {
    'SINGLE': 1,
    'DOUBLE': 1,
    'INTERLEAVE': 2,
    'MICROSTEP': 8,
}

class StepperController:
    """Controls a stepper motor with Adafruit Motor HAT and optional limit switch support."""

    def __init__(self):
        self.kit = MotorKit()
        self.motor = self.kit.stepper1 if MOTOR_PORT == 1 else self.kit.stepper2
        self.speed_rpm = MOTOR_SPEED_RPM
        self.motor.rpm = self.speed_rpm
        self.style_name = MOTOR_STYLE.upper()
        self.current_position = 0
        self.is_moving = False
        self.stop_requested = False
        self._state_lock = threading.Lock()
        self._setup_limit_switches()

    def _current_style(self):
        with self._state_lock:
            return _STYLE_MAP.get(self.style_name, stepper.INTERLEAVE)

    def _current_style_factor(self):
        with self._state_lock:
            return _STYLE_FACTOR.get(self.style_name, 1)

    def set_speed(self, rpm):
        rpm = int(rpm)
        if rpm <= 0:
            raise ValueError("RPM must be greater than 0")
        with self._state_lock:
            self.speed_rpm = rpm
            self.motor.rpm = rpm

    def set_style(self, style):
        name = str(style).upper()
        if name not in _STYLE_MAP:
            raise ValueError("Style must be SINGLE, DOUBLE, INTERLEAVE, or MICROSTEP")
        with self._state_lock:
            self.style_name = name

    def _step_delay_seconds(self):
        # Effective step frequency from configured RPM and stepping mode.
        with self._state_lock:
            factor = _STYLE_FACTOR.get(self.style_name, 1)
            speed_rpm = self.speed_rpm
        steps_per_second = (MOTOR_STEPS_PER_REV * speed_rpm / 60.0) * factor
        if steps_per_second <= 0:
            return 0.005
        # Clamp to avoid unrealistically small delays on slower boards.
        return max(0.0005, 1.0 / steps_per_second)

    def _ramped_delay_seconds(self, index, total_steps):
        base_delay = self._step_delay_seconds()
        if not ACCEL_RAMP_ENABLED or total_steps <= 2:
            return base_delay

        style_factor = self._current_style_factor()
        ramp_steps = max(1, int(ACCEL_RAMP_STEPS * style_factor))
        ramp_steps = min(ramp_steps, total_steps // 2)
        if ramp_steps <= 0:
            return base_delay

        start_factor = max(1.0, float(ACCEL_START_FACTOR))

        # Acceleration phase
        if index < ramp_steps:
            t = index / ramp_steps
            mult = start_factor - (start_factor - 1.0) * t
            return base_delay * mult

        # Deceleration phase
        if index >= total_steps - ramp_steps:
            t = (total_steps - 1 - index) / ramp_steps
            mult = start_factor - (start_factor - 1.0) * t
            return base_delay * mult

        # Cruise phase
        return base_delay

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
        style_factor = self._current_style_factor()
        total_steps = max(0, int(steps)) * style_factor
        if total_steps <= 0:
            return True
        delta_per_driver_step = 1.0 / style_factor
        print(f"[MOVE] Moving forward {steps} full-steps ({total_steps} driver-steps)...")
        self.stop_requested = False
        self.is_moving = True
        try:
            for i in range(total_steps):
                if self.stop_requested:
                    print("[MOVE] Stop requested")
                    break
                if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT and self.limit_switch_2_pressed():
                    print("[LIMIT] Limit switch 2 triggered - stopping motor")
                    break
                style = self._current_style()
                step_delay = self._ramped_delay_seconds(i, total_steps)
                self.motor.onestep(direction=stepper.FORWARD, style=style)
                self.current_position += delta_per_driver_step
                time.sleep(step_delay)
        finally:
            self.is_moving = False
            self.release()
        return True

    def move_backward(self, steps):
        """Move stepper backward by specified number of steps."""
        style_factor = self._current_style_factor()
        total_steps = max(0, int(steps)) * style_factor
        if total_steps <= 0:
            return True
        delta_per_driver_step = 1.0 / style_factor
        print(f"[MOVE] Moving backward {steps} full-steps ({total_steps} driver-steps)...")
        self.stop_requested = False
        self.is_moving = True
        try:
            for i in range(total_steps):
                if self.stop_requested:
                    print("[MOVE] Stop requested")
                    break
                if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT and self.limit_switch_1_pressed():
                    print("[LIMIT] Limit switch 1 triggered - stopping motor")
                    break
                style = self._current_style()
                step_delay = self._ramped_delay_seconds(i, total_steps)
                self.motor.onestep(direction=stepper.BACKWARD, style=style)
                self.current_position -= delta_per_driver_step
                time.sleep(step_delay)
        finally:
            self.is_moving = False
            self.release()
        return True

    def stop(self):
        self.stop_requested = True
        self.is_moving = False
        self.release()
        print("[MOVE] Motor stopped")

    def home(self, max_steps=2000):
        """Move to home position using limit switch 1 (left/bottom)."""
        print("[HOME] Homing to limit switch 1...")
        style_factor = self._current_style_factor()
        total_steps = max(1, int(max_steps)) * style_factor
        self.stop_requested = False
        steps = 0
        self.is_moving = True
        try:
            while steps < total_steps:
                if self.stop_requested:
                    print("[HOME] Stop requested")
                    break
                if self.limit_switch_1_pressed():
                    print("[HOME] Home position reached")
                    self.current_position = 0
                    return True
                style = self._current_style()
                step_delay = self._ramped_delay_seconds(steps, total_steps)
                self.motor.onestep(direction=stepper.BACKWARD, style=style)
                self.current_position -= 1.0 / style_factor
                time.sleep(step_delay)
                steps += 1
        finally:
            self.is_moving = False
            self.release()
        print("[HOME] Home position search failed - limit not found")
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
        with self._state_lock:
            speed_rpm = self.speed_rpm
            style_name = self.style_name
        return {
            "position": round(self.current_position, 3),
            "limit_switch_1": self.limit_switch_1_pressed(),
            "limit_switch_2": self.limit_switch_2_pressed(),
            "moving": self.is_moving,
            "speed_rpm": speed_rpm,
            "style": style_name
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
