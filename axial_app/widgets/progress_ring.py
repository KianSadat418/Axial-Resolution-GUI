"""
Canvas-drawn arc progress indicator.

Two modes:
- Indeterminate: spinning arc (during motor ramp, connecting)
- Determinate: filling arc proportional to progress (0.0 - 1.0)
"""

from __future__ import annotations

import tkinter as tk

from axial_app.theme import (
    RING_SIZE, RING_THICKNESS, RING_ANIM_INTERVAL_MS,
    ACCENT_PRIMARY, BORDER_DARK,
)


class ProgressRing(tk.Canvas):
    """Circular progress indicator drawn on a canvas."""

    def __init__(
        self,
        master,
        size: int = RING_SIZE,
        thickness: int = RING_THICKNESS,
        color: str = ACCENT_PRIMARY,
        track_color: str = BORDER_DARK,
        **kwargs,
    ):
        super().__init__(
            master,
            width=size,
            height=size,
            highlightthickness=0,
            **kwargs,
        )
        self._size = size
        self._thickness = thickness
        self._color = color
        self._track_color = track_color
        self._mode = "idle"  # idle, indeterminate, determinate
        self._progress = 0.0
        self._spin_angle = 0
        self._after_id = None

        pad = thickness
        self._bbox = (pad, pad, size - pad, size - pad)
        # Track arc (background)
        self._track = self.create_arc(
            *self._bbox, start=0, extent=359.9,
            outline=track_color, width=thickness, style="arc",
        )
        # Progress arc (foreground)
        self._arc = self.create_arc(
            *self._bbox, start=90, extent=0,
            outline=color, width=thickness, style="arc",
        )

    def set_indeterminate(self) -> None:
        """Start spinning animation."""
        self._mode = "indeterminate"
        self._spin_angle = 0
        self._start_animation()

    def set_determinate(self, progress: float = 0.0) -> None:
        """Switch to determinate mode with given progress (0.0-1.0)."""
        self._mode = "determinate"
        self._progress = max(0.0, min(1.0, progress))
        self._start_animation()

    def set_progress(self, progress: float) -> None:
        """Update progress value (0.0-1.0). Only effective in determinate mode."""
        self._progress = max(0.0, min(1.0, progress))

    def set_idle(self) -> None:
        """Stop animation and clear the ring."""
        self._mode = "idle"
        self._stop_animation()
        self.itemconfigure(self._arc, extent=0)

    def _start_animation(self) -> None:
        if self._after_id is not None:
            return
        self._tick()

    def _stop_animation(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self) -> None:
        if self._mode == "idle":
            self._after_id = None
            return

        if self._mode == "indeterminate":
            self._spin_angle = (self._spin_angle + 8) % 360
            self.itemconfigure(
                self._arc,
                start=90 - self._spin_angle,
                extent=-90,
            )
        elif self._mode == "determinate":
            extent = -360 * self._progress
            self.itemconfigure(self._arc, start=90, extent=extent)

        self._after_id = self.after(RING_ANIM_INTERVAL_MS, self._tick)

    def configure_colors(self, color: str = None, track_color: str = None, bg: str = None) -> None:
        if color:
            self._color = color
            self.itemconfigure(self._arc, outline=color)
        if track_color:
            self._track_color = track_color
            self.itemconfigure(self._track, outline=track_color)
        if bg:
            self.configure(bg=bg)
