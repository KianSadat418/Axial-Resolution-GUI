"""
About dialog — app name, version, author info.
"""

from __future__ import annotations

import customtkinter as ct

from axial_app import __version__
from axial_app.theme import FONT_FAMILY, FONT_SIZE_LG, FONT_SIZE_MD, FONT_SIZE_SM, PAD_LG, PAD_MD


def show_about(parent) -> None:
    """Show the About dialog."""
    dialog = ct.CTkToplevel(parent)
    dialog.title("About Axial Resolution GUI")
    dialog.geometry("380x280")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.transient(parent)

    # Center on parent
    dialog.update_idletasks()
    px = parent.winfo_rootx() + parent.winfo_width() // 2 - 190
    py = parent.winfo_rooty() + parent.winfo_height() // 2 - 140
    dialog.geometry(f"+{px}+{py}")

    # Content
    ct.CTkLabel(
        dialog, text="Axial Resolution GUI",
        font=ct.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
    ).pack(pady=(PAD_LG + 8, PAD_MD))

    ct.CTkLabel(
        dialog, text=f"Version {__version__}",
        font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_MD),
    ).pack(pady=PAD_MD)

    ct.CTkLabel(
        dialog,
        text="Professional scientific software for measuring\naxial resolution of optical systems.",
        font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_SM),
        justify="center",
    ).pack(pady=PAD_MD)

    ct.CTkLabel(
        dialog,
        text="Supports Player One, Allied Vision,\nThorlabs Kinesis, and Pololu Tic hardware.",
        font=ct.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_SM),
        text_color=("gray50", "gray60"),
        justify="center",
    ).pack(pady=PAD_MD)

    ct.CTkButton(
        dialog, text="OK", width=100,
        command=dialog.destroy,
    ).pack(pady=PAD_LG)
