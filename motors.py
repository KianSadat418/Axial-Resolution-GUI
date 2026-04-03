"""
Motor abstraction layer for the Axial Resolution GUI.

Provides a common `_MotorBase` API and concrete implementations for:
- Thorlabs Kinesis stages via `pylablib.devices.Thorlabs.KinesisMotor`
- Optional Pololu Tic stepper controllers via `pytic`
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import sleep, time
from typing import Callable, Optional

import config


class _MotorBase:
    """Minimal blocking motor API used by the GUI."""

    def connect(self) -> None:
        ...

    def move_rel_mm(self, dz_mm: float, speed_mm_s: float | None = None) -> None:
        ...

    def move_abs_mm(self, z_mm: float, speed_mm_s: float | None = None) -> None:
        ...

    def wait(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def shutdown(self) -> None:
        ...

    def perform_sawtooth_scan(
        self,
        range_mm: float,
        step_mm: float,
        fps: float,
        on_scan_start: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Axial scan motion: symmetric about 0 so the scan leg produces a bell curve.
        - Move up +range_mm/2 (to start position)
        - Call on_scan_start() if provided (GUI uses this to start frame capture)
        - Move down -range_mm (scan leg; frames captured during this)
        - Move up +range_mm/2 (return to 0)
        Scan speed on the middle leg is step_mm * fps so frame spacing matches step size.
        """
        raise NotImplementedError


# ---- Thorlabs Kinesis (via pylablib) ----

try:
    from pylablib.devices.Thorlabs import KinesisMotor  # type: ignore

    _HAS_KINESIS = True
except Exception:  # pragma: no cover - optional dependency
    KinesisMotor = None
    _HAS_KINESIS = False


class ThorlabsMotor(_MotorBase):
    """
    Kinesis via pylablib, GUI uses mm. We use scale='stage' so moves are in
    stage units, converted to mm where necessary.
    """

    def __init__(
        self,
        serial: str | None = None,
        stage: str | None = None,
        max_speed_mm_s: float = 1.0,
        accel_mm_s2: float = 2.0,
    ):
        if not _HAS_KINESIS:
            raise RuntimeError("pylablib / Thorlabs Kinesis not available")
        self.serial = serial
        self.stage = stage
        self._km = None
        self._ux_max_speed = max_speed_mm_s
        self._ux_accel = accel_mm_s2

    # ---- helpers ----

    def connect(self) -> None:
        devs = KinesisMotor.list_devices()
        if self.serial is None:
            if not devs:
                raise RuntimeError("No Thorlabs Kinesis motor found")
            self.serial = devs[0][0]
        scale = self.stage if self.stage else "stage"
        self._km = KinesisMotor(self.serial, scale=scale)
        self._set_speed(0.5, self._ux_accel)  # safe default

    def _get_units(self) -> str:
        try:
            return self._km.get_scale_units()
        except Exception:
            return "m"

    def _mm_to_stage(self, value_mm: float) -> float:
        units = self._get_units().lower()
        if units in ("mm", "millimeter", "millimeters"):
            return value_mm
        return value_mm / 1000.0  # assume meters

    def _set_speed(self, v_mm_s: float, a_mm_s2: float) -> None:
        assert self._km is not None
        if hasattr(self._km, "setup_velocity"):
            vmax = self._mm_to_stage(v_mm_s if v_mm_s > 0 else 0.5)
            acc  = self._mm_to_stage(a_mm_s2 if a_mm_s2 > 0 else 1.0)
            vmin = self._mm_to_stage(0.01)
            self._km.setup_velocity(min_velocity=vmin, acceleration=acc, max_velocity=vmax)
        elif hasattr(self._km, "set_velocity"):
            pct = 50
            if v_mm_s and self._ux_max_speed > 0:
                pct = max(1, min(100, int(round(100.0 * min(v_mm_s, self._ux_max_speed) / self._ux_max_speed))))
            self._km.set_velocity(pct)

    # ---- basic movement ----

    def move_rel_mm(self, dz_mm: float, speed_mm_s: float | None = None) -> None:
        assert self._km is not None, "Motor not connected"
        self._set_speed(speed_mm_s if speed_mm_s else 0.5, self._ux_accel)
        self._km.move_by(self._mm_to_stage(dz_mm), scale=True)
        self._km.wait_move()

    def move_abs_mm(self, z_mm: float, speed_mm_s: float | None = None) -> None:
        assert self._km is not None, "Motor not connected"
        self._set_speed(speed_mm_s if speed_mm_s else 0.5, self._ux_accel)
        self._km.move_to(self._mm_to_stage(z_mm), scale=True)
        self._km.wait_move()

    def wait(self) -> None:
        assert self._km is not None
        self._km.wait_move()

    def stop(self) -> None:
        if self._km:
            self._km.stop()

    def shutdown(self) -> None:
        if self._km:
            try:
                self._km.close()
            finally:
                self._km = None

    # ---- axial scan helper ----

    def perform_sawtooth_scan(
        self,
        range_mm: float,
        step_mm: float,
        fps: float,
        on_scan_start: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Axial scan: up range/2 → down range (scan leg) → up range/2 back to 0.
        Scan leg speed = step_mm * fps so frame spacing matches step size.
        """
        scan_speed = step_mm * fps                    # no floor — validated in GUI
        return_speed = min(scan_speed * 2, 2.0)
        half = range_mm / 2.0
        accel = config.MOTOR_ACCEL_MM_S2
        ramp_dist_mm = min(0.5 * scan_speed ** 2 / accel, range_mm * 0.05)

        self.move_rel_mm(+(half + ramp_dist_mm), speed_mm_s=return_speed)
        if on_scan_start:
            on_scan_start()
        self.move_rel_mm(-(range_mm + 2 * ramp_dist_mm), speed_mm_s=scan_speed)
        self.move_rel_mm(+(half + ramp_dist_mm), speed_mm_s=return_speed)


# ---- Optional Pololu Tic support ----

@dataclass
class PololuConfig:
    """Configuration needed to drive a Pololu Tic as a Z stage."""

    config_path: Path
    steps_per_mm: int = 3200


class PololuMotor(_MotorBase):
    """
    Pololu Tic motor backend using `pytic.PyTic`.

    This preserves the original behaviour used in the legacy code, but hides
    the details behind the same motor interface as Kinesis.
    """

    def __init__(self, cfg: PololuConfig):
        try:
            import pytic  # type: ignore
        except ImportError as e:  # pragma: no cover - optional dependency
            raise RuntimeError("pytic (Pololu Tic) is not installed") from e

        self._pytic_mod = pytic
        self.cfg = cfg
        self._tic = pytic.PyTic()
        self._connected = False

    def connect(self) -> None:
        serial_nums = self._tic.list_connected_device_serial_numbers()
        if not serial_nums:
            raise RuntimeError("No Pololu Tic devices detected")
        self._tic.connect_to_serial_number(serial_nums[0])
        self._connected = True

    # ---- helpers ----

    def _mm_to_steps(self, mm: float) -> int:
        return int(mm * self.cfg.steps_per_mm)

    def _load_config(self) -> None:
        self._tic.settings.load_config(str(self.cfg.config_path))

    # ---- basic movement ----

    def move_rel_mm(self, dz_mm: float, speed_mm_s: float | None = None) -> None:
        """
        Blocking relative move, matching the legacy button behaviour.
        """
        if not self._connected:
            self.connect()

        speed = speed_mm_s if speed_mm_s is not None else 1.0
        steps = self._mm_to_steps(dz_mm)
        max_speed = int(speed * self.cfg.steps_per_mm * 10000)

        self._load_config()
        self._tic.settings.max_speed = max_speed
        self._tic.settings.apply()
        self._tic.halt_and_set_position(0)
        self._tic.energize()
        self._tic.exit_safe_start()
        self._tic.set_target_position(steps)

        _deadline = time() + 30.0
        while self._tic.variables.current_position != self._tic.variables.target_position:
            if time() > _deadline:
                self._tic.halt_and_hold()
                raise RuntimeError("PololuMotor: move timed out after 30s")
            sleep(0.01)

        self._tic.enter_safe_start()
        self._tic.deenergize()

    def move_abs_mm(self, z_mm: float, speed_mm_s: float | None = None) -> None:
        """
        Simple absolute move relative to an internal origin; implemented as
        a relative move from 0 for now.
        """
        # Reset position to 0 then call move_rel_mm
        if not self._connected:
            self.connect()
        self._tic.halt_and_set_position(0)
        self.move_rel_mm(z_mm, speed_mm_s=speed_mm_s)

    def wait(self) -> None:
        # Moves are blocking in this implementation, so nothing extra to do.
        return

    def stop(self) -> None:
        if not self._connected:
            return
        try:
            self._tic.halt_and_hold()
        except Exception:
            pass

    def shutdown(self) -> None:
        if not self._connected:
            return
        try:
            self._tic.enter_safe_start()
            self._tic.deenergize()
        except Exception:
            pass
        self._connected = False

    # ---- axial scan helper ----

    def perform_sawtooth_scan(
        self,
        range_mm: float,
        step_mm: float,
        fps: float,
        on_scan_start: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Axial scan: up range/2 → down range (scan leg) → up range/2 back to 0.
        Scan leg speed = step_mm * fps so frame spacing matches step size.
        """
        if not self._connected:
            self.connect()

        scan_speed = step_mm * fps                    # no floor — validated in GUI
        return_speed = min(scan_speed * 2, 2.0)
        half = range_mm / 2.0
        accel = config.MOTOR_ACCEL_MM_S2
        ramp_dist_mm = min(0.5 * scan_speed ** 2 / accel, range_mm * 0.05)

        def run_move(dz_mm: float, speed_mm_s: float) -> None:
            self._load_config()
            self._tic.settings.max_speed = int(speed_mm_s * self.cfg.steps_per_mm * 10000)
            self._tic.settings.apply()
            self._tic.halt_and_set_position(0)
            self._tic.energize()
            self._tic.exit_safe_start()
            self._tic.set_target_position(self._mm_to_steps(dz_mm))
            _deadline = time() + 30.0
            while self._tic.variables.current_position != self._tic.variables.target_position:
                if time() > _deadline:
                    self._tic.halt_and_hold()
                    raise RuntimeError("PololuMotor: move timed out after 30s")
                sleep(0.01)
            self._tic.enter_safe_start()
            self._tic.deenergize()

        run_move(+(half + ramp_dist_mm), return_speed)
        if on_scan_start:
            on_scan_start()
        run_move(-(range_mm + 2 * ramp_dist_mm), scan_speed)
        run_move(+(half + ramp_dist_mm), return_speed)


def create_default_motor(config_path: Optional[str] = None) -> _MotorBase:
    """
    Auto-detect and connect to the first available motor.

    Tries in order: Thorlabs Kinesis → Pololu Tic. Uses whichever device
    is actually connected; no preference other than try order.
    """
    # 1. Thorlabs Kinesis – only connect if at least one device is listed
    if _HAS_KINESIS and KinesisMotor is not None:
        try:
            devs = KinesisMotor.list_devices()
            if devs:
                motor = ThorlabsMotor(serial=None, stage=None, max_speed_mm_s=1.0)
                motor.connect()
                return motor
        except Exception as e:
            print("[MOTOR] Thorlabs detection/connect failed:", e)

    # 2. Pololu Tic – only connect if at least one device is listed
    if config_path is not None:
        try:
            import pytic  # type: ignore
            tic = pytic.PyTic()
            serial_nums = tic.list_connected_device_serial_numbers()
            if serial_nums:
                cfg = PololuConfig(config_path=Path(config_path))
                motor = PololuMotor(cfg)
                motor.connect()
                return motor
        except ImportError:
            pass
        except Exception as e:
            print("[MOTOR] Pololu detection/connect failed:", e)

    raise RuntimeError(
        "No motor detected. Please connect a Thorlabs Kinesis or Pololu Tic device."
    )

