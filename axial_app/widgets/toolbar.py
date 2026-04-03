"""
Icon toolbar bar below the menu.

Uses PIL-generated simple icons (no external icon pack needed).
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ct
from PIL import Image, ImageDraw

from axial_app.theme import (
    TOOLBAR_HEIGHT, TOOLBAR_BTN_SIZE, PAD_SM, PAD_MD,
    ACCENT_PRIMARY, TEXT_PRIMARY_DARK, ICON_SIZE,
)
from axial_app.widgets.tooltip import Tooltip


def _make_icon(draw_func, size: int = ICON_SIZE, color: str = "#e2e8f0") -> Image.Image:
    """Create a small PIL icon by calling draw_func(draw, size, color)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_func(draw, size, color)
    return img


def _draw_connect(draw, s, c):
    # Plug icon: two vertical lines with horizontal connector
    m = s // 2
    draw.line([(s // 4, s // 4), (s // 4, 3 * s // 4)], fill=c, width=2)
    draw.line([(3 * s // 4, s // 4), (3 * s // 4, 3 * s // 4)], fill=c, width=2)
    draw.line([(s // 4, m), (3 * s // 4, m)], fill=c, width=2)


def _draw_scan(draw, s, c):
    # Sine wave / scan icon
    points = []
    import math
    for i in range(s):
        y = s // 2 + int((s // 3) * math.sin(i * 2 * math.pi / s))
        points.append((i, y))
    draw.line(points, fill=c, width=2)


def _draw_save(draw, s, c):
    # Floppy disk icon
    p = s // 5
    draw.rectangle([p, p, s - p, s - p], outline=c, width=2)
    draw.rectangle([p + 3, p, s - p - 3, p + 5], outline=c, width=1)
    draw.rectangle([p + 2, s // 2, s - p - 2, s - p - 2], outline=c, width=1)


def _draw_export(draw, s, c):
    # Arrow pointing out of box
    m = s // 2
    p = s // 5
    draw.rectangle([p, m, s - p, s - p], outline=c, width=2)
    draw.line([(m, m), (m, p)], fill=c, width=2)
    draw.polygon([(m - 3, p + 3), (m, p - 1), (m + 3, p + 3)], fill=c)


def _draw_theme(draw, s, c):
    # Half circle (light/dark toggle)
    m = s // 2
    r = s // 3
    draw.arc([m - r, m - r, m + r, m + r], 0, 360, fill=c, width=2)
    draw.pieslice([m - r, m - r, m + r, m + r], 90, 270, fill=c)


class Toolbar(ct.CTkFrame):
    """Horizontal toolbar with icon buttons."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=TOOLBAR_HEIGHT, corner_radius=0, **kwargs)
        self.grid_propagate(False)
        self._buttons: list[ct.CTkButton] = []
        self._col = 0

    def add_button(
        self,
        icon_draw_func,
        tooltip_text: str,
        command: Callable,
        icon_color: str = "#e2e8f0",
    ) -> ct.CTkButton:
        """Add an icon button to the toolbar."""
        icon_img = _make_icon(icon_draw_func, color=icon_color)
        ctk_icon = ct.CTkImage(light_image=icon_img, dark_image=icon_img,
                               size=(ICON_SIZE, ICON_SIZE))

        btn = ct.CTkButton(
            self,
            text="",
            image=ctk_icon,
            width=TOOLBAR_BTN_SIZE,
            height=TOOLBAR_BTN_SIZE,
            corner_radius=4,
            command=command,
            fg_color="transparent",
            hover_color=("#dde0e8", "#253556"),
        )
        btn.grid(row=0, column=self._col, padx=PAD_SM, pady=PAD_SM)
        Tooltip(btn, tooltip_text)
        self._buttons.append(btn)
        self._col += 1
        return btn

    def add_separator(self) -> None:
        """Add a vertical separator line."""
        sep = ct.CTkFrame(self, width=1, height=TOOLBAR_BTN_SIZE - 8, corner_radius=0)
        sep.grid(row=0, column=self._col, padx=PAD_SM, pady=PAD_SM + 4)
        self._col += 1

    def add_spacer(self) -> None:
        """Add an expanding spacer."""
        self.grid_columnconfigure(self._col, weight=1)
        self._col += 1


# Expose icon draw functions for toolbar setup
ICONS = {
    "connect": _draw_connect,
    "scan": _draw_scan,
    "save": _draw_save,
    "export": _draw_export,
    "theme": _draw_theme,
}
