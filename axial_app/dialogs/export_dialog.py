"""
Export dialog — choose format (PNG plot, CSV data) and file location.
"""

from __future__ import annotations

from tkinter import filedialog
from typing import Optional

import customtkinter as ct
import numpy as np

from axial_app.theme import FONT_FAMILY, FONT_SIZE_MD, PAD_LG, PAD_MD


def export_plot_png(parent, figure) -> Optional[str]:
    """Save the current matplotlib figure as PNG."""
    if figure is None:
        return None
    path = filedialog.asksaveasfilename(
        parent=parent,
        title="Export Plot as PNG",
        defaultextension=".png",
        filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
    )
    if path:
        figure.savefig(path, dpi=150, bbox_inches="tight")
        return path
    return None


def export_csv(
    parent,
    z_positions: np.ndarray | None,
    intensities: list | np.ndarray | None,
) -> Optional[str]:
    """Export scan data as CSV."""
    if z_positions is None or intensities is None:
        return None
    path = filedialog.asksaveasfilename(
        parent=parent,
        title="Export Data as CSV",
        defaultextension=".csv",
        filetypes=[("CSV File", "*.csv"), ("All Files", "*.*")],
    )
    if path:
        import csv
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Z Position (mm)", "Pixel Intensity"])
            for z, i in zip(z_positions, intensities):
                writer.writerow([f"{z:.6f}", f"{i}"])
        return path
    return None
