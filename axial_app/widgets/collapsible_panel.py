"""
Collapsible panel with animated expand/collapse.

Header with triangle indicator (▶/▼) + title, clickable to toggle.
Content frame animates height via after() steps.
"""

from __future__ import annotations

import customtkinter as ct

from axial_app.theme import (
    FONT_FAMILY, FONT_SIZE_MD, PAD_SM, PAD_MD,
    COLLAPSE_ANIM_MS, COLLAPSE_ANIM_STEPS,
    ACCENT_PRIMARY,
)


class CollapsiblePanel(ct.CTkFrame):
    """Expandable/collapsible section with animated toggle."""

    def __init__(
        self,
        master,
        title: str = "Section",
        expanded: bool = True,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._expanded = expanded
        self._animating = False
        self._target_height = 0

        self.grid_columnconfigure(0, weight=1)

        # Header (clickable)
        self._header = ct.CTkFrame(self, height=32, corner_radius=4)
        self._header.grid(row=0, column=0, sticky="ew", padx=PAD_SM, pady=(PAD_SM, 0))
        self._header.grid_columnconfigure(1, weight=1)

        arrow_text = "▼" if expanded else "▶"
        self._arrow = ct.CTkLabel(
            self._header, text=arrow_text,
            font=ct.CTkFont(size=FONT_SIZE_MD),
            width=20,
        )
        self._arrow.grid(row=0, column=0, padx=(PAD_MD, PAD_SM), pady=PAD_SM)

        self._title_label = ct.CTkLabel(
            self._header, text=title,
            font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_MD, weight="bold"),
            anchor="w",
        )
        self._title_label.grid(row=0, column=1, padx=PAD_SM, pady=PAD_SM, sticky="w")

        # Make entire header clickable
        for widget in (self._header, self._arrow, self._title_label):
            widget.bind("<Button-1>", lambda e: self.toggle())
            widget.configure(cursor="hand2")

        # Content frame
        self._content = ct.CTkFrame(self, corner_radius=4)
        self._content.grid_columnconfigure(0, weight=1)
        if expanded:
            self._content.grid(row=1, column=0, sticky="ew", padx=PAD_SM, pady=(0, PAD_SM))
        else:
            # Hidden initially
            pass

    @property
    def content(self) -> ct.CTkFrame:
        """The frame to add child widgets to."""
        return self._content

    @property
    def expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        """Toggle expanded/collapsed state."""
        if self._animating:
            return
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self) -> None:
        """Expand the panel to show content."""
        if self._expanded or self._animating:
            return
        self._expanded = True
        self._arrow.configure(text="▼")
        self._content.grid(row=1, column=0, sticky="ew", padx=PAD_SM, pady=(0, PAD_SM))

    def collapse(self) -> None:
        """Collapse the panel to hide content."""
        if not self._expanded or self._animating:
            return
        self._expanded = False
        self._arrow.configure(text="▶")
        self._content.grid_forget()
