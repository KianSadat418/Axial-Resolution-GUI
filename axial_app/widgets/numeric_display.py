"""
Monospace numeric readout widget for measurement results.

Shows a label + value in Consolas font with optional color coding
based on thresholds.
"""

from __future__ import annotations

import customtkinter as ct

from axial_app.theme import (
    FONT_MONO, FONT_SIZE_READOUT, FONT_SIZE_READOUT_LABEL,
    STATUS_GREEN, STATUS_AMBER, STATUS_RED,
    TEXT_PRIMARY_DARK, TEXT_SECONDARY_DARK,
    PAD_SM, PAD_MD,
)


class NumericDisplay(ct.CTkFrame):
    """Monospace readout for a single measurement value."""

    def __init__(
        self,
        master,
        label: str = "Value",
        unit: str = "",
        threshold_good: float | None = None,
        threshold_warn: float | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._unit = unit
        self._threshold_good = threshold_good
        self._threshold_warn = threshold_warn

        self.grid_columnconfigure(0, weight=1)

        self._label = ct.CTkLabel(
            self,
            text=label,
            font=ct.CTkFont(family="Segoe UI", size=FONT_SIZE_READOUT_LABEL),
            anchor="w",
        )
        self._label.grid(row=0, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self._value_label = ct.CTkLabel(
            self,
            text="—",
            font=ct.CTkFont(family=FONT_MONO, size=FONT_SIZE_READOUT, weight="bold"),
            anchor="w",
        )
        self._value_label.grid(row=1, column=0, padx=PAD_MD, pady=(0, PAD_SM), sticky="w")

    def set_value(self, value: float | str, suffix: str = "") -> None:
        """Update the displayed value."""
        if isinstance(value, (int, float)):
            text = f"{value:.4f}" if isinstance(value, float) else str(value)
            if self._unit:
                text += f" {self._unit}"
            if suffix:
                text += f" {suffix}"
            self._apply_threshold_color(value)
        else:
            text = str(value)
        self._value_label.configure(text=text)

    def set_text(self, text: str) -> None:
        """Set arbitrary text (e.g., 'N/A')."""
        self._value_label.configure(text=text)

    def _apply_threshold_color(self, value: float) -> None:
        if self._threshold_good is None:
            return
        if value <= self._threshold_good:
            color = STATUS_GREEN
        elif self._threshold_warn is not None and value <= self._threshold_warn:
            color = STATUS_AMBER
        else:
            color = STATUS_RED
        self._value_label.configure(text_color=color)
