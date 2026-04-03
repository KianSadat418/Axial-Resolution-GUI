"""
CapturePage — all scan/camera logic preserved from the original application.

This is the main working page of the GUI. All threading, FWHM calculation,
camera feed, zoom, mouse interactions, and motor controls are preserved exactly.
The layout has been redesigned with collapsible panels, status bar integration,
progress ring, numeric displays, and crosshair overlay.
"""

from __future__ import annotations

from datetime import datetime
import customtkinter as ct
from tkinter import filedialog
from PIL import Image, ImageDraw
import cv2
import numpy as np
import threading
import os
from pathlib import Path
from time import sleep, time, perf_counter
from typing import Optional

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import config
from cameras import CameraBase, detect_and_open_camera
from motors import _MotorBase, create_default_motor

from axial_app.theme import (
    FONT_FAMILY, FONT_MONO, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    FONT_SIZE_XL, FONT_SIZE_XXL,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    ACCENT_PRIMARY, ACCENT_SECONDARY,
    STATUS_GREEN, STATUS_RED, STATUS_AMBER,
    TEXT_PRIMARY_DARK, TEXT_SECONDARY_DARK,
    CROSSHAIR_COLOR, CROSSHAIR_FLASH,
    SIDEBAR_WIDTH,
)
from axial_app.widgets.collapsible_panel import CollapsiblePanel
from axial_app.widgets.numeric_display import NumericDisplay
from axial_app.widgets.progress_ring import ProgressRing
from axial_app.widgets.tooltip import Tooltip


class CapturePage(ct.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0)

        # Runtime device references
        self.camera: Optional[CameraBase] = None
        self.camera_backend: Optional[str] = None
        self.camera_thread: Optional[threading.Thread] = None
        self._camera_running: bool = False
        self._scan_active: bool = False
        self._feed_update_pending: bool = False
        self.motor: Optional[_MotorBase] = None

        # Per-page lock for camera access
        self.camera_lock = threading.Lock()

        # Camera operating parameters
        self.fps: int = config.DEFAULT_FPS
        self.current_exposure_us: int = config.DEFAULT_EXPOSURE_US
        self.current_gain: int = config.DEFAULT_GAIN

        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        '..', '..', 'config.yml')
        self.config_path = os.path.normpath(self.config_path)

        # Scan progress tracking
        self._scan_progress: float = 0.0

        # Last scan data (for export)
        self._last_z_positions: Optional[np.ndarray] = None
        self._last_intensities: Optional[list] = None
        self._last_figure = None
        self._last_tiff_path: Optional[str] = None

        # Output folder
        self._output_folder: Optional[str] = None

        # Crosshair flash state
        self._crosshair_flash_frames: int = 0

        # FPS tracking
        self._fps_times = []
        self._fps_display_value: float = 0.0

        # Placeholder for current PIL image
        self.current_image: Optional[Image.Image] = None

        # Interactive zoom & pixel selection state
        self.display_scale = 0.6
        self._last_disp_w = 1
        self._last_disp_h = 1

        self.zoom_enabled = True
        self.zoom_center = None
        self.zoom_radius_pct = 12.5

        self.hover_pixel = None
        self.selected_pixel = None

        # Scan status animation
        self._scan_dots = 0
        self._scan_dots_after_id = None

        # Silent auto-connect flag (no popups on startup failure)
        self._auto_connect_silent: bool = False

        # Scan capture state (camera_feed thread writes scan frames here)
        self._scan_buffer: Optional[np.ndarray] = None
        self._scan_capture_idx: int = 0
        self._scan_capture_total: int = 0
        self._scan_capturing: bool = False
        self._scan_capture_done: Optional[threading.Event] = None

        # Build the layout
        self._build_layout()

        # Auto-connect hardware on startup (after widget is mapped)
        self.after(500, self._auto_connect)

    def _build_layout(self):
        """Construct the full redesigned layout."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH)  # sidebar
        self.grid_columnconfigure(1, weight=1)  # main content

        # ---- SIDEBAR ----
        self._sidebar_visible = True
        self.sidebar = ct.CTkScrollableFrame(self, width=SIDEBAR_WIDTH - 20, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)

        # App title in sidebar
        self.logo_label = ct.CTkLabel(
            self.sidebar, text="Axial Resolution",
            font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_XXL, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=PAD_MD, pady=(PAD_LG, PAD_MD), sticky="ew")

        # --- System panel ---
        self._system_panel = CollapsiblePanel(self.sidebar, title="System", expanded=True)
        self._system_panel.grid(row=1, column=0, sticky="ew", padx=PAD_SM, pady=PAD_SM)

        self.system_on = ct.CTkButton(
            self._system_panel.content, text="Connect Hardware",
            command=self.turn_on, height=32,
            fg_color=ACCENT_PRIMARY,
        )
        self.system_on.grid(row=0, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")
        Tooltip(self.system_on, "Detect and connect camera + motor (Ctrl+H)")

        self.status_camera = ct.CTkLabel(
            self._system_panel.content, text="Camera: —",
            font=ct.CTkFont(size=FONT_SIZE_SM),
        )
        self.status_camera.grid(row=1, column=0, padx=PAD_MD, pady=PAD_SM, sticky="w")

        self.status_motor = ct.CTkLabel(
            self._system_panel.content, text="Motor: —",
            font=ct.CTkFont(size=FONT_SIZE_SM),
        )
        self.status_motor.grid(row=2, column=0, padx=PAD_MD, pady=PAD_SM, sticky="w")

        # --- Camera Settings panel ---
        self._camera_panel = CollapsiblePanel(self.sidebar, title="Camera Settings", expanded=True)
        self._camera_panel.grid(row=2, column=0, sticky="ew", padx=PAD_SM, pady=PAD_SM)

        ct.CTkLabel(
            self._camera_panel.content,
            text=f"Exposure (µs) [default: {config.DEFAULT_EXPOSURE_US}]",
            font=ct.CTkFont(size=FONT_SIZE_SM),
        ).grid(row=0, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.exposure_entry = ct.CTkEntry(
            self._camera_panel.content, placeholder_text="Enter exposure",
        )
        self.exposure_entry.grid(row=1, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")

        ct.CTkLabel(
            self._camera_panel.content,
            text=f"Gain [default: {config.DEFAULT_GAIN}]",
            font=ct.CTkFont(size=FONT_SIZE_SM),
        ).grid(row=2, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.gain_entry_widget = ct.CTkEntry(
            self._camera_panel.content, placeholder_text="Enter gain",
        )
        self.gain_entry_widget.grid(row=3, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")

        self._apply_settings_btn = ct.CTkButton(
            self._camera_panel.content, text="Apply Settings",
            command=self._apply_camera_settings, height=28,
        )
        self._apply_settings_btn.grid(row=4, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")

        self.clear_pixel_btn = ct.CTkButton(
            self._camera_panel.content, text="Use Center Pixel",
            command=self._clear_selected_pixel, height=28,
            fg_color="transparent", border_width=1,
        )
        self.clear_pixel_btn.grid(row=5, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")

        # --- Motor Controls panel ---
        self._motor_panel = CollapsiblePanel(self.sidebar, title="Motor Controls", expanded=True)
        self._motor_panel.grid(row=3, column=0, sticky="ew", padx=PAD_SM, pady=PAD_SM)

        ct.CTkLabel(
            self._motor_panel.content,
            text="(+) into sample  |  (-) away",
            font=ct.CTkFont(size=FONT_SIZE_SM, slant="italic"),
        ).grid(row=0, column=0, columnspan=2, padx=PAD_MD, pady=PAD_SM, sticky="w")

        motor_buttons = [
            ("+300µm", "300"),  ("+100µm", "100"),  ("+10µm", "10"),
            ("-10µm", "-10"),   ("-100µm", "-100"),  ("-300µm", "-300"),
        ]
        for i, (label, val) in enumerate(motor_buttons):
            col = 0 if i < 3 else 1
            row = (i % 3) + 1
            btn = ct.CTkButton(
                self._motor_panel.content, text=label,
                command=lambda v=val: self.button_motor(v),
                width=90, height=28,
                fg_color="transparent", border_width=1,
            )
            btn.grid(row=row, column=col, padx=PAD_SM, pady=PAD_SM, sticky="ew")

        self._motor_panel.content.grid_columnconfigure(0, weight=1)
        self._motor_panel.content.grid_columnconfigure(1, weight=1)

        # --- Scan Setup panel ---
        self._scan_panel = CollapsiblePanel(self.sidebar, title="Scan Setup", expanded=True)
        self._scan_panel.grid(row=4, column=0, sticky="ew", padx=PAD_SM, pady=PAD_SM)

        ct.CTkLabel(
            self._scan_panel.content, text="Folder Name:",
            font=ct.CTkFont(size=FONT_SIZE_SM),
        ).grid(row=0, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.name_entry = ct.CTkEntry(
            self._scan_panel.content, placeholder_text="Enter file name",
        )
        self.name_entry.grid(row=1, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")

        ct.CTkLabel(
            self._scan_panel.content, text="Scan Range Z (mm):",
            font=ct.CTkFont(size=FONT_SIZE_SM),
        ).grid(row=2, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.range_entry = ct.CTkEntry(
            self._scan_panel.content, placeholder_text="Enter range",
        )
        self.range_entry.grid(row=3, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")

        ct.CTkLabel(
            self._scan_panel.content, text="Axial Step Size (mm):",
            font=ct.CTkFont(size=FONT_SIZE_SM),
        ).grid(row=4, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.axial_entry = ct.CTkEntry(
            self._scan_panel.content, placeholder_text="Enter step size",
        )
        self.axial_entry.grid(row=5, column=0, padx=PAD_MD, pady=PAD_SM, sticky="ew")

        # ---- MAIN CONTENT AREA ----
        self.main = ct.CTkFrame(self, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(0, weight=4)   # camera feed — dominant
        self.main.grid_rowconfigure(1, weight=1)   # bottom section (compact)
        self.main.grid_columnconfigure(0, weight=1)

        # --- Camera Feed ---
        self.main_cam = ct.CTkFrame(self.main, corner_radius=6)
        self.main_cam.grid(row=0, column=0, padx=PAD_MD, pady=(PAD_MD, PAD_SM), sticky="nsew")
        self.main_cam.grid_rowconfigure(0, weight=1)
        self.main_cam.grid_rowconfigure(1, weight=0)
        self.main_cam.grid_rowconfigure(2, weight=0)
        self.main_cam.grid_columnconfigure(0, weight=1)

        self.camera_feed_label = ct.CTkLabel(
            self.main_cam, text="No Camera Connected\n\nClick 'Connect Hardware' to start",
            anchor="center",
            font=ct.CTkFont(size=FONT_SIZE_LG),
            text_color=("gray60", "gray40"),
        )
        self.camera_feed_label.grid(row=0, column=0, padx=PAD_SM, pady=PAD_SM, sticky="nsew")

        # Mouse interactions on main feed
        self.camera_feed_label.bind("<Motion>", self._on_feed_mouse_move)
        self.camera_feed_label.bind("<Leave>", self._on_feed_mouse_leave)
        self.camera_feed_label.bind("<Button-1>", self._on_feed_left_click)
        self.camera_feed_label.bind("<Shift-Button-1>", self._on_feed_shift_left_click)
        self.camera_feed_label.bind("<Button-3>", self._on_feed_right_click)
        self.camera_feed_label.bind("<MouseWheel>", self._on_feed_mouse_wheel)
        self.camera_feed_label.bind("<Button-4>", lambda e: self._adjust_zoom(-1))
        self.camera_feed_label.bind("<Button-5>", lambda e: self._adjust_zoom(+1))

        # Hover/selection info
        self.hover_label = ct.CTkLabel(
            self.main_cam, text="x: —, y: —",
            font=ct.CTkFont(family=FONT_MONO, size=FONT_SIZE_SM), anchor="w",
        )
        self.hover_label.grid(row=1, column=0, padx=PAD_MD, pady=(0, PAD_SM), sticky="ew")

        self.selected_label = ct.CTkLabel(
            self.main_cam, text="Selected axial pixel: center",
            font=ct.CTkFont(family=FONT_MONO, size=FONT_SIZE_SM), anchor="w",
        )
        self.selected_label.grid(row=2, column=0, padx=PAD_MD, pady=(0, PAD_SM), sticky="ew")

        # --- Bottom section: plot + zoom + results + controls ---
        self.bottom = ct.CTkFrame(self.main, corner_radius=0)
        self.bottom.grid(row=1, column=0, padx=PAD_MD, pady=(PAD_SM, PAD_MD), sticky="nsew")
        self.bottom.grid_rowconfigure(0, weight=1)
        self.bottom.grid_columnconfigure(0, weight=3)  # plot
        self.bottom.grid_columnconfigure(1, weight=2)  # right panel

        # Plot area
        self.graph_frame = ct.CTkFrame(self.bottom, corner_radius=6)
        self.graph_frame.grid(row=0, column=0, padx=(0, PAD_SM), pady=0, sticky="nsew")

        self._plot_placeholder = ct.CTkLabel(
            self.graph_frame, text="Axial Resolution Plot\n(run a scan to see results)",
            font=ct.CTkFont(size=FONT_SIZE_MD),
            text_color=("gray60", "gray40"),
        )
        self._plot_placeholder.pack(expand=True)

        # Right panel: zoom + results + controls
        self.right_panel = ct.CTkFrame(self.bottom, corner_radius=0, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.right_panel.grid_rowconfigure(0, weight=2)  # zoom
        self.right_panel.grid_rowconfigure(1, weight=1)  # results
        self.right_panel.grid_rowconfigure(2, weight=0)  # scan controls
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Zoom window
        self.zoom_frame = ct.CTkFrame(self.right_panel, corner_radius=6)
        self.zoom_frame.grid(row=0, column=0, pady=(0, PAD_SM), sticky="nsew")
        self.zoom_frame.grid_rowconfigure(0, weight=0)
        self.zoom_frame.grid_rowconfigure(1, weight=1)
        self.zoom_frame.grid_columnconfigure(0, weight=1)
        self.zoom_frame.grid_columnconfigure(1, weight=0)

        ct.CTkLabel(
            self.zoom_frame, text="Zoom",
            font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_MD, weight="bold"),
        ).grid(row=0, column=0, padx=PAD_MD, pady=PAD_SM, sticky="w")

        self.zoom_feed_label = ct.CTkLabel(self.zoom_frame, text="")
        self.zoom_feed_label.grid(row=1, column=0, padx=PAD_SM, pady=PAD_SM, sticky="nsew")

        self.zoom_scale = ct.CTkSlider(
            self.zoom_frame, orientation="vertical",
            from_=25, to=1, command=self.resize,
        )
        self.zoom_scale.set(12.5)
        self.zoom_scale.grid(row=1, column=1, padx=PAD_SM, pady=PAD_SM, sticky="ns")

        # Results section
        self.result_frame = ct.CTkFrame(self.right_panel, corner_radius=6)
        self.result_frame.grid(row=1, column=0, pady=(0, PAD_SM), sticky="nsew")
        self.result_frame.grid_columnconfigure(0, weight=1)

        ct.CTkLabel(
            self.result_frame, text="Results",
            font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_MD, weight="bold"),
        ).grid(row=0, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.fwhm_display = NumericDisplay(
            self.result_frame, label="FWHM", unit="mm",
        )
        self.fwhm_display.grid(row=1, column=0, padx=PAD_SM, pady=PAD_SM, sticky="ew")

        self.peak_display = NumericDisplay(
            self.result_frame, label="Peak Intensity", unit="",
        )
        self.peak_display.grid(row=2, column=0, padx=PAD_SM, pady=(0, PAD_SM), sticky="ew")

        # Scan controls (calculate button + progress)
        self.control_frame = ct.CTkFrame(self.right_panel, corner_radius=6)
        self.control_frame.grid(row=2, column=0, sticky="ew")
        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=0)

        self.calculate_button = ct.CTkButton(
            self.control_frame, text="Calculate",
            command=self.axial, height=36,
            font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_MD, weight="bold"),
            fg_color=ACCENT_PRIMARY,
        )
        self.calculate_button.grid(row=0, column=0, padx=PAD_MD, pady=PAD_MD, sticky="ew")
        Tooltip(self.calculate_button, "Start axial resolution scan")

        self.progress_ring = ProgressRing(self.control_frame, size=36)
        self.progress_ring.grid(row=0, column=1, padx=(0, PAD_MD), pady=PAD_MD)

        self.scan_status_label = ct.CTkLabel(
            self.control_frame, text="Ready",
            font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_SM),
        )
        self.scan_status_label.grid(row=1, column=0, columnspan=2, padx=PAD_MD, pady=(0, PAD_MD), sticky="w")

    # ========================================================================
    # Shutdown / device lifecycle (preserved exactly)
    # ========================================================================

    def _shutdown_devices(self) -> None:
        """Stop camera thread, close camera, and shut down motor. Idempotent."""
        self._camera_running = False
        if self.camera_thread is not None and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=2.0)
        self.camera_thread = None
        if self.camera is not None:
            try:
                self.camera.close()
            except Exception as e:
                print("Error closing camera:", e)
            self.camera = None
        if self.motor is not None:
            try:
                self.motor.shutdown()
            except Exception as e:
                print("Error shutting down motor:", e)
            self.motor = None
        self.status_camera.configure(text="Camera: —")
        self.status_motor.configure(text="Motor: —")
        # Update status bar if available
        app = self._get_app()
        if app and hasattr(app, 'status_bar'):
            app.status_bar.set_camera(None)
            app.status_bar.set_motor(None)

    def _get_app(self):
        """Get reference to the App root window."""
        try:
            return self.winfo_toplevel()
        except Exception:
            return None

    # ========================================================================
    # System init (preserved logic)
    # ========================================================================

    def turn_on(self):
        """Auto-detect and connect camera and motor, then start the camera thread."""
        if self.camera is not None or self.motor is not None:
            self._shutdown_devices()

        self.system_on.configure(state="disabled", text="Connecting...")
        app = self._get_app()

        # Camera
        if app and hasattr(app, 'status_bar'):
            app.status_bar.set_camera_connecting()

        cam_obj, backend = detect_and_open_camera(
            exposure_us=self.current_exposure_us,
            gain=self.current_gain,
            fps=self.fps,
        )
        if cam_obj is None or backend is None:
            self.system_on.configure(state="normal", text="Connect Hardware")
            if not self._auto_connect_silent:
                self.show_warning_popup(
                    "No camera detected. Please connect a Player One, Allied Vision Alvium, "
                    "or Basler camera."
                )
            if app and hasattr(app, 'status_bar'):
                app.status_bar.set_camera(None)
            return

        self.camera = cam_obj
        self.camera_backend = backend
        self.status_camera.configure(text=f"Camera: {backend}")
        print(f"[SYS] Camera: {backend}")

        if app and hasattr(app, 'status_bar'):
            app.status_bar.set_camera(backend)

        # Start camera thread
        self._camera_running = True
        self.camera_thread = threading.Thread(target=self.camera_feed, daemon=True)
        self.camera_thread.start()

        # Motor
        if app and hasattr(app, 'status_bar'):
            app.status_bar.set_motor_connecting()

        try:
            self.motor = create_default_motor(config_path=self.config_path)
            motor_name = type(self.motor).__name__.replace("Motor", "")
            self.status_motor.configure(text=f"Motor: {motor_name}")
            print(f"[SYS] Motor: {motor_name}")
            if app and hasattr(app, 'status_bar'):
                app.status_bar.set_motor(motor_name)
        except Exception as e:
            self.status_motor.configure(text="Motor: not detected")
            print(f"[SYS] Motor not detected: {e}")
            if not self._auto_connect_silent:
                self.show_warning_popup(f"Motor not detected: {e}")
            if app and hasattr(app, 'status_bar'):
                app.status_bar.set_motor(None)

        self.system_on.configure(state="normal", text="Reconnect Hardware")

    def _auto_connect(self):
        """Auto-connect hardware on startup (silent — no popups on failure)."""
        self._auto_connect_silent = True
        self.turn_on()
        self._auto_connect_silent = False

    # Aliases for menu/toolbar
    def connect_hardware(self):
        self.turn_on()

    def disconnect_hardware(self):
        self._shutdown_devices()

    # ========================================================================
    # Appearance / misc (preserved)
    # ========================================================================

    def resize(self, zoom):
        self.zoom_radius_pct = float(zoom)
        return self.zoom_radius_pct

    def toggle_theme(self):
        current = ct.get_appearance_mode()
        new_mode = "Light" if current == "Dark" else "Dark"
        ct.set_appearance_mode(new_mode)

    def toggle_sidebar(self):
        if self._sidebar_visible:
            self.sidebar.grid_forget()
            self.grid_columnconfigure(0, weight=0, minsize=0)
        else:
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH)
        self._sidebar_visible = not self._sidebar_visible

    def toggle_status_bar(self):
        app = self._get_app()
        if app and hasattr(app, '_toggle_status_bar'):
            app._toggle_status_bar()

    # ========================================================================
    # Popups (preserved)
    # ========================================================================

    def show_confirmed(self, note):
        confirm = ct.CTkToplevel()
        confirm.title("Confirmation")
        confirm.grab_set()
        ok_label = ct.CTkLabel(confirm, text=note, wraplength=350)
        ok_label.pack(padx=10, pady=10)
        ok_button = ct.CTkButton(confirm, text="OK", command=confirm.destroy)
        ok_button.pack(pady=10)
        confirm.update_idletasks()
        confirm.minsize(300, 100)

    def show_warning_popup(self, message):
        popup = ct.CTkToplevel()
        popup.title("Warning")
        popup.grab_set()
        label = ct.CTkLabel(popup, text=message, wraplength=350)
        label.pack(padx=10, pady=10)
        button = ct.CTkButton(popup, text="OK", command=popup.destroy)
        button.pack(pady=10)
        popup.update_idletasks()
        popup.minsize(300, 100)

    def _clear_selected_pixel(self):
        self.selected_pixel = None
        self.selected_label.configure(text="Selected axial pixel: center")

    # ========================================================================
    # Mouse interactions (preserved exactly)
    # ========================================================================

    def _disp_to_fullres(self, ex: int, ey: int):
        if self.current_image is None:
            return None
        img_w, img_h = self.current_image.size
        disp_w = max(1, int(img_w * self.display_scale))
        disp_h = max(1, int(img_h * self.display_scale))
        w = max(1, self.camera_feed_label.winfo_width())
        h = max(1, self.camera_feed_label.winfo_height())
        off_x = max(0, (w - disp_w) // 2)
        off_y = max(0, (h - disp_h) // 2)
        ix = ex - off_x
        iy = ey - off_y
        if ix < 0 or iy < 0 or ix >= disp_w or iy >= disp_h:
            return None
        fx = int(round(ix * (img_w / disp_w)))
        fy = int(round(iy * (img_h / disp_h)))
        fx = max(0, min(img_w - 1, fx))
        fy = max(0, min(img_h - 1, fy))
        return fx, fy

    def _on_feed_mouse_move(self, event):
        p = self._disp_to_fullres(event.x, event.y)
        if p is None:
            return
        self.hover_pixel = p
        self.hover_label.configure(text=f"x: {p[0]}, y: {p[1]}")

    def _on_feed_mouse_leave(self, event):
        self.hover_pixel = None
        self.hover_label.configure(text="x: —, y: —")

    def _on_feed_left_click(self, event):
        p = self._disp_to_fullres(event.x, event.y)
        if p is None:
            return
        self.zoom_center = p

    def _on_feed_shift_left_click(self, event):
        p = self._disp_to_fullres(event.x, event.y)
        if p is None:
            return
        self.selected_pixel = p
        self.selected_label.configure(text=f"Selected axial pixel: x={p[0]}, y={p[1]}")
        self._crosshair_flash_frames = 3

    def _on_feed_right_click(self, event):
        self.zoom_center = None
        self.zoom_radius_pct = 12.5
        self.zoom_scale.set(self.zoom_radius_pct)
        self.selected_label.configure(
            text=("Selected axial pixel: center" if self.selected_pixel is None
                  else f"Selected axial pixel: x={self.selected_pixel[0]}, y={self.selected_pixel[1]}")
        )

    def _on_feed_mouse_wheel(self, event):
        direction = -1 if event.delta > 0 else +1
        self._adjust_zoom(direction)

    def _adjust_zoom(self, direction: int):
        step = 1.0
        new_pct = float(self.zoom_radius_pct) + (step * direction)
        new_pct = max(1.0, min(25.0, new_pct))
        self.zoom_radius_pct = new_pct
        try:
            self.zoom_scale.set(new_pct)
        except Exception:
            pass

    # ========================================================================
    # Camera parameters (preserved)
    # ========================================================================

    def change_exposure(self):
        if self.camera is None:
            self.show_warning_popup("Camera not initialized.")
            return
        try:
            value = int(self.exposure_entry.get())
            self.current_exposure_us = value
            self.camera.set_exposure(value)
            print("Exposure set to:", value, "µs")
        except ValueError:
            self.show_warning_popup("Invalid exposure value. Please enter an integer.")

    def change_gain(self):
        if self.camera is None:
            self.show_warning_popup("Camera not initialized.")
            return
        try:
            gain_value = int(self.gain_entry_widget.get())
            self.current_gain = gain_value
            self.camera.set_gain(gain_value)
            print("Gain set to:", gain_value)
        except ValueError:
            self.show_warning_popup("Invalid gain value. Please enter an integer.")

    def _apply_camera_settings(self):
        """Apply both exposure and gain at once."""
        if self.camera is None:
            self.show_warning_popup("Camera not initialized.")
            return
        try:
            exp_text = self.exposure_entry.get()
            gain_text = self.gain_entry_widget.get()
            if exp_text:
                exposure = int(exp_text)
                self.current_exposure_us = exposure
                self.camera.set_exposure(exposure)
            if gain_text:
                gain = int(gain_text)
                self.current_gain = gain
                self.camera.set_gain(gain)
            self.show_confirmed("Camera settings applied.")
        except ValueError:
            self.show_warning_popup("Invalid input. Please enter integer values.")

    def show_camera_settings(self):
        """Open camera settings — just expand the panel and focus."""
        if not self._camera_panel.expanded:
            self._camera_panel.expand()
        self.exposure_entry.focus_set()

    # ========================================================================
    # Axial scan (preserved logic exactly, with progress tracking added)
    # ========================================================================

    def axial(self):
        """Validate inputs then launch scan worker thread (non-blocking)."""
        if self.camera is None:
            self.show_warning_popup("Camera not initialized.")
            return

        user_video_name = self.name_entry.get()
        if not user_video_name:
            self.show_warning_popup("Folder name cannot be empty.")
            return

        if not (self.range_entry.get() and self.axial_entry.get()):
            self.show_warning_popup("Please provide all necessary inputs.")
            return

        try:
            range_mm = float(self.range_entry.get())
            step_mm = float(self.axial_entry.get())
        except ValueError:
            self.show_warning_popup("Invalid input. Please try again!")
            return

        scan_speed = step_mm * self.fps
        if scan_speed < 0.001:
            self.show_warning_popup(
                f"Scan speed ({scan_speed:.4f} mm/s) too slow. Increase step size."
            )
            return

        Frames = int(round(abs(range_mm / step_mm)))
        if Frames < 3:
            self.show_warning_popup("Too few frames. Reduce step size or increase range.")
            return

        img_w, img_h = self.camera.get_size()
        if img_w <= 0 or img_h <= 0:
            self.show_warning_popup("Invalid camera image size.")
            return

        # Build save path
        save_folder = self._output_folder or os.path.dirname(os.path.abspath(__file__))
        if self._output_folder is None:
            save_folder = os.path.join(save_folder, '..', '..')
            save_folder = os.path.normpath(save_folder)
        axial_folder = os.path.join(save_folder, user_video_name)
        video_folder = os.path.join(axial_folder, "Axial Resolution Measurement")
        os.makedirs(video_folder, exist_ok=True)
        base_filename = (
            f"{user_video_name}_exp_{self.current_exposure_us}"
            f"_gain_{self.current_gain}_ss_{step_mm}"
        )
        i = 1
        while True:
            video_filename = f"{base_filename}_{i:03}.tiff"
            if not os.path.exists(os.path.join(video_folder, video_filename)):
                break
            i += 1
        tiff_path = os.path.join(video_folder, video_filename)

        # Lock UI and start scan
        self.calculate_button.configure(state="disabled")
        self._scan_progress = 0.0
        self.progress_ring.set_indeterminate()
        self._start_scan_status_animation()
        self._scan_active = True

        app = self._get_app()
        if app and hasattr(app, 'status_bar'):
            app.status_bar.set_status("Scanning...")

        threading.Thread(
            target=self._axial_worker,
            args=(range_mm, step_mm, Frames, img_w, img_h, tiff_path),
            daemon=True,
        ).start()

    def _axial_worker(self, range_mm, step_mm, Frames, img_w, img_h, tiff_path):
        """Background thread: run motor scan, capture frames, compute FWHM.

        Frames are captured by the camera_feed thread (which stays live) via
        the shared _scan_buffer. This worker just coordinates the motor and
        waits for capture completion.
        """
        # Prepare scan buffer for camera_feed thread to fill
        self._scan_buffer = np.zeros((Frames, img_h, img_w), dtype=np.uint8)
        self._scan_capture_idx = 0
        self._scan_capture_total = Frames
        self._scan_capture_done = threading.Event()
        self._scan_capturing = False  # will be enabled after ramp

        scan_started = threading.Event()

        def move_motor():
            if self.motor is None:
                scan_started.set()
                return
            def signal():
                scan_started.set()
            try:
                self.motor.perform_sawtooth_scan(range_mm, step_mm, self.fps,
                                                  on_scan_start=signal)
            except AttributeError:
                scan_speed_l = step_mm * self.fps
                half = range_mm / 2.0
                self.motor.move_rel_mm(+half, speed_mm_s=min(scan_speed_l * 2, 2.0))
                signal()
                self.motor.move_rel_mm(-range_mm, speed_mm_s=scan_speed_l)
                self.motor.move_rel_mm(+half, speed_mm_s=min(scan_speed_l * 2, 2.0))

        motor_thread = threading.Thread(target=move_motor, daemon=True)
        motor_thread.start()

        # Wait for scan start signal, then sleep through motor acceleration ramp
        scan_started.wait()

        # Switch to determinate progress
        self.after(0, lambda: self.progress_ring.set_determinate(0.0))

        scan_speed = step_mm * self.fps
        ramp_time_s = scan_speed / config.MOTOR_ACCEL_MM_S2
        sleep(ramp_time_s)

        # Enable scan capture — camera_feed thread will start filling the buffer
        print("[AXIAL] Capturing frames:", Frames)
        t1 = time()
        self._scan_capturing = True

        # Wait for camera_feed thread to capture all frames
        timeout_s = max(Frames * 2.0 / max(self.fps, 1), 60.0)
        self._scan_capture_done.wait(timeout=timeout_s)
        print(f"[AXIAL] Capture done in {time() - t1:.2f}s")

        buffer = self._scan_buffer
        self._scan_buffer = None
        self._scan_capturing = False

        motor_thread.join(timeout=30.0)

        # Save TIFF
        self.after(0, lambda: self.scan_status_label.configure(text="Saving..."))
        app = self._get_app()
        if app and hasattr(app, 'status_bar'):
            self.after(0, lambda: app.status_bar.set_status("Saving..."))

        if len(buffer) > 1:
            pil_images = [Image.fromarray(fr) for fr in buffer]
            pil_images[0].save(tiff_path, save_all=True, append_images=pil_images[1:],
                               compression="tiff_deflate")
            print(f"[AXIAL] TIFF saved: {tiff_path}")

        self._last_tiff_path = tiff_path

        # FWHM calculation (preserved exactly)
        px = img_w // 2 if self.selected_pixel is None else int(self.selected_pixel[0])
        py = img_h // 2 if self.selected_pixel is None else int(self.selected_pixel[1])
        px = max(0, min(img_w - 1, px))
        py = max(0, min(img_h - 1, py))

        intensities = [frame[py, px] for frame in buffer]
        z_positions = np.arange(Frames) * step_mm

        peak_intensity = float(np.max(intensities))
        half_max = peak_intensity / 2.0
        intensities_arr = np.array(intensities, dtype=float)
        above_half = np.where(intensities_arr >= half_max)[0]

        truncated = False
        fwhm_z = 0.0
        if len(above_half) > 1:
            left, right = above_half[0], above_half[-1]
            if left == 0 or right == len(intensities_arr) - 1:
                truncated = True
            if left > 0:
                x0, x1 = z_positions[left - 1], z_positions[left]
                y0, y1 = intensities_arr[left - 1], intensities_arr[left]
                left_cross = x0 + (half_max - y0) * (x1 - x0) / (y1 - y0)
            else:
                left_cross = z_positions[left]
            if right < len(intensities_arr) - 1:
                x0, x1 = z_positions[right], z_positions[right + 1]
                y0, y1 = intensities_arr[right], intensities_arr[right + 1]
                right_cross = x0 + (half_max - y0) * (x1 - x0) / (y1 - y0)
            else:
                right_cross = z_positions[right]
            fwhm_z = float(right_cross - left_cross)

        del buffer

        # Store for export
        self._last_z_positions = z_positions
        self._last_intensities = intensities

        # All GUI updates via after()
        def _finish():
            # Update numeric displays
            suffix = "(truncated)" if truncated else ""
            self.fwhm_display.set_value(fwhm_z, suffix=suffix)
            self.peak_display.set_value(peak_intensity)

            # Plot
            fig, ax = plt.subplots(figsize=(5, 3))
            ax.plot(z_positions, intensities, marker='o', markersize=3,
                    color=ACCENT_PRIMARY, linewidth=1.5)
            ax.set_xlabel('Z Position (mm)')
            ax.set_ylabel('Pixel Intensity')
            ax.set_title('Axial Resolution Scan')
            ax.grid(True, alpha=0.3)
            fig.tight_layout()

            self._last_figure = fig

            for w in self.graph_frame.winfo_children():
                w.destroy()
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)

            # Re-enable UI
            self.calculate_button.configure(state="normal")
            self.progress_ring.set_idle()
            self._stop_scan_status_animation()
            self.scan_status_label.configure(text="Complete")
            self._scan_active = False

            app = self._get_app()
            if app and hasattr(app, 'status_bar'):
                app.status_bar.set_status("Complete")

        self.after(0, _finish)

    # ========================================================================
    # Scan status animation
    # ========================================================================

    def _start_scan_status_animation(self):
        self._scan_dots = 0
        self._scan_status_tick()

    def _scan_status_tick(self):
        self._scan_dots = (self._scan_dots + 1) % 4
        dots = "." * self._scan_dots
        self.scan_status_label.configure(text=f"Scanning{dots}")
        self._scan_dots_after_id = self.after(500, self._scan_status_tick)

    def _stop_scan_status_animation(self):
        if self._scan_dots_after_id is not None:
            self.after_cancel(self._scan_dots_after_id)
            self._scan_dots_after_id = None

    # ========================================================================
    # Export / save methods (new for menu/toolbar)
    # ========================================================================

    def save_last_scan(self):
        if self._last_tiff_path and os.path.exists(self._last_tiff_path):
            self.show_confirmed(f"Last scan saved at:\n{self._last_tiff_path}")
        else:
            self.show_warning_popup("No scan data to save.")

    def export_plot_png(self):
        from axial_app.dialogs.export_dialog import export_plot_png
        path = export_plot_png(self, self._last_figure)
        if path:
            self.show_confirmed(f"Plot exported to:\n{path}")

    def export_csv(self):
        from axial_app.dialogs.export_dialog import export_csv
        path = export_csv(self, self._last_z_positions, self._last_intensities)
        if path:
            self.show_confirmed(f"Data exported to:\n{path}")

    def change_output_folder(self):
        folder = filedialog.askdirectory(parent=self, title="Select Output Folder")
        if folder:
            self._output_folder = folder
            self.show_confirmed(f"Output folder set to:\n{folder}")

    def show_about(self):
        from axial_app.dialogs.about_dialog import show_about
        show_about(self)

    def show_shortcuts(self):
        popup = ct.CTkToplevel(self)
        popup.title("Keyboard Shortcuts")
        popup.geometry("320x240")
        popup.grab_set()
        popup.transient(self)

        shortcuts = [
            ("Ctrl+H", "Connect Hardware"),
            ("Ctrl+S", "Save Last Scan"),
            ("Ctrl+D", "Toggle Dark/Light Mode"),
            ("Ctrl+Q", "Exit"),
            ("Shift+Click", "Select axial pixel"),
            ("Right Click", "Reset zoom"),
            ("Mouse Wheel", "Adjust zoom level"),
        ]

        for i, (key, desc) in enumerate(shortcuts):
            ct.CTkLabel(
                popup, text=key,
                font=ct.CTkFont(family=FONT_MONO, size=FONT_SIZE_SM, weight="bold"),
                anchor="e", width=100,
            ).grid(row=i, column=0, padx=(PAD_LG, PAD_SM), pady=PAD_SM, sticky="e")
            ct.CTkLabel(
                popup, text=desc,
                font=ct.CTkFont(size=FONT_SIZE_SM), anchor="w",
            ).grid(row=i, column=1, padx=(PAD_SM, PAD_LG), pady=PAD_SM, sticky="w")

    # ========================================================================
    # Motor quick buttons (preserved)
    # ========================================================================

    def button_motor(self, button_text):
        if self.motor is None:
            self.show_warning_popup("Motor is not connected.")
            return
        if self._scan_active:
            self.show_warning_popup("Cannot move motor during an active scan.")
            return
        try:
            dz_mm = float(button_text) / 1000.0
        except Exception as e:
            self.show_warning_popup(f"Motor move failed: {e}")
            return

        def _do_move():
            try:
                self.motor.move_rel_mm(dz_mm, speed_mm_s=0.5)
            except Exception as e:
                self.after(0, lambda: self.show_warning_popup(f"Motor move failed: {e}"))

        threading.Thread(target=_do_move, daemon=True).start()

    # ========================================================================
    # Camera live view (preserved logic, with crosshair overlay + FPS tracking)
    # ========================================================================

    def _update_feed_display(self, imgtk, imgtkN):
        """Called on the main thread only via self.after()."""
        self._feed_update_pending = False
        self.camera_feed_label.configure(image=imgtk)
        self.camera_feed_label.imgtk = imgtk
        if imgtkN is not None:
            self.zoom_feed_label.configure(image=imgtkN)
            self.zoom_feed_label.img = imgtkN

    def camera_feed(self):
        """
        Continuous camera loop. Grabs frames from whichever backend is active,
        shows them in the GUI, and updates the zoom window.
        Feed stays live during scans — scan frames are captured here too.
        """
        frame_count = 0
        fps_start = perf_counter()

        while self._camera_running and self.camera is not None:
            frame = self.camera.get_frame(timeout_ms=100)
            if frame is None:
                sleep(0.001)
                continue

            # If scan is capturing, store frame in the scan buffer
            if self._scan_capturing and self._scan_buffer is not None:
                scan_frame = frame
                if scan_frame.ndim == 3:
                    scan_frame = scan_frame[:, :, 0]
                scan_frame = scan_frame.astype(np.uint8)
                idx = self._scan_capture_idx
                if idx < self._scan_capture_total:
                    sh, sw = self._scan_buffer.shape[1], self._scan_buffer.shape[2]
                    if scan_frame.shape != (sh, sw):
                        scan_frame = cv2.resize(scan_frame, (sw, sh))
                    self._scan_buffer[idx] = scan_frame
                    self._scan_capture_idx = idx + 1
                    self._scan_progress = (idx + 1) / self._scan_capture_total
                    self.after(0, lambda p=self._scan_progress: self.progress_ring.set_progress(p))
                    if idx + 1 >= self._scan_capture_total:
                        self._scan_capturing = False
                        if self._scan_capture_done is not None:
                            self._scan_capture_done.set()

            # FPS tracking
            frame_count += 1
            elapsed = perf_counter() - fps_start
            if elapsed >= 1.0:
                self._fps_display_value = frame_count / elapsed
                frame_count = 0
                fps_start = perf_counter()
                fps_val = self._fps_display_value
                def _update_fps(v=fps_val):
                    app = self._get_app()
                    if app and hasattr(app, 'status_bar'):
                        app.status_bar.set_fps(v)
                self.after(0, _update_fps)

            # Ensure grayscale uint8 2D
            if frame.ndim == 3:
                frame = frame[:, :, 0]
            frame = frame.astype(np.uint8)

            img_h, img_w = frame.shape[:2]

            # Convert to PIL for display
            img = Image.fromarray(frame)
            self.current_image = img

            # Draw crosshair on display copy if pixel is selected
            display_img = img.copy()
            if self.selected_pixel is not None:
                draw = ImageDraw.Draw(display_img)
                sx, sy = self.selected_pixel
                color = CROSSHAIR_FLASH if self._crosshair_flash_frames > 0 else CROSSHAIR_COLOR
                if self._crosshair_flash_frames > 0:
                    self._crosshair_flash_frames -= 1
                # Horizontal line
                draw.line([(0, sy), (img_w - 1, sy)], fill=color, width=1)
                # Vertical line
                draw.line([(sx, 0), (sx, img_h - 1)], fill=color, width=1)

            # Scale image to fit the camera feed container, preserving aspect ratio
            container_w = max(1, self.camera_feed_label.winfo_width())
            container_h = max(1, self.camera_feed_label.winfo_height())
            # Fit within container while keeping aspect ratio
            scale_w = container_w / img_w
            scale_h = container_h / img_h
            scaling_factor = min(scale_w, scale_h)  # fill container, no cap
            scaling_factor = max(scaling_factor, 0.1)  # safety floor
            self.display_scale = scaling_factor
            new_size = (int(img_w * scaling_factor), int(img_h * scaling_factor))
            imgtk = ct.CTkImage(light_image=display_img, size=new_size)

            # Zoom window — scale to fit the zoom container too
            zoom_container_w = max(1, self.zoom_feed_label.winfo_width())
            zoom_container_h = max(1, self.zoom_feed_label.winfo_height())

            if self.zoom_center is None:
                centerX, centerY = img_w // 2, img_h // 2
            else:
                centerX, centerY = int(self.zoom_center[0]), int(self.zoom_center[1])

            radiusX = int(self.zoom_radius_pct * img_w / 100)
            radiusY = int(self.zoom_radius_pct * img_h / 100)

            minX, maxX = max(0, centerX - radiusX), min(img_w, centerX + radiusX)
            minY, maxY = max(0, centerY - radiusY), min(img_h, centerY + radiusY)

            imgtkN = None
            if maxX > minX and maxY > minY:
                zoomed_img_np = frame[minY:maxY, minX:maxX]
                imHN = cv2.resize(zoomed_img_np, (img_w, img_h))
                imgN_pil = Image.fromarray(imHN)
                zoom_size = (min(zoom_container_w, img_w), min(zoom_container_h, img_h))
                imgtkN = ct.CTkImage(light_image=imgN_pil, size=zoom_size)

            # Schedule GUI update on main thread, skip if one is already pending
            if not self._feed_update_pending:
                self._feed_update_pending = True
                self.after(0, self._update_feed_display, imgtk, imgtkN)
