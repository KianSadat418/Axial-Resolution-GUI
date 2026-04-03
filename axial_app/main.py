"""
Main application window.

Sets up the window, menu bar, toolbar, status bar, and hosts the CapturePage.
No MainMenu page — the app opens directly to the capture/measurement interface.
"""

from __future__ import annotations

import os
import customtkinter as ct

from axial_app.theme import (
    FONT_FAMILY, STATUSBAR_HEIGHT, PAD_SM,
    ACCENT_PRIMARY, BG_DARKEST,
)
from axial_app.pages.capture_page import CapturePage
from axial_app.widgets.status_bar import StatusBar
from axial_app.widgets.toolbar import Toolbar, ICONS
from axial_app.menu_bar import create_menu_bar


# Default to dark mode
ct.set_appearance_mode("Dark")
ct.set_default_color_theme("blue")


class App(ct.CTk):
    def __init__(self):
        super().__init__()
        self.title("Axial Resolution Measurement")
        self.minsize(900, 650)
        self.geometry("1400x900")

        # Try to set icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'app_icon.ico')
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # Layout: toolbar | content | status bar
        self.grid_rowconfigure(0, weight=0)  # toolbar
        self.grid_rowconfigure(1, weight=1)  # content
        self.grid_rowconfigure(2, weight=0)  # status bar
        self.grid_columnconfigure(0, weight=1)

        # Toolbar
        self.toolbar = Toolbar(self)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        # Capture page (main content)
        self.capture_page = CapturePage(self)
        self.capture_page.grid(row=1, column=0, sticky="nsew")

        # Status bar
        self._status_bar_visible = True
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, sticky="ew")

        # Menu bar
        self._menu_bar = create_menu_bar(self)

        # Toolbar buttons
        self._setup_toolbar()

        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _setup_toolbar(self):
        """Add buttons to the toolbar."""
        self.toolbar.add_button(
            ICONS["connect"], "Connect Hardware (Ctrl+H)",
            self.capture_page.connect_hardware,
        )
        self.toolbar.add_button(
            ICONS["scan"], "Start Scan",
            self.capture_page.axial,
        )
        self.toolbar.add_separator()
        self.toolbar.add_button(
            ICONS["save"], "Save Last Scan (Ctrl+S)",
            self.capture_page.save_last_scan,
        )
        self.toolbar.add_button(
            ICONS["export"], "Export...",
            self.capture_page.export_plot_png,
        )
        self.toolbar.add_spacer()
        self.toolbar.add_button(
            ICONS["theme"], "Toggle Dark/Light Mode (Ctrl+D)",
            self.capture_page.toggle_theme,
        )

    def _on_window_close(self) -> None:
        """Clean up devices and exit."""
        self.capture_page._shutdown_devices()
        self.destroy()
        os._exit(0)

    def _toggle_status_bar(self) -> None:
        if self._status_bar_visible:
            self.status_bar.grid_forget()
        else:
            self.status_bar.grid(row=2, column=0, sticky="ew")
        self._status_bar_visible = not self._status_bar_visible


def main():
    app = App()
    app.resizable(True, True)
    app.mainloop()


if __name__ == "__main__":
    main()
