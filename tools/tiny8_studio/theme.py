"""Tiny8 Studio — dark theme tokens.

The studio uses a small set of named colors and fonts.  No third-party
dependencies; just plain tkinter palettes.

The theme is intentionally restrained: dark surface, soft borders, a
single accent color for actions, and high-contrast text.  All values are
exposed as module-level constants so widgets can read them without
instantiating a class.
"""

# Surfaces
BG          = "#1E1F22"   # window background
BG_PANEL    = "#26282C"   # side panels, status bar
BG_RAISED   = "#2C2E33"   # editor canvas, list boxes
BG_INPUT    = "#1A1B1E"   # text inputs, terminal
BG_HOVER    = "#3A3D43"   # hover state
BORDER      = "#3A3D43"   # separators, frames
BORDER_FOC  = "#5B7CFA"   # focused border

# Text
FG          = "#E6E6E6"   # primary text
FG_DIM      = "#9AA0A6"   # secondary text
FG_MUTED    = "#6B7280"   # tertiary text
FG_ON_ACC   = "#FFFFFF"   # text on accent buttons
FG_ERROR    = "#F87171"   # errors
FG_WARN     = "#FBBF24"   # warnings
FG_OK       = "#34D399"   # success

# Accent
ACCENT      = "#5B7CFA"   # primary action color
ACCENT_DARK = "#4458C7"   # pressed/active

# Pixel editor palette (1-bit displayed, but preview uses 2 grays)
PX_ON       = "#E6E6E6"
PX_OFF      = "#1A1B1E"
PX_GRID     = "#33363B"

# Fonts
FONT_UI     = ("Segoe UI", 9)
FONT_UI_B   = ("Segoe UI", 9, "bold")
FONT_MONO   = ("Consolas", 9)
FONT_TITLE  = ("Segoe UI", 11, "bold")

# Geometry
PAD         = 6
PAD_TIGHT   = 3
TOOLBAR_BTN_W = 90
