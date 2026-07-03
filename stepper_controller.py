"""
RPIStepper - Adafruit Motor HAT (PCA9685/TB6612) Stepper Controller for Raspberry Pi

Controls a single stepper motor via Adafruit Motor HAT (I2C) with dual limit switch monitoring.
"""

import time
import threading
import os
import board
import digitalio
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
try:
    from Adafruit_MotorHAT import Adafruit_MotorHAT
except Exception:
    Adafruit_MotorHAT = None
import config as _cfg


def _cfg_value(name, default):
    return getattr(_cfg, name, default)


LIMIT_SWITCH_1_PIN = int(_cfg_value("LIMIT_SWITCH_1_PIN", 23))
LIMIT_SWITCH_2_PIN = int(_cfg_value("LIMIT_SWITCH_2_PIN", 24))
MOTOR_PORT = int(_cfg_value("MOTOR_PORT", 1))
MOTOR_STEPS_PER_REV = int(_cfg_value("MOTOR_STEPS_PER_REV", 200))
MOTOR_STYLE = str(_cfg_value("MOTOR_STYLE", "INTERLEAVE"))
MOTOR_SPEED_RPM = int(_cfg_value("MOTOR_SPEED_RPM", 30))

ACCEL_RAMP_ENABLED = bool(_cfg_value("ACCEL_RAMP_ENABLED", True))
ACCEL_RAMP_STEPS = int(_cfg_value("ACCEL_RAMP_STEPS", 80))
ACCEL_START_FACTOR = float(_cfg_value("ACCEL_START_FACTOR", 2.5))

MIN_STEP_DELAY_SEC = float(_cfg_value("MIN_STEP_DELAY_SEC", 0.0008))
MAX_DRIVER_STEPS_PER_SEC_SINGLE = int(_cfg_value("MAX_DRIVER_STEPS_PER_SEC_SINGLE", 900))
MAX_DRIVER_STEPS_PER_SEC_DOUBLE = int(_cfg_value("MAX_DRIVER_STEPS_PER_SEC_DOUBLE", 900))
MAX_DRIVER_STEPS_PER_SEC_INTERLEAVE = int(_cfg_value("MAX_DRIVER_STEPS_PER_SEC_INTERLEAVE", 1200))
MAX_DRIVER_STEPS_PER_SEC_MICROSTEP = int(_cfg_value("MAX_DRIVER_STEPS_PER_SEC_MICROSTEP", 2200))
SAFETY_CHECK_EVERY_DRIVER_STEPS = int(_cfg_value("SAFETY_CHECK_EVERY_DRIVER_STEPS", 8))

HOLD_POSITION_BETWEEN_MOVES = bool(_cfg_value("HOLD_POSITION_BETWEEN_MOVES", True))
USE_LEGACY_MOTORHAT_STEP = bool(_cfg_value("USE_LEGACY_MOTORHAT_STEP", False))
PERFORMANCE_PROFILE_DEFAULT = str(_cfg_value("PERFORMANCE_PROFILE_DEFAULT", "balanced"))

ENABLE_LIMIT_SWITCHES = bool(_cfg_value("ENABLE_LIMIT_SWITCHES", True))
AUTO_STOP_AT_LIMIT = bool(_cfg_value("AUTO_STOP_AT_LIMIT", False))

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

_STYLE_MAX_DRIVER_STEPS_PER_SEC = {
    'SINGLE': MAX_DRIVER_STEPS_PER_SEC_SINGLE,
    'DOUBLE': MAX_DRIVER_STEPS_PER_SEC_DOUBLE,
    'INTERLEAVE': MAX_DRIVER_STEPS_PER_SEC_INTERLEAVE,
    'MICROSTEP': MAX_DRIVER_STEPS_PER_SEC_MICROSTEP,
}

_LEGACY_STYLE_NAME = {
    'SINGLE': 'SINGLE',
    'DOUBLE': 'DOUBLE',
    'INTERLEAVE': 'INTERLEAVE',
    'MICROSTEP': 'MICROSTEP',
}

_PERFORMANCE_PROFILES = ("safe", "balanced", "aggressive")

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
        self._timing_clamped = False
        self._legacy_enabled = False
        self._legacy_hat = None
        self._legacy_stepper = None
        self.performance_profile = "balanced"
        self._profile_settings = self._build_profile_settings()
        self._state_lock = threading.Lock()
        self._jitter_warn_threshold_ms = max(0.5, float(os.getenv("STEPPER_JITTER_WARN_MS", "6.0")))
        self._jitter_warn_interval_sec = max(0.2, float(os.getenv("STEPPER_JITTER_WARN_INTERVAL_SEC", "2.0")))
        self._jitter_stats = self._new_jitter_stats()
        self._last_jitter_warning_at = 0.0
        self._active_motion_diag = None
        self._last_motion_diag = None
        self.set_performance_profile(PERFORMANCE_PROFILE_DEFAULT)
        self._setup_legacy_backend()
        self._setup_limit_switches()

    def _new_jitter_stats(self):
        return {
            "samples": 0,
            "late_samples": 0,
            "late_sum_ms": 0.0,
            "max_late_ms": 0.0,
            "warn_count": 0,
            "total_moves": 0,
        }

    def _start_motion_diagnostics(self, move_name, total_steps):
        with self._state_lock:
            self._active_motion_diag = {
                "move": str(move_name),
                "expected_steps": int(total_steps),
                "start_monotonic": time.monotonic(),
                "samples": 0,
                "late_samples": 0,
                "late_sum_ms": 0.0,
                "max_late_ms": 0.0,
                "warn_count": 0,
            }

    def _record_scheduler_jitter(self, scheduled_time, step_index, total_steps):
        now = time.monotonic()
        lateness_ms = max(0.0, (now - scheduled_time) * 1000.0)
        with self._state_lock:
            self._jitter_stats["samples"] += 1
            if self._active_motion_diag is not None:
                self._active_motion_diag["samples"] += 1

            if lateness_ms <= 0.0:
                return

            self._jitter_stats["late_samples"] += 1
            self._jitter_stats["late_sum_ms"] += lateness_ms
            self._jitter_stats["max_late_ms"] = max(self._jitter_stats["max_late_ms"], lateness_ms)

            if self._active_motion_diag is not None:
                self._active_motion_diag["late_samples"] += 1
                self._active_motion_diag["late_sum_ms"] += lateness_ms
                self._active_motion_diag["max_late_ms"] = max(self._active_motion_diag["max_late_ms"], lateness_ms)

            should_warn = lateness_ms >= self._jitter_warn_threshold_ms and (now - self._last_jitter_warning_at) >= self._jitter_warn_interval_sec
            if not should_warn:
                return

            self._last_jitter_warning_at = now
            self._jitter_stats["warn_count"] += 1
            if self._active_motion_diag is not None:
                self._active_motion_diag["warn_count"] += 1

        print(
            f"[JITTER] Scheduler late by {lateness_ms:.2f} ms at step {step_index + 1}/{total_steps}; "
            "Raspberry Pi may be CPU/IO busy"
        )

    def _finish_motion_diagnostics(self, completed_steps, reason):
        now = time.monotonic()
        with self._state_lock:
            if self._active_motion_diag is None:
                return

            active = self._active_motion_diag
            self._active_motion_diag = None
            self._jitter_stats["total_moves"] += 1

            late_samples = int(active["late_samples"])
            avg_late_ms = (active["late_sum_ms"] / late_samples) if late_samples > 0 else 0.0
            duration_sec = max(0.0, now - float(active["start_monotonic"]))
            summary = {
                "move": active["move"],
                "reason": str(reason),
                "expected_steps": int(active["expected_steps"]),
                "completed_steps": int(completed_steps),
                "duration_sec": round(duration_sec, 3),
                "late_samples": late_samples,
                "avg_late_ms": round(avg_late_ms, 3),
                "max_late_ms": round(float(active["max_late_ms"]), 3),
                "warn_count": int(active["warn_count"]),
                "timestamp": int(time.time()),
            }
            self._last_motion_diag = summary

        print(
            "[JITTER] Move summary: "
            f"move={summary['move']} reason={summary['reason']} completed={summary['completed_steps']}/{summary['expected_steps']} "
            f"duration={summary['duration_sec']:.3f}s max_late={summary['max_late_ms']:.2f}ms avg_late={summary['avg_late_ms']:.2f}ms "
            f"late_samples={summary['late_samples']} warnings={summary['warn_count']}"
        )

    def _build_profile_settings(self):
        safe_scale = 0.8
        aggressive_scale = 1.2
        return {
            "safe": {
                "style_max_steps_per_sec": {
                    "SINGLE": int(MAX_DRIVER_STEPS_PER_SEC_SINGLE * safe_scale),
                    "DOUBLE": int(MAX_DRIVER_STEPS_PER_SEC_DOUBLE * safe_scale),
                    "INTERLEAVE": int(MAX_DRIVER_STEPS_PER_SEC_INTERLEAVE * safe_scale),
                    "MICROSTEP": int(MAX_DRIVER_STEPS_PER_SEC_MICROSTEP * safe_scale),
                },
                "min_step_delay_sec": max(float(MIN_STEP_DELAY_SEC), 0.0012),
                "safety_check_every_driver_steps": max(1, int(SAFETY_CHECK_EVERY_DRIVER_STEPS // 2) or 1),
            },
            "balanced": {
                "style_max_steps_per_sec": {
                    "SINGLE": int(MAX_DRIVER_STEPS_PER_SEC_SINGLE),
                    "DOUBLE": int(MAX_DRIVER_STEPS_PER_SEC_DOUBLE),
                    "INTERLEAVE": int(MAX_DRIVER_STEPS_PER_SEC_INTERLEAVE),
                    "MICROSTEP": int(MAX_DRIVER_STEPS_PER_SEC_MICROSTEP),
                },
                "min_step_delay_sec": float(MIN_STEP_DELAY_SEC),
                "safety_check_every_driver_steps": max(1, int(SAFETY_CHECK_EVERY_DRIVER_STEPS)),
            },
            "aggressive": {
                "style_max_steps_per_sec": {
                    "SINGLE": int(MAX_DRIVER_STEPS_PER_SEC_SINGLE * aggressive_scale),
                    "DOUBLE": int(MAX_DRIVER_STEPS_PER_SEC_DOUBLE * aggressive_scale),
                    "INTERLEAVE": int(MAX_DRIVER_STEPS_PER_SEC_INTERLEAVE * aggressive_scale),
                    "MICROSTEP": int(MAX_DRIVER_STEPS_PER_SEC_MICROSTEP * aggressive_scale),
                },
                "min_step_delay_sec": max(0.0004, float(MIN_STEP_DELAY_SEC) * 0.75),
                "safety_check_every_driver_steps": max(1, int(SAFETY_CHECK_EVERY_DRIVER_STEPS * 2)),
            },
        }

    def set_performance_profile(self, profile):
        name = str(profile).strip().lower()
        if name not in _PERFORMANCE_PROFILES:
            allowed = ", ".join(_PERFORMANCE_PROFILES)
            raise ValueError(f"Performance profile must be one of: {allowed}")
        with self._state_lock:
            self.performance_profile = name

    def _current_profile_settings(self):
        with self._state_lock:
            profile_name = self.performance_profile
        return self._profile_settings.get(profile_name, self._profile_settings["balanced"])

    def _setup_legacy_backend(self):
        if not USE_LEGACY_MOTORHAT_STEP:
            return
        if Adafruit_MotorHAT is None:
            print("[LEGACY] USE_LEGACY_MOTORHAT_STEP=True but Adafruit_MotorHAT is not installed; using scheduler path")
            return
        try:
            self._legacy_hat = Adafruit_MotorHAT()
            self._legacy_stepper = self._legacy_hat.getStepper(MOTOR_STEPS_PER_REV, MOTOR_PORT)
            self._legacy_enabled = self._legacy_stepper is not None
            if self._legacy_enabled:
                print("[LEGACY] Enabled Adafruit_MotorHAT step(numsteps) backend")
        except Exception as exc:
            print(f"[LEGACY] Failed to initialize legacy backend ({exc}); using scheduler path")
            self._legacy_enabled = False
            self._legacy_hat = None
            self._legacy_stepper = None

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
            if self._legacy_enabled and self._legacy_stepper is not None:
                self._legacy_stepper.setSpeed(rpm)

    def set_style(self, style):
        name = str(style).upper()
        if name not in _STYLE_MAP:
            raise ValueError("Style must be SINGLE, DOUBLE, INTERLEAVE, or MICROSTEP")
        with self._state_lock:
            self.style_name = name

    def _step_delay_seconds(self):
        # Effective step frequency from configured RPM and stepping mode.
        with self._state_lock:
            style_name = self.style_name
            factor = _STYLE_FACTOR.get(style_name, 1)
            speed_rpm = self.speed_rpm
        steps_per_second = (MOTOR_STEPS_PER_REV * speed_rpm / 60.0) * factor
        if steps_per_second <= 0:
            return 0.005

        max_steps_per_second = float(_STYLE_MAX_DRIVER_STEPS_PER_SEC.get(style_name, MAX_DRIVER_STEPS_PER_SEC_SINGLE))
        effective_steps_per_second = min(steps_per_second, max_steps_per_second)

        if effective_steps_per_second < steps_per_second and not self._timing_clamped:
            effective_rpm = (effective_steps_per_second * 60.0) / (MOTOR_STEPS_PER_REV * factor)
            print(
                f"[TIMING] Requested {speed_rpm} RPM in {style_name} exceeds stable limit; "
                f"clamping to ~{effective_rpm:.1f} RPM"
            )
            self._timing_clamped = True
        elif effective_steps_per_second >= steps_per_second:
            self._timing_clamped = False

        # Keep a practical floor so the scheduler can remain stable on Raspberry Pi.
        return max(float(MIN_STEP_DELAY_SEC), 1.0 / effective_steps_per_second)

    def _base_delay_for_style(self, style_name, style_factor, speed_rpm):
        steps_per_second = (MOTOR_STEPS_PER_REV * speed_rpm / 60.0) * style_factor
        if steps_per_second <= 0:
            return 0.005

        profile = self._current_profile_settings()
        profile_limits = profile.get("style_max_steps_per_sec", {})
        max_steps_per_second = float(profile_limits.get(style_name, MAX_DRIVER_STEPS_PER_SEC_SINGLE))
        effective_steps_per_second = min(steps_per_second, max_steps_per_second)

        if effective_steps_per_second < steps_per_second and not self._timing_clamped:
            effective_rpm = (effective_steps_per_second * 60.0) / (MOTOR_STEPS_PER_REV * style_factor)
            print(
                f"[TIMING] Requested {speed_rpm} RPM in {style_name} exceeds stable limit; "
                f"clamping to ~{effective_rpm:.1f} RPM"
            )
            self._timing_clamped = True
        elif effective_steps_per_second >= steps_per_second:
            self._timing_clamped = False

        min_step_delay_sec = float(profile.get("min_step_delay_sec", MIN_STEP_DELAY_SEC))
        return max(min_step_delay_sec, 1.0 / effective_steps_per_second)

    def _timing_profile(self, total_steps, style_name, style_factor, speed_rpm):
        base_delay = self._base_delay_for_style(style_name, style_factor, speed_rpm)
        if not ACCEL_RAMP_ENABLED or total_steps <= 2:
            return base_delay, 0, 1.0

        ramp_steps = max(1, int(ACCEL_RAMP_STEPS * style_factor))
        ramp_steps = min(ramp_steps, total_steps // 2)
        if ramp_steps <= 0:
            return base_delay, 0, 1.0

        start_factor = max(1.0, float(ACCEL_START_FACTOR))
        return base_delay, ramp_steps, start_factor

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

    def _ramped_delay_from_profile(self, index, total_steps, base_delay, ramp_steps, start_factor):
        if ramp_steps <= 0:
            return base_delay

        if index < ramp_steps:
            t = index / ramp_steps
            mult = start_factor - (start_factor - 1.0) * t
            return base_delay * mult

        if index >= total_steps - ramp_steps:
            t = (total_steps - 1 - index) / ramp_steps
            mult = start_factor - (start_factor - 1.0) * t
            return base_delay * mult

        return base_delay

    def _safety_check_due(self, step_index, check_interval):
        return step_index == 0 or (step_index % check_interval == 0)

    def _finalize_motion(self, keep_holding=True):
        self.is_moving = False
        if not keep_holding or not HOLD_POSITION_BETWEEN_MOVES:
            self.release()

    def _legacy_style_constant(self, style_name):
        if Adafruit_MotorHAT is None:
            return None
        name = _LEGACY_STYLE_NAME.get(style_name, 'INTERLEAVE')
        return getattr(Adafruit_MotorHAT, name, Adafruit_MotorHAT.INTERLEAVE)

    def _legacy_direction_constant(self, forward=True):
        if Adafruit_MotorHAT is None:
            return None
        return Adafruit_MotorHAT.FORWARD if forward else Adafruit_MotorHAT.BACKWARD

    def _legacy_move_allowed(self):
        if not self._legacy_enabled or self._legacy_stepper is None:
            return False
        if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT:
            # Legacy step() is blocking and cannot check limits mid-move.
            return False
        return True

    def _legacy_step_move(self, full_steps, forward=True):
        with self._state_lock:
            style_name = self.style_name
            style_factor = _STYLE_FACTOR.get(style_name, 1)
            speed_rpm = self.speed_rpm

        legacy_stepper = self._legacy_stepper
        if legacy_stepper is None:
            return False

        total_steps = max(0, int(full_steps)) * style_factor
        if total_steps <= 0:
            return True

        direction = self._legacy_direction_constant(forward=forward)
        style = self._legacy_style_constant(style_name)
        if direction is None or style is None:
            return False

        legacy_stepper.setSpeed(max(1, int(speed_rpm)))
        legacy_stepper.step(total_steps, direction, style)
        if forward:
            self.current_position += int(full_steps)
        else:
            self.current_position -= int(full_steps)
        return True

    def _wait_until(self, target_time):
        while True:
            remaining = target_time - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.002))

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
        requested_steps = max(0, int(steps))
        if self._legacy_move_allowed():
            print(f"[MOVE] Moving forward {requested_steps} full-steps (legacy step backend)...")
            self.stop_requested = False
            self.is_moving = True
            try:
                return self._legacy_step_move(requested_steps, forward=True)
            finally:
                self._finalize_motion(keep_holding=True)

        with self._state_lock:
            style_name = self.style_name
            style_factor = _STYLE_FACTOR.get(style_name, 1)
            style = _STYLE_MAP.get(style_name, stepper.INTERLEAVE)
            speed_rpm = self.speed_rpm
        total_steps = max(0, int(steps)) * style_factor
        if total_steps <= 0:
            return True
        profile = self._current_profile_settings()
        check_interval = max(1, int(profile.get("safety_check_every_driver_steps", SAFETY_CHECK_EVERY_DRIVER_STEPS)))
        base_delay, ramp_steps, start_factor = self._timing_profile(total_steps, style_name, style_factor, speed_rpm)
        delta_per_driver_step = 1.0 / style_factor
        print(f"[MOVE] Moving forward {steps} full-steps ({total_steps} driver-steps)...")
        self.stop_requested = False
        self.is_moving = True
        completed_steps = 0
        reason = "completed"
        self._start_motion_diagnostics("move_forward", total_steps)
        try:
            next_step_time = time.monotonic()
            for i in range(total_steps):
                if self._safety_check_due(i, check_interval):
                    if self.stop_requested:
                        print("[MOVE] Stop requested")
                        reason = "stop_requested"
                        break
                    if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT and self.limit_switch_2_pressed():
                        print("[LIMIT] Limit switch 2 triggered - stopping motor")
                        reason = "limit_switch_2"
                        break
                self._record_scheduler_jitter(next_step_time, i, total_steps)
                step_delay = self._ramped_delay_from_profile(i, total_steps, base_delay, ramp_steps, start_factor)
                self.motor.onestep(direction=stepper.FORWARD, style=style)
                self.current_position += delta_per_driver_step
                completed_steps += 1
                next_step_time += step_delay
                self._wait_until(next_step_time)
        finally:
            self._finish_motion_diagnostics(completed_steps=completed_steps, reason=reason)
            self._finalize_motion(keep_holding=True)
        return True

    def move_backward(self, steps):
        """Move stepper backward by specified number of steps."""
        requested_steps = max(0, int(steps))
        if self._legacy_move_allowed():
            print(f"[MOVE] Moving backward {requested_steps} full-steps (legacy step backend)...")
            self.stop_requested = False
            self.is_moving = True
            try:
                return self._legacy_step_move(requested_steps, forward=False)
            finally:
                self._finalize_motion(keep_holding=True)

        with self._state_lock:
            style_name = self.style_name
            style_factor = _STYLE_FACTOR.get(style_name, 1)
            style = _STYLE_MAP.get(style_name, stepper.INTERLEAVE)
            speed_rpm = self.speed_rpm
        total_steps = max(0, int(steps)) * style_factor
        if total_steps <= 0:
            return True
        profile = self._current_profile_settings()
        check_interval = max(1, int(profile.get("safety_check_every_driver_steps", SAFETY_CHECK_EVERY_DRIVER_STEPS)))
        base_delay, ramp_steps, start_factor = self._timing_profile(total_steps, style_name, style_factor, speed_rpm)
        delta_per_driver_step = 1.0 / style_factor
        print(f"[MOVE] Moving backward {steps} full-steps ({total_steps} driver-steps)...")
        self.stop_requested = False
        self.is_moving = True
        completed_steps = 0
        reason = "completed"
        self._start_motion_diagnostics("move_backward", total_steps)
        try:
            next_step_time = time.monotonic()
            for i in range(total_steps):
                if self._safety_check_due(i, check_interval):
                    if self.stop_requested:
                        print("[MOVE] Stop requested")
                        reason = "stop_requested"
                        break
                    if ENABLE_LIMIT_SWITCHES and AUTO_STOP_AT_LIMIT and self.limit_switch_1_pressed():
                        print("[LIMIT] Limit switch 1 triggered - stopping motor")
                        reason = "limit_switch_1"
                        break
                self._record_scheduler_jitter(next_step_time, i, total_steps)
                step_delay = self._ramped_delay_from_profile(i, total_steps, base_delay, ramp_steps, start_factor)
                self.motor.onestep(direction=stepper.BACKWARD, style=style)
                self.current_position -= delta_per_driver_step
                completed_steps += 1
                next_step_time += step_delay
                self._wait_until(next_step_time)
        finally:
            self._finish_motion_diagnostics(completed_steps=completed_steps, reason=reason)
            self._finalize_motion(keep_holding=True)
        return True

    def stop(self):
        self.stop_requested = True
        self.is_moving = False
        self.release()
        print("[MOVE] Motor stopped")

    def home(self, max_steps=2000):
        """Move to home position using limit switch 1 (left/bottom)."""
        print("[HOME] Homing to limit switch 1...")
        with self._state_lock:
            style_name = self.style_name
            style_factor = _STYLE_FACTOR.get(style_name, 1)
            style = _STYLE_MAP.get(style_name, stepper.INTERLEAVE)
            speed_rpm = self.speed_rpm
        total_steps = max(1, int(max_steps)) * style_factor
        profile = self._current_profile_settings()
        check_interval = max(1, int(profile.get("safety_check_every_driver_steps", SAFETY_CHECK_EVERY_DRIVER_STEPS)))
        base_delay, ramp_steps, start_factor = self._timing_profile(total_steps, style_name, style_factor, speed_rpm)
        self.stop_requested = False
        steps = 0
        self.is_moving = True
        reason = "max_steps_reached"
        self._start_motion_diagnostics("home", total_steps)
        try:
            next_step_time = time.monotonic()
            while steps < total_steps:
                if self._safety_check_due(steps, check_interval):
                    if self.stop_requested:
                        print("[HOME] Stop requested")
                        reason = "stop_requested"
                        break
                    if self.limit_switch_1_pressed():
                        print("[HOME] Home position reached")
                        self.current_position = 0
                        reason = "home_reached"
                        return True
                self._record_scheduler_jitter(next_step_time, steps, total_steps)
                step_delay = self._ramped_delay_from_profile(steps, total_steps, base_delay, ramp_steps, start_factor)
                self.motor.onestep(direction=stepper.BACKWARD, style=style)
                self.current_position -= 1.0 / style_factor
                next_step_time += step_delay
                self._wait_until(next_step_time)
                steps += 1
        finally:
            self._finish_motion_diagnostics(completed_steps=steps, reason=reason)
            self._finalize_motion(keep_holding=False)
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
            performance_profile = self.performance_profile
            jitter_stats = dict(self._jitter_stats)
            last_motion_diag = dict(self._last_motion_diag) if self._last_motion_diag else None

        late_samples = int(jitter_stats.get("late_samples", 0))
        avg_late_ms = (float(jitter_stats.get("late_sum_ms", 0.0)) / late_samples) if late_samples > 0 else 0.0
        return {
            "position": round(self.current_position, 3),
            "limit_switch_1": self.limit_switch_1_pressed(),
            "limit_switch_2": self.limit_switch_2_pressed(),
            "moving": self.is_moving,
            "speed_rpm": speed_rpm,
            "style": style_name,
            "performance_profile": performance_profile,
            "diagnostics": {
                "jitter": {
                    "samples": int(jitter_stats.get("samples", 0)),
                    "late_samples": late_samples,
                    "max_late_ms": round(float(jitter_stats.get("max_late_ms", 0.0)), 3),
                    "avg_late_ms": round(avg_late_ms, 3),
                    "warn_count": int(jitter_stats.get("warn_count", 0)),
                    "total_moves": int(jitter_stats.get("total_moves", 0)),
                    "warn_threshold_ms": self._jitter_warn_threshold_ms,
                },
                "last_move": last_motion_diag,
            },
        }

    def release(self):
        self.motor.release()
        if self._legacy_enabled and self._legacy_hat is not None and Adafruit_MotorHAT is not None:
            motors = (1, 2) if MOTOR_PORT == 1 else (3, 4)
            for motor_idx in motors:
                self._legacy_hat.getMotor(motor_idx).run(Adafruit_MotorHAT.RELEASE)

    def cleanup(self):
        print("[GPIO] Cleaning up...")
        self.release()

def main():
    controller = None
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
        if controller is not None:
            controller.cleanup()

if __name__ == "__main__":
    main()
