"""
Native Tkinter menu bar: File, View, Tools, Help.

CustomTkinter has no menu bar widget, so we use Tkinter's native Menu.
"""

from __future__ import annotations

from tkinter import Menu
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from axial_app.main import App


def create_menu_bar(app: App) -> Menu:
    """Create and attach the menu bar to the app window."""
    menubar = Menu(app, tearoff=0)

    # ---- File ----
    file_menu = Menu(menubar, tearoff=0)
    file_menu.add_command(label="Save Last Scan", accelerator="Ctrl+S",
                          command=lambda: _safe_call(app, "save_last_scan"))
    file_menu.add_command(label="Export Plot as PNG...",
                          command=lambda: _safe_call(app, "export_plot_png"))
    file_menu.add_command(label="Export Data as CSV...",
                          command=lambda: _safe_call(app, "export_csv"))
    file_menu.add_separator()
    file_menu.add_command(label="Change Output Folder...",
                          command=lambda: _safe_call(app, "change_output_folder"))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", accelerator="Ctrl+Q",
                          command=app._on_window_close)
    menubar.add_cascade(label="File", menu=file_menu)

    # ---- View ----
    view_menu = Menu(menubar, tearoff=0)
    view_menu.add_command(label="Toggle Dark/Light Mode", accelerator="Ctrl+D",
                          command=lambda: _safe_call(app, "toggle_theme"))
    view_menu.add_command(label="Toggle Sidebar",
                          command=lambda: _safe_call(app, "toggle_sidebar"))
    view_menu.add_command(label="Toggle Status Bar",
                          command=lambda: _safe_call(app, "toggle_status_bar"))
    menubar.add_cascade(label="View", menu=view_menu)

    # ---- Tools ----
    tools_menu = Menu(menubar, tearoff=0)
    tools_menu.add_command(label="Connect Hardware", accelerator="Ctrl+H",
                           command=lambda: _safe_call(app, "connect_hardware"))
    tools_menu.add_command(label="Disconnect",
                           command=lambda: _safe_call(app, "disconnect_hardware"))
    tools_menu.add_separator()
    tools_menu.add_command(label="Camera Settings...",
                           command=lambda: _safe_call(app, "show_camera_settings"))
    menubar.add_cascade(label="Tools", menu=tools_menu)

    # ---- Help ----
    help_menu = Menu(menubar, tearoff=0)
    help_menu.add_command(label="Keyboard Shortcuts",
                          command=lambda: _safe_call(app, "show_shortcuts"))
    help_menu.add_separator()
    help_menu.add_command(label="About...",
                          command=lambda: _safe_call(app, "show_about"))
    menubar.add_cascade(label="Help", menu=help_menu)

    app.configure(menu=menubar)

    # Keyboard shortcuts
    app.bind_all("<Control-q>", lambda e: app._on_window_close())
    app.bind_all("<Control-s>", lambda e: _safe_call(app, "save_last_scan"))
    app.bind_all("<Control-d>", lambda e: _safe_call(app, "toggle_theme"))
    app.bind_all("<Control-h>", lambda e: _safe_call(app, "connect_hardware"))

    return menubar


def _safe_call(app: App, method_name: str) -> None:
    """Call a method on the app's capture page if it exists."""
    page = app.capture_page
    if page and hasattr(page, method_name):
        getattr(page, method_name)()
