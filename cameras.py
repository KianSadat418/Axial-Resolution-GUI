"""
Camera abstraction layer for the Axial Resolution GUI.

This module exposes a small, backend-agnostic API (`CameraBase`) and concrete
implementations for:
- Player One cameras via `pyPOACamera`
- Allied Vision Alvium cameras via `vmbpy` (Vimba X)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Tuple, Optional

import numpy as np

import config


class CameraBase:
    """Abstract camera API used by the GUI."""

    def open(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def set_exposure(self, exposure_us: float) -> None:
        raise NotImplementedError

    def set_gain(self, gain_val: float) -> None:
        raise NotImplementedError

    def get_frame(self, timeout_ms: int = 100) -> Optional[np.ndarray]:
        """Return a 2D uint8 numpy array (grayscale)."""
        raise NotImplementedError

    def get_size(self) -> Tuple[int, int]:
        """Return (width, height) of the current ROI."""
        raise NotImplementedError


@dataclass
class PlayerOneDefaults:
    exposure_us: float = config.DEFAULT_EXPOSURE_US
    gain: float = config.DEFAULT_GAIN
    offset: int = config.DEFAULT_OFFSET
    fps: int = config.DEFAULT_FPS


class PlayerOneCamera(CameraBase):
    """Player One (MARS-C etc.) backend via pyPOACamera."""

    def __init__(self, cam_index: int = 0, defaults: PlayerOneDefaults | None = None):
        import pyPOACamera  # type: ignore

        self._py = pyPOACamera
        self.cam_index = cam_index
        self.camera_id: Optional[int] = None
        self.img_width: Optional[int] = None
        self.img_height: Optional[int] = None
        self.img_format = None
        self.img_size: Optional[int] = None
        self._buffer: Optional[np.ndarray] = None
        self._exposing: bool = False
        self._bit_depth: int = 12

        self._defaults = defaults or PlayerOneDefaults()

    # ---- lifecycle ----

    def open(self) -> None:
        py = self._py

        # Get camera properties for first POA camera
        err, props = py.GetCameraProperties(self.cam_index)
        if err != py.POAErrors.POA_OK:
            raise RuntimeError(f"POA GetCameraProperties failed: {py.GetErrorString(err)}")

        self.camera_id = props.cameraID
        model = props.cameraModelName.decode(errors="ignore")
        sensor = props.sensorModelName.decode(errors="ignore")
        print(f"[POA] Detected {model} (sensor {sensor})")
        try:
            self._bit_depth = int(props.bitDepth) if props.bitDepth else 12
        except Exception:
            self._bit_depth = 12

        # Open and init
        err = py.OpenCamera(self.camera_id)
        if err != py.POAErrors.POA_OK:
            raise RuntimeError(f"POA OpenCamera failed: {py.GetErrorString(err)}")

        err = py.InitCamera(self.camera_id)
        if err != py.POAErrors.POA_OK:
            raise RuntimeError(f"POA InitCamera failed: {py.GetErrorString(err)}")

        # ROI: mimic original values (1296x1096, crop_x=615)
        width = 1296
        height = 1096
        crop_x = 615
        crop_y = 0

        err = py.SetImageSize(self.camera_id, width, height)
        if err != py.POAErrors.POA_OK:
            print("Warning: SetImageSize failed:", py.GetErrorString(err))
        err = py.SetImageStartPos(self.camera_id, crop_x, crop_y)
        if err != py.POAErrors.POA_OK:
            print("Warning: SetImageStartPos failed:", py.GetErrorString(err))

        err, self.img_width, self.img_height = py.GetImageSize(self.camera_id)
        if err != py.POAErrors.POA_OK:
            raise RuntimeError("POA GetImageSize failed")
        err, self.img_format = py.GetImageFormat(self.camera_id)
        if err != py.POAErrors.POA_OK:
            raise RuntimeError("POA GetImageFormat failed")

        self.img_size = py.ImageCalcSize(self.img_height, self.img_width, self.img_format)
        self._buffer = np.zeros(self.img_size, dtype=np.uint8)

        # Apply default exposure/gain
        self.set_exposure(self._defaults.exposure_us)
        self.set_gain(self._defaults.gain)

        # Try to limit FPS / bandwidth
        try:
            py.SetConfig(
                self.camera_id,
                py.POAConfig.POA_FRAME_LIMIT,
                int(self._defaults.fps),
                False,
            )
            py.SetConfig(
                self.camera_id,
                py.POAConfig.POA_USB_BANDWIDTH_LIMIT,
                90,
                False,
            )
        except Exception:
            pass

        # Start continuous exposure
        err = py.StartExposure(self.camera_id, False)
        if err != py.POAErrors.POA_OK:
            raise RuntimeError(f"POA StartExposure failed: {py.GetErrorString(err)}")
        self._exposing = True

    # ---- parameter control ----

    def set_exposure(self, exposure_us: float) -> None:
        if self.camera_id is None:
            return
        py = self._py
        err = py.SetExp(self.camera_id, int(exposure_us), False)
        if err != py.POAErrors.POA_OK:
            print("[POA] SetExp failed:", py.GetErrorString(err))

    def set_gain(self, gain_val: float) -> None:
        if self.camera_id is None:
            return
        py = self._py
        g_int = int(gain_val)
        err = py.SetGain(self.camera_id, g_int, False)
        if err != py.POAErrors.POA_OK:
            print("[POA] SetGain failed:", py.GetErrorString(err))

        # Refresh offset based on presets
        status, presets = py.GetGainsAndOffsets(self.camera_id)
        if status == py.POAErrors.POA_OK:
            HCGain = int(presets.pHCGain)
            off_HC = int(presets.pOffsetHCGain)
            off_DR = int(presets.pOffsetHighestDR)
            chosen_offset = off_HC if g_int >= HCGain else off_DR
            py.SetConfig(self.camera_id, py.POAConfig.POA_OFFSET, chosen_offset, False)
            print(f"[POA] HCGain={HCGain} offset={chosen_offset}")
        else:
            # Fallback to default offset if presets not available
            py.SetConfig(
                self.camera_id,
                py.POAConfig.POA_OFFSET,
                self._defaults.offset,
                False,
            )

    # ---- frame acquisition ----

    def get_frame(self, timeout_ms: int = 100) -> Optional[np.ndarray]:
        if self.camera_id is None:
            return None
        py = self._py

        # Poll ImageReady with deadline (Bug 4: no CPU spin)
        deadline = time.monotonic() + timeout_ms / 1000.0
        while True:
            err, ready = py.ImageReady(self.camera_id)
            if err != py.POAErrors.POA_OK:
                return None
            if ready and self._buffer is not None:
                break
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.001)

        err = py.GetImageData(self.camera_id, self._buffer, timeout_ms)
        if err != py.POAErrors.POA_OK:
            print("[POA] GetImageData error:", py.GetErrorString(err))
            return None

        img = py.ImageDataConvert(
            self._buffer, self.img_height, self.img_width, self.img_format
        )

        # Bug 15: guard against None return
        if img is None:
            return None

        # Normalize for RAW16, otherwise just squeeze to 2D
        if self.img_format == py.POAImgFormat.POA_RAW16:
            frame16 = np.squeeze(img, axis=2) if img.ndim == 3 else img
            # Bug 5: correct shift for actual sensor bit depth (e.g. 12-bit → divide by 16, not 256)
            scale = 2 ** (self._bit_depth - 8)
            frame8 = (frame16 // scale).astype(np.uint8)
            return frame8
        elif self.img_format in (
            py.POAImgFormat.POA_RAW8,
            py.POAImgFormat.POA_MONO8,
        ):
            frame8 = np.squeeze(img, axis=2) if img.ndim == 3 else img
            return frame8.astype(np.uint8)
        else:
            # Any other format: best effort
            if img.ndim == 3 and img.shape[2] == 1:
                return img[:, :, 0].astype(np.uint8)
            return img.astype(np.uint8)

    def get_size(self) -> Tuple[int, int]:
        if self.img_width is None or self.img_height is None:
            return 0, 0
        return int(self.img_width), int(self.img_height)

    # ---- cleanup ----

    def close(self) -> None:
        if self.camera_id is not None:
            py = self._py
            if self._exposing:
                try:
                    py.StopExposure(self.camera_id)
                except Exception:
                    pass
            try:
                py.CloseCamera(self.camera_id)
            except Exception:
                pass
            self.camera_id = None
            self._exposing = False


class AlviumCamera(CameraBase):
    """Allied Vision Alvium backend via VmbPy / Vimba X."""

    def __init__(self, cam_id: Optional[str] = None,
                 exposure_us: float = config.DEFAULT_EXPOSURE_US,
                 gain: float = config.DEFAULT_GAIN):
        self.cam_id = cam_id
        self._vmb = None
        self._cam = None
        self._width: int = 0
        self._height: int = 0
        self._default_exposure_us = exposure_us
        self._default_gain = gain

    def open(self) -> None:
        try:
            import vmbpy as vmb  # type: ignore
        except ImportError as e:  # pragma: no cover - optional dependency
            raise RuntimeError("vmbpy (Vimba X Python API) is not installed") from e

        self._vmb = vmb.VmbSystem.get_instance()
        self._vmb.__enter__()
        try:
            cams = self._vmb.get_all_cameras()
            if not cams:
                raise RuntimeError("No Allied Vision cameras found by VmbPy")
            self._cam = cams[0] if self.cam_id is None else self._vmb.get_camera_by_id(self.cam_id)
            self._cam.__enter__()
        except Exception:
            self._vmb.__exit__(None, None, None)
            self._vmb = None
            raise

        # Try to set PixelFormat to Mono8 (if available)
        try:
            pf = self._cam.get_feature_by_name("PixelFormat")
            avail = pf.get_available()
            if "Mono8" in avail:
                pf.set("Mono8")
        except Exception as e:
            print("[ALV] Could not set PixelFormat to Mono8:", e)

        self._update_size()
        print(f"[ALV] Using camera {self._cam.get_name()} {self._width}x{self._height}")

        # Apply default global exposure/gain if possible
        self.set_exposure(self._default_exposure_us)
        self.set_gain(self._default_gain)

    def _update_size(self) -> None:
        try:
            w_feat = self._cam.get_feature_by_name("Width")
            h_feat = self._cam.get_feature_by_name("Height")
            self._width = int(w_feat.get())
            self._height = int(h_feat.get())
        except Exception as e:
            print("[ALV] Failed to read Width/Height:", e)
            self._width, self._height = 0, 0

    def set_exposure(self, exposure_us: float) -> None:
        if self._cam is None:
            return
        try:
            feat = self._cam.get_feature_by_name("ExposureTime")
            mn, mx = feat.get_range()
            val = max(mn, min(mx, float(exposure_us)))
            feat.set(val)
            print(f"[ALV] ExposureTime set to {val} µs")
        except Exception as e:
            print("[ALV] Failed to set ExposureTime:", e)

    def set_gain(self, gain_val: float) -> None:
        if self._cam is None:
            return
        try:
            feat = self._cam.get_feature_by_name("Gain")
            mn, mx = feat.get_range()
            val = max(mn, min(mx, float(gain_val)))
            feat.set(val)
            print(f"[ALV] Gain set to {val}")
        except Exception as e:
            print("[ALV] Failed to set Gain:", e)

    def get_frame(self, timeout_ms: int = 100) -> Optional[np.ndarray]:
        if self._cam is None:
            return None
        try:
            from vmbpy import FrameStatus, PixelFormat  # type: ignore

            frame = self._cam.get_frame(timeout_ms)
            if frame.get_status() is not FrameStatus.Complete:
                return None
            try:
                frame.convert_pixel_format(PixelFormat.Mono8)
            except Exception:
                pass
            img = frame.as_numpy_ndarray()  # HxW or HxWxC
            if img.ndim == 3 and img.shape[2] == 1:
                img = img[:, :, 0]
            return img.astype(np.uint8)
        except Exception as e:
            print("[ALV] get_frame error:", e)
            return None

    def get_size(self) -> Tuple[int, int]:
        return int(self._width), int(self._height)

    def close(self) -> None:
        if self._cam is not None:
            try:
                self._cam.__exit__(None, None, None)
            except Exception:
                pass
            self._cam = None
        if self._vmb is not None:
            try:
                self._vmb.__exit__(None, None, None)
            except Exception:
                pass
            self._vmb = None


# ---------------------------------------------------------------------------
# Auto-detection: try each backend in order and return the first camera that
# opens successfully. Add new backends here (e.g. Basler) for plug-and-play.
# ---------------------------------------------------------------------------

def detect_and_open_camera(
    exposure_us: float = config.DEFAULT_EXPOSURE_US,
    gain: float = config.DEFAULT_GAIN,
    fps: int = config.DEFAULT_FPS,
) -> tuple[Optional[CameraBase], Optional[str]]:
    """
    Detect and open the first available camera from supported backends.

    Tries in order: Player One → Allied Vision Alvium → Basler (stub).
    Returns (camera_instance, backend_name) or (None, None) if none found.
    """
    # 1. Player One (pyPOACamera)
    try:
        import pyPOACamera  # type: ignore
        if pyPOACamera.GetCameraCount() > 0:
            cam = PlayerOneCamera(
                cam_index=0,
                defaults=PlayerOneDefaults(
                    exposure_us=exposure_us,
                    gain=gain,
                    fps=fps,
                ),
            )
            cam.open()
            return cam, "PlayerOne"
    except Exception as e:
        print("[CAM] Player One detection failed:", e)

    # 2. Allied Vision Alvium (VmbPy / Vimba X)
    try:
        cam = AlviumCamera(
            cam_id=None,
            exposure_us=exposure_us,
            gain=gain,
        )
        cam.open()
        return cam, "Alvium"
    except ImportError:
        pass
    except Exception as e:
        print("[CAM] Alvium detection failed:", e)

    # 3. Basler (pypylon) – stub for future
    try:
        cam, backend = _try_open_basler(exposure_us=exposure_us, gain=gain)
        if cam is not None:
            return cam, backend
    except Exception as e:
        print("[CAM] Basler detection failed:", e)

    return None, None


def _try_open_basler(
    exposure_us: float = config.DEFAULT_EXPOSURE_US,
    gain: float = config.DEFAULT_GAIN,
) -> tuple[Optional[CameraBase], Optional[str]]:
    """
    Try to detect and open a Basler camera (pypylon). Returns (None, None) if
    not available or no device. Implement when Basler support is added.
    """
    try:
        import pypylon  # type: ignore  # noqa: F401
    except ImportError:
        return None, None
    # TODO: enumerate devices, open first, wrap in a BaslerCamera(CameraBase)
    return None, None

