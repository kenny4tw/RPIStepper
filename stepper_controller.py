"""
RPIStepper - Stepper Motor Controller for Raspberry Pi 3 B/B+

Controls a single stepper motor via HAT interface with dual limit switch monitoring.
"""

import time
import RPi.GPIO as GPIO
from config import (
    STEPPER_STEP_PIN,
    STEPPER_DIR_PIN,
    STEPPER_ENABLE_PIN,
    LIMIT_SWITCH_1_PIN,
    LIMIT_SWITCH_2_PIN,
    STEP_DELAY,
    STEPS_PER_REVOLUTION,
    ENABLE_LIMIT_SWITCHES,
    AUTO_STOP_AT_LIMIT
)


class StepperController:
    """Controls a stepper motor with optional limit switch support."""

    def __init__(self):
        """Initialize GPIO and stepper motor control."""
        self.setup_gpio()
        self.is_moving = False
        self.current_position = 0

    def setup_gpio(self):
        """Configure GPIO pins for stepper motor and limit switches."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Setup stepper motor output pins
        GPIO.setup(STEPPER_STEP_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(STEPPER_DIR_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(STEPPER_ENABLE_PIN, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = disabled

        # Setup limit switch input pins
        if ENABLE_LIMIT_SWITCHES:
            GPIO.setup(LIMIT_SWITCH_1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(LIMIT_SWITCH_2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        print("[GPIO] Stepper motor controller initialized")

    def enable_motor(self):
        """Enable the stepper motor."""
        GPIO.output(STEPPER_ENABLE_PIN, GPIO.LOW)  # LOW = enabled
        print("[MOTOR] Motor enabled")

    def disable_motor(self):
        """Disable the stepper motor."""
        GPIO.output(STEPPER_ENABLE_PIN, GPIO.HIGH)  # HIGH = disabled
        self.is_moving = False
        print("[MOTOR] Motor disabled")

    def set_direction(self, forward=True):
        """Set motor direction.
        
        Args:
            forward (bool): True for forward, False for backward
        """
        direction = GPIO.HIGH if forward else GPIO.LOW
        GPIO.output(STEPPER_DIR_PIN, direction)

    def step(self, num_steps=1, delay=None):
        """Execute motor steps.
        
        Args:
            num_steps (int): Number of steps to execute
            delay (float): Delay between steps in seconds (uses STEP_DELAY if None)
        """
        if delay is None:
            delay = STEP_DELAY

        self.enable_motor()

        for i in range(num_steps):
            # Check limit switches if enabled
            if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT:
                if self.limit_switch_1_pressed() or self.limit_switch_2_pressed():
                    print("[LIMIT] Limit switch triggered - stopping motor")
                    self.disable_motor()
                    return False

            # Execute step pulse
            GPIO.output(STEPPER_STEP_PIN, GPIO.HIGH)
            time.sleep(delay / 2)
            GPIO.output(STEPPER_STEP_PIN, GPIO.LOW)
            time.sleep(delay / 2)

        return True

    def move_forward(self, steps):
        """Move stepper forward by specified number of steps.
        
        Args:
            steps (int): Number of steps to move forward
            
        Returns:
            bool: True if movement completed, False if limit switch triggered
        """
        print(f"[MOVE] Moving forward {steps} steps...")
        self.set_direction(forward=True)
        success = self.step(steps)
        self.current_position += steps if success else steps - 1
        return success

    def move_backward(self, steps):
        """Move stepper backward by specified number of steps.
        
        Args:
            steps (int): Number of steps to move backward
            
        Returns:
            bool: True if movement completed, False if limit switch triggered
        """
        print(f"[MOVE] Moving backward {steps} steps...")
        self.set_direction(forward=False)
        success = self.step(steps)
        self.current_position -= steps if success else steps - 1
        return success

    def stop(self):
        """Stop motor immediately."""
        self.disable_motor()
        print("[MOVE] Motor stopped")

    def home(self):
        """Move to home position using limit switch 1 (left/bottom)."""
        print("[HOME] Homing to limit switch 1...")
        self.set_direction(forward=False)
        self.enable_motor()

        max_steps = STEPS_PER_REVOLUTION * 10  # Safety limit: 10 revolutions
        steps = 0

        while steps < max_steps:
            if self.limit_switch_1_pressed():
                print("[HOME] Home position reached")
                self.disable_motor()
                self.current_position = 0
                return True

            GPIO.output(STEPPER_STEP_PIN, GPIO.HIGH)
            time.sleep(STEP_DELAY / 2)
            GPIO.output(STEPPER_STEP_PIN, GPIO.LOW)
            time.sleep(STEP_DELAY / 2)
            steps += 1

        print("[HOME] Home position search failed - limit not found")
        self.disable_motor()
        return False

    def limit_switch_1_pressed(self):
        """Check if limit switch 1 is pressed.
        
        Returns:
            bool: True if switch is pressed (LOW), False otherwise
        """
        if not ENABLE_LIMIT_SWITCHES:
            return False
        return GPIO.input(LIMIT_SWITCH_1_PIN) == GPIO.LOW

    def limit_switch_2_pressed(self):
        """Check if limit switch 2 is pressed.
        
        Returns:
            bool: True if switch is pressed (LOW), False otherwise
        """
        if not ENABLE_LIMIT_SWITCHES:
            return False
        return GPIO.input(LIMIT_SWITCH_2_PIN) == GPIO.LOW

    def get_status(self):
        """Get current motor status.
        
        Returns:
            dict: Status information
        """
        return {
            "position": self.current_position,
            "limit_switch_1": self.limit_switch_1_pressed(),
            "limit_switch_2": self.limit_switch_2_pressed(),
            "moving": self.is_moving
        }

    def cleanup(self):
        """Clean up GPIO resources."""
        print("[GPIO] Cleaning up...")
        GPIO.cleanup()


def main():
    """Demo program showing basic stepper control."""
    try:
        controller = StepperController()

        # Test 1: Simple forward and backward movement
        print("\n=== Test 1: Basic Movement ===")
        controller.move_forward(100)
        time.sleep(1)
        controller.move_backward(100)
        time.sleep(1)

        # Test 2: Check limit switches
        print("\n=== Test 2: Limit Switch Status ===")
        status = controller.get_status()
        print(f"Limit Switch 1: {status['limit_switch_1']}")
        print(f"Limit Switch 2: {status['limit_switch_2']}")

        # Test 3: Home movement (optional - uncomment if limit switches are wired)
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
