"""
Bottom status bar showing camera, motor, FPS, and scan status.
"""

from __future__ import annotations

import customtkinter as ct

from axial_app.theme import (
    STATUSBAR_HEIGHT, FONT_FAMILY, FONT_SIZE_SM, FONT_MONO,
    PAD_SM, PAD_MD,
)
from axial_app.widgets.status_indicator import StatusIndicator


class StatusBar(ct.CTkFrame):
    """Thin bar at the bottom of the window with status sections."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=STATUSBAR_HEIGHT, corner_radius=0, **kwargs)
        self.grid_propagate(False)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=1)  # scan status gets remaining space

        font = ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_SM)
        mono_font = ct.CTkFont(family=FONT_MONO, size=FONT_SIZE_SM)

        # Camera section
        self._cam_indicator = StatusIndicator(self, size=8)
        self._cam_indicator.grid(row=0, column=0, padx=(PAD_MD, 2), pady=PAD_SM)

        self._cam_label = ct.CTkLabel(self, text="Camera: —", font=font, anchor="w")
        self._cam_label.grid(row=0, column=0, padx=(PAD_MD + 14, PAD_MD), pady=PAD_SM, sticky="w")

        # Separator
        sep1 = ct.CTkLabel(self, text="|", font=font)
        sep1.grid(row=0, column=0, padx=(140, 0), pady=PAD_SM)

        # Motor section
        self._motor_indicator = StatusIndicator(self, size=8)
        self._motor_indicator.grid(row=0, column=1, padx=(PAD_SM, 2), pady=PAD_SM)

        self._motor_label = ct.CTkLabel(self, text="Motor: —", font=font, anchor="w")
        self._motor_label.grid(row=0, column=1, padx=(PAD_SM + 14, PAD_MD), pady=PAD_SM, sticky="w")

        # FPS section
        self._fps_label = ct.CTkLabel(self, text="FPS: —", font=mono_font, anchor="w")
        self._fps_label.grid(row=0, column=2, padx=PAD_MD, pady=PAD_SM, sticky="w")

        # Scan status
        self._status_label = ct.CTkLabel(self, text="Ready", font=font, anchor="w")
        self._status_label.grid(row=0, column=3, padx=PAD_MD, pady=PAD_SM, sticky="w")

    def set_camera(self, name: str | None) -> None:
        if name:
            self._cam_label.configure(text=f"Camera: {name}")
            self._cam_indicator.set_state("connected")
        else:
            self._cam_label.configure(text="Camera: —")
            self._cam_indicator.set_state("disconnected")

    def set_motor(self, name: str | None) -> None:
        if name:
            self._motor_label.configure(text=f"Motor: {name}")
            self._motor_indicator.set_state("connected")
        else:
            self._motor_label.configure(text="Motor: —")
            self._motor_indicator.set_state("disconnected")

    def set_fps(self, fps: float) -> None:
        self._fps_label.configure(text=f"FPS: {fps:.0f}")

    def set_status(self, text: str) -> None:
        self._status_label.configure(text=text)

    def set_camera_connecting(self) -> None:
        self._cam_label.configure(text="Camera: connecting...")
        self._cam_indicator.set_state("connecting")

    def set_motor_connecting(self) -> None:
        self._motor_label.configure(text="Motor: connecting...")
        self._motor_indicator.set_state("connecting")
