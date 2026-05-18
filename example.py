"""
Example usage of the RPIStepper controller.

This file demonstrates common operations with the stepper motor.
"""

import time
from stepper_controller import StepperController


def example_basic_movement():
    """Example: Basic forward/backward movement."""
    print("\n=== Example 1: Basic Movement ===\n")

    controller = StepperController()

    # Move forward 200 steps (one full revolution)
    print("Moving forward 200 steps...")
    controller.move_forward(200)

    time.sleep(2)

    # Move backward 100 steps (half revolution)
    print("Moving backward 100 steps...")
    controller.move_backward(100)

    controller.cleanup()


def example_limit_switches():
    """Example: Monitor and react to limit switches."""
    print("\n=== Example 2: Limit Switch Monitoring ===\n")

    controller = StepperController()

    # Check current limit switch status
    status = controller.get_status()
    print(f"Limit Switch 1 pressed: {status['limit_switch_1']}")
    print(f"Limit Switch 2 pressed: {status['limit_switch_2']}")

    # Move forward until limit switch 2 is hit (with auto-stop enabled)
    print("Moving forward until limit switch 2 is triggered...")
    controller.move_forward(1000)  # Large number, will stop at limit

    controller.cleanup()


def example_home_position():
    """Example: Find and move to home position."""
    print("\n=== Example 3: Homing ===\n")

    controller = StepperController()

    # Move to home position (using limit switch 1)
    print("Homing to limit switch 1...")
    if controller.home():
        print("Successfully homed!")
    else:
        print("Failed to find home position")

    # Now move from home position
    print("Moving 100 steps from home...")
    controller.move_forward(100)

    controller.cleanup()


def example_continuous_operation():
    """Example: Continuous operation loop."""
    print("\n=== Example 4: Continuous Operation ===\n")

    controller = StepperController()

    try:
        for cycle in range(3):
            print(f"\n--- Cycle {cycle + 1} ---")

            # Forward movement
            print("Moving forward...")
            controller.move_forward(150)
            time.sleep(1)

            # Check status
            status = controller.get_status()
            print(f"Current position: {status['position']}")

            # Backward movement
            print("Moving backward...")
            controller.move_backward(150)
            time.sleep(1)

            status = controller.get_status()
            print(f"Current position: {status['position']}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example = sys.argv[1].lower()
        if example == "basic":
            example_basic_movement()
        elif example == "limit":
            example_limit_switches()
        elif example == "home":
            example_home_position()
        elif example == "continuous":
            example_continuous_operation()
        else:
            print(f"Unknown example: {example}")
            print("Available examples: basic, limit, home, continuous")
    else:
        print("Usage: python3 example.py [basic|limit|home|continuous]")
        print("\nRun one of the example functions:")
        print("  python3 example.py basic      - Basic forward/backward movement")
        print("  python3 example.py limit      - Limit switch monitoring")
        print("  python3 example.py home       - Homing to position")
        print("  python3 example.py continuous - Continuous operation loop")
