"""
Theme constants for the Axial Resolution GUI.

Dark-mode-first design suitable for laboratory environments.
Colors, fonts, and spacing constants used throughout the application.
"""

from __future__ import annotations


# ---- Color Palette ----

# Dark mode backgrounds (primary surfaces)
BG_DARKEST = "#0f0f1a"       # Window background
BG_DARK = "#1a1a2e"          # Main panels
BG_MEDIUM = "#16213e"        # Sidebar, secondary panels
BG_LIGHT = "#1e2a4a"         # Cards, elevated surfaces
BG_HOVER = "#253556"         # Hover state for interactive elements

# Light mode backgrounds
BG_LIGHT_MODE = "#f0f2f5"
BG_LIGHT_CARD = "#ffffff"
BG_LIGHT_SIDEBAR = "#e8eaf0"
BG_LIGHT_HOVER = "#dde0e8"

# Accent colors
ACCENT_PRIMARY = "#0891b2"     # Teal — primary actions, active states
ACCENT_PRIMARY_HOVER = "#06b6d4"
ACCENT_SECONDARY = "#6366f1"   # Indigo — secondary actions
ACCENT_SECONDARY_HOVER = "#818cf8"

# Status colors
STATUS_GREEN = "#22c55e"       # Connected, success
STATUS_GREEN_DIM = "#166534"   # Dimmed green for pulse animation
STATUS_RED = "#ef4444"         # Disconnected, error
STATUS_RED_DIM = "#7f1d1d"
STATUS_AMBER = "#f59e0b"       # Connecting, warning
STATUS_AMBER_DIM = "#78350f"

# Text colors
TEXT_PRIMARY_DARK = "#e2e8f0"   # High contrast text on dark bg
TEXT_SECONDARY_DARK = "#94a3b8" # Muted text on dark bg
TEXT_DISABLED_DARK = "#475569"

TEXT_PRIMARY_LIGHT = "#1e293b"  # Dark text on light bg
TEXT_SECONDARY_LIGHT = "#64748b"
TEXT_DISABLED_LIGHT = "#94a3b8"

# Borders
BORDER_DARK = "#2d3a5c"
BORDER_LIGHT = "#cbd5e1"

# Plot colors
PLOT_BG_DARK = "#1a1a2e"
PLOT_FG_DARK = "#e2e8f0"
PLOT_LINE = "#0891b2"
PLOT_GRID_DARK = "#2d3a5c"

PLOT_BG_LIGHT = "#ffffff"
PLOT_FG_LIGHT = "#1e293b"
PLOT_GRID_LIGHT = "#e2e8f0"

# Crosshair overlay
CROSSHAIR_COLOR = "#f59e0b"
CROSSHAIR_FLASH = "#fbbf24"


# ---- Fonts ----

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"

# Font sizes
FONT_SIZE_XS = 10
FONT_SIZE_SM = 11
FONT_SIZE_MD = 13
FONT_SIZE_LG = 15
FONT_SIZE_XL = 18
FONT_SIZE_XXL = 23
FONT_SIZE_TITLE = 28

# Numeric display
FONT_SIZE_READOUT = 20
FONT_SIZE_READOUT_LABEL = 11


# ---- Spacing ----

PAD_XS = 2
PAD_SM = 4
PAD_MD = 8
PAD_LG = 16
PAD_XL = 24

# Widget sizing
SIDEBAR_WIDTH = 260
TOOLBAR_HEIGHT = 40
TOOLBAR_BTN_SIZE = 36
STATUSBAR_HEIGHT = 28
COLLAPSE_ANIM_MS = 200
COLLAPSE_ANIM_STEPS = 10

# Status indicator
INDICATOR_SIZE = 10
INDICATOR_PULSE_MS = 500

# Tooltip
TOOLTIP_DELAY_MS = 400
TOOLTIP_BG_DARK = "#1e293b"
TOOLTIP_BG_LIGHT = "#f8fafc"

# Progress ring
RING_SIZE = 32
RING_THICKNESS = 3
RING_ANIM_INTERVAL_MS = 33  # ~30fps


# ---- Icon generation sizes ----
ICON_SIZE = 20
ICON_PADDING = 8


def get_colors(mode: str = "dark") -> dict:
    """Return a dict of semantic color names for the given mode."""
    if mode == "dark":
        return {
            "bg_window": BG_DARKEST,
            "bg_panel": BG_DARK,
            "bg_sidebar": BG_MEDIUM,
            "bg_card": BG_LIGHT,
            "bg_hover": BG_HOVER,
            "accent": ACCENT_PRIMARY,
            "accent_hover": ACCENT_PRIMARY_HOVER,
            "accent2": ACCENT_SECONDARY,
            "accent2_hover": ACCENT_SECONDARY_HOVER,
            "text": TEXT_PRIMARY_DARK,
            "text_secondary": TEXT_SECONDARY_DARK,
            "text_disabled": TEXT_DISABLED_DARK,
            "border": BORDER_DARK,
            "plot_bg": PLOT_BG_DARK,
            "plot_fg": PLOT_FG_DARK,
            "plot_grid": PLOT_GRID_DARK,
            "tooltip_bg": TOOLTIP_BG_DARK,
        }
    else:
        return {
            "bg_window": BG_LIGHT_MODE,
            "bg_panel": BG_LIGHT_CARD,
            "bg_sidebar": BG_LIGHT_SIDEBAR,
            "bg_card": BG_LIGHT_CARD,
            "bg_hover": BG_LIGHT_HOVER,
            "accent": ACCENT_PRIMARY,
            "accent_hover": ACCENT_PRIMARY_HOVER,
            "accent2": ACCENT_SECONDARY,
            "accent2_hover": ACCENT_SECONDARY_HOVER,
            "text": TEXT_PRIMARY_LIGHT,
            "text_secondary": TEXT_SECONDARY_LIGHT,
            "text_disabled": TEXT_DISABLED_LIGHT,
            "border": BORDER_LIGHT,
            "plot_bg": PLOT_BG_LIGHT,
            "plot_fg": PLOT_FG_LIGHT,
            "plot_grid": PLOT_GRID_LIGHT,
            "tooltip_bg": TOOLTIP_BG_LIGHT,
        }
