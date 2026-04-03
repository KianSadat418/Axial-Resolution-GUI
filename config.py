"""
Shared configuration values and defaults for the Axial Resolution GUI.

These are *defaults only* and are not mutated at runtime. Runtime state such as
current exposure, gain, etc. should live on GUI or device instances.
"""

from __future__ import annotations

# ---- Camera defaults ----

DEFAULT_FPS: int = 136

# Exposure in microseconds
DEFAULT_EXPOSURE_US: int = 7355

# Camera gain units (backend specific)
DEFAULT_GAIN: int = 480

# Player One offset fallback
DEFAULT_OFFSET: int = 0


# ---- Zoom / display defaults ----

# Percentage of half-width/height used for zoom window radius.
DEFAULT_ZOOM_RADIUS_PERCENT: float = 12.5
MIN_ZOOM_RADIUS_PERCENT: float = 1.0
MAX_ZOOM_RADIUS_PERCENT: float = 25.0


# ---- Motor defaults ----
MOTOR_ACCEL_MM_S2: float = 2.0  # used for ramp calculation in sawtooth scan

