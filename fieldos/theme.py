"""FIELD//OS visual tokens — the single source of truth for color/type/shape.

Every tier's stylesheet (qt_app.STYLE -> qt_field_app.V29_STYLE ->
qt_v3_app.V3_STYLE -> qt_v3_health_app.HEALTH_STYLE, each concatenating onto
the last) builds on these constants instead of hardcoding hex values, so a
palette change made here reaches every surface. ACCENT is deliberately left
matching fieldos/visual_surfaces.py's hand-painted GREEN/GRID/BG constants
(the RADIO waterfall and NAVIGATION map canvases) rather than introduced
fresh, so drawn canvases and QSS-styled widgets read as one palette.
"""

from __future__ import annotations

BG = "#020503"
PANEL = "#080f0a"
# Cards/tiles sit one step above PANEL so grouped content reads as a
# distinct layer (elevation) rather than a flat wash of the same dark green.
SURFACE = "#111b14"
SURFACE_HOVER = "#17251a"
BORDER = "#284b31"
BORDER_DIM = "#17301d"

TEXT = "#d7f7df"
TEXT_BRIGHT = "#ffffff"
TEXT_DIM = "#88ac95"
TEXT_FAINT = "#557a63"

ACCENT = "#63ff88"
ACCENT_SOFT = "#12341c"

WARN = "#ffb84d"
ERROR = "#ff6b6b"

# 'Share Tech Mono' is bundled (fieldos/assets/fonts/, SIL OFL 1.1) and
# registered at startup by qt_app.load_bundled_fonts(). If that ever fails
# (missing file, platform rejects it), Qt just falls through to the next
# name in this ordinary CSS-style font-family stack.
MONO_FONT = "'Share Tech Mono','DejaVu Sans Mono','Consolas','Courier New',monospace"

# System sans stack for UI chrome (labels, buttons, tile titles). Reserved
# for navigation/structure; actual data/telemetry (status text, lists,
# typed input, the top bar/footer) stays on MONO_FONT so the app still
# reads as an instrument, not a generic app -- see qt_app.STYLE's
# QLabel#body/QLineEdit/QListWidget overrides.
UI_FONT = "'Segoe UI','Noto Sans','DejaVu Sans','Helvetica Neue',sans-serif"

RADIUS = "10px"
RADIUS_LG = "16px"

STATUS_COLORS = {"OK": ACCENT, "WARN": WARN, "ERROR": ERROR, "NEUTRAL": TEXT_DIM}
