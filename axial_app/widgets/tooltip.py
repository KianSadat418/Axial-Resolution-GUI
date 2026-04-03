"""
Hover tooltip using CTkToplevel.

Appears after a delay when hovering over a widget, disappears on leave.
"""

from __future__ import annotations

import customtkinter as ct

from axial_app.theme import TOOLTIP_DELAY_MS, FONT_FAMILY, FONT_SIZE_SM, PAD_SM


class Tooltip:
    """Attach a tooltip to any widget."""

    def __init__(self, widget, text: str, delay_ms: int = TOOLTIP_DELAY_MS):
        self._widget = widget
        self._text = text
        self._delay_ms = delay_ms
        self._toplevel: ct.CTkToplevel | None = None
        self._after_id: str | None = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Button-1>", self._on_leave, add="+")

    def _on_enter(self, event=None) -> None:
        self._cancel()
        self._after_id = self._widget.after(self._delay_ms, self._show)

    def _on_leave(self, event=None) -> None:
        self._cancel()
        self._hide()

    def _cancel(self) -> None:
        if self._after_id is not None:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        if self._toplevel is not None:
            return
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 5

        self._toplevel = ct.CTkToplevel(self._widget)
        self._toplevel.wm_overrideredirect(True)
        self._toplevel.wm_geometry(f"+{x}+{y}")
        self._toplevel.attributes("-topmost", True)

        label = ct.CTkLabel(
            self._toplevel,
            text=self._text,
            font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_SM),
            corner_radius=4,
            padx=PAD_SM + 4,
            pady=PAD_SM,
        )
        label.pack()

    def _hide(self) -> None:
        if self._toplevel is not None:
            self._toplevel.destroy()
            self._toplevel = None

    def update_text(self, text: str) -> None:
        self._text = text
