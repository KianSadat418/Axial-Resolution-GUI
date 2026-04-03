"""
Animation helpers using Tkinter's after() mechanism.

All animations are non-blocking and driven by the main thread event loop.
"""

from __future__ import annotations

import math
from typing import Callable, Optional


class AnimationScheduler:
    """Manages after()-based animations on a Tkinter widget."""

    def __init__(self, widget):
        self._widget = widget
        self._active: dict[str, str] = {}  # name -> after_id

    def start(
        self,
        name: str,
        callback: Callable[[int], bool],
        interval_ms: int = 33,
    ) -> None:
        """
        Start a named animation.

        callback(frame_number) is called every interval_ms milliseconds.
        Return False from callback to stop the animation.
        """
        self.stop(name)
        frame = [0]

        def _tick():
            if name not in self._active:
                return
            should_continue = callback(frame[0])
            frame[0] += 1
            if should_continue:
                self._active[name] = self._widget.after(interval_ms, _tick)
            else:
                self._active.pop(name, None)

        self._active[name] = self._widget.after(interval_ms, _tick)

    def stop(self, name: str) -> None:
        """Stop a named animation if running."""
        after_id = self._active.pop(name, None)
        if after_id is not None:
            try:
                self._widget.after_cancel(after_id)
            except Exception:
                pass

    def stop_all(self) -> None:
        """Stop all running animations."""
        for name in list(self._active.keys()):
            self.stop(name)

    def is_running(self, name: str) -> bool:
        return name in self._active


def ease_in_out(t: float) -> float:
    """Ease-in-out curve (smooth start and end). t in [0, 1]."""
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * t


def pulse_alpha(frame: int, period_frames: int = 30) -> float:
    """Return a 0..1 pulsing alpha value based on frame number."""
    t = (frame % period_frames) / period_frames
    return 0.5 + 0.5 * math.sin(2 * math.pi * t)
