"""
Colored status dot indicator with optional pulse animation.

Green = connected, Red = disconnected, Amber + pulsing = connecting.
"""

from __future__ import annotations

import tkinter as tk

from axial_app.theme import (
    INDICATOR_SIZE, INDICATOR_PULSE_MS,
    STATUS_GREEN, STATUS_GREEN_DIM,
    STATUS_RED, STATUS_RED_DIM,
    STATUS_AMBER, STATUS_AMBER_DIM,
)


class StatusIndicator(tk.Canvas):
    """Small canvas circle showing connection status."""

    STATES = {
        "connected": (STATUS_GREEN, STATUS_GREEN_DIM),
        "disconnected": (STATUS_RED, STATUS_RED_DIM),
        "connecting": (STATUS_AMBER, STATUS_AMBER_DIM),
    }

    def __init__(self, master, size: int = INDICATOR_SIZE, **kwargs):
        self._size = size
        pad = 2
        super().__init__(
            master,
            width=size + pad * 2,
            height=size + pad * 2,
            highlightthickness=0,
            **kwargs,
        )
        self._pad = pad
        self._dot = self.create_oval(
            pad, pad, pad + size, pad + size,
            fill=STATUS_RED, outline="",
        )
        self._state = "disconnected"
        self._pulse_on = False
        self._after_id = None

    def set_state(self, state: str) -> None:
        """Set state to 'connected', 'disconnected', or 'connecting'."""
        if state == self._state:
            return
        self._state = state
        colors = self.STATES.get(state, self.STATES["disconnected"])
        self.itemconfigure(self._dot, fill=colors[0])

        # Start/stop pulse for connecting state
        if state == "connecting":
            self._start_pulse()
        else:
            self._stop_pulse()

    def _start_pulse(self) -> None:
        if self._pulse_on:
            return
        self._pulse_on = True
        self._pulse_tick(True)

    def _stop_pulse(self) -> None:
        self._pulse_on = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _pulse_tick(self, bright: bool) -> None:
        if not self._pulse_on:
            return
        colors = self.STATES.get(self._state, self.STATES["disconnected"])
        self.itemconfigure(self._dot, fill=colors[0] if bright else colors[1])
        self._after_id = self.after(
            INDICATOR_PULSE_MS, self._pulse_tick, not bright
        )

    def configure_bg(self, bg_color: str) -> None:
        """Update canvas background to match parent."""
        self.configure(bg=bg_color)
