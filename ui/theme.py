# =============================================================================
# ui/theme.py  –  Application Design System
# =============================================================================
# All colours, fonts, sizes, and geometry constants for the main application.
# theme_plantpax.py handles HMI Dashboard / PlantPAx symbol-specific styling.
#
# Import everywhere with:  from ui.theme import *
# =============================================================================


# ---------------------------------------------------------------------------
# Colour Palette  (raw hex values — prefer semantic aliases below)
# ---------------------------------------------------------------------------

# Backgrounds
BG_MAIN   = "#1a1a1a"    # page / canvas / workspace background
BG_CARD   = "#262626"    # card / panel surface
BG_EDITOR = "#1e1e1e"    # code-editor and textbox background

# Brand & accent
BRAND_CYAN    = "#4db8ff"
SUCCESS_GREEN = "#3DDC84"
WARNING_AMBER = "#ffcc00"
CAUTION_ORANGE = "#E67E22"
ERROR_RED      = "#E74C3C"

# Button base colours
BTN_NAVY          = "#1f538d"
BTN_TEAL          = "#2b7a78"
BTN_RED           = "#8b0000"
BTN_ORANGE        = "#E67E22"
BTN_ORANGE_HOVER  = "#D35400"
BTN_PURPLE        = "#8E44AD"
BTN_PURPLE_HOVER  = "#732D91"

# Borders & separators
BORDER_DARK   = "#333333"    # standard panel / scroll-frame borders
BORDER_MID    = "#444444"    # separator bar
BORDER_LIGHT  = "#555555"    # IO scroll-frame borders
BORDER_FORCED = CAUTION_ORANGE  # entry highlight when a value is forced

# Canvas / node workspace
CANVAS_BG          = "#121212"
CANVAS_GRID_MAJOR  = "#262626"
CANVAS_GRID_MINOR  = "#1a1a1a"
GATE_BLOCK_BG      = "#1E3246"

# Alarm severity — background and foreground pairs
ALM_CRITICAL_BG = "#3d1010"
ALM_WARNING_BG  = "#3d2a10"
ALM_INFO_BG     = "#3d3510"
ALM_CRITICAL_FG = "#E74C3C"
ALM_WARNING_FG  = "#E67E22"
ALM_INFO_FG     = "#F1C40F"

# Table / chart alternating row colours
ROW_ALT_A = "#222222"
ROW_ALT_B = "#1e1e1e"


# ---------------------------------------------------------------------------
# Text Colours  (semantic aliases — use these in widget text_color=)
# ---------------------------------------------------------------------------

TXT_PRIMARY     = "#d4d4d4"    # standard body / entry text
TXT_SECONDARY   = "gray70"     # muted / helper / description text
TXT_DISABLED    = "gray40"     # disabled state
TXT_PLACEHOLDER = "gray50"     # placeholder / empty-state text

TXT_ACCENT      = BRAND_CYAN   # hyperlinks, interactive highlights
TXT_SUCCESS     = SUCCESS_GREEN
TXT_WARNING     = WARNING_AMBER
TXT_CAUTION     = CAUTION_ORANGE
TXT_ERROR       = ERROR_RED

# Icon / action text colours (used on transparent-background buttons)
TXT_DANGER      = "#ff4d4d"    # close / destructive action icon
TXT_DELETE      = "#ff6666"    # delete row icon (slightly softer red)
TXT_HIGHLIGHT   = "#ff9966"    # variable-name accent (UDT inspector)

TXT_CODE        = "#d4d4d4"    # monospace code text (explicit alias)
TXT_COL_HEADER  = "gray55"     # table column header labels


# ---------------------------------------------------------------------------
# Typography  (font tuples — prefer semantic aliases below)
# ---------------------------------------------------------------------------

_FONT_UI   = "Helvetica"   # UI chrome: titles, labels, buttons
_FONT_MONO = "Consolas"    # code, data values, variable names

# Raw size/weight combinations
FONT_TITLE        = (_FONT_UI,   20, "bold")   # app-level header
FONT_H1           = (_FONT_UI,   16, "bold")   # page heading (e.g. Alarms title)
FONT_H2           = (_FONT_UI,   14, "bold")   # section heading (e.g. Snippets Library)
FONT_H3           = (_FONT_UI,   13, "bold")   # sub-section (e.g. Inputs / Outputs)
FONT_LABEL        = (_FONT_UI,   12, "bold")   # toolbar labels
FONT_BODY         = (_FONT_UI,   11)           # general body text
FONT_BODY_BOLD    = (_FONT_UI,   11, "bold")   # column headers in dialogs / tables
FONT_SMALL        = (_FONT_UI,   10)           # small labels, checkboxes

FONT_CODE         = (_FONT_MONO, 14)           # script editor, line numbers, help box
FONT_CODE_MD      = (_FONT_MONO, 12)           # debug box, json view, autocomplete list
FONT_CODE_SM_BOLD = (_FONT_MONO, 12, "bold")   # live error label, legend headers
FONT_CODE_BODY    = (_FONT_MONO, 11)           # variable names, entries, listboxes
FONT_CODE_HDR     = (_FONT_MONO, 11, "bold")   # column headers in code contexts
FONT_CODE_XS      = (_FONT_MONO, 10)           # dense info / line numbers
FONT_CODE_XS_BOLD = (_FONT_MONO, 10, "bold")   # dense column headers (UDT inspector)

# Semantic aliases — use these names in widget code so intent is clear
FONT_SECTION_TITLE = FONT_H3          # "Inputs", "Outputs", "Locals", "VAR_IN_OUT"
FONT_TOOLBAR_LBL   = FONT_LABEL       # "Available Tags:", "Source Language:" etc.
FONT_COL_HEADER    = FONT_CODE_HDR    # "Name", "Tag", "Type", "Value", "Sim"
FONT_ENTRY         = FONT_CODE_BODY   # text inside CTkEntry / listbox widgets
FONT_BTN           = (_FONT_UI, 12)   # standard button label
FONT_SNIPPETS_TITLE = FONT_H2         # right-pane view titles
FONT_ERROR_LABEL    = FONT_CODE_SM_BOLD  # live compile-error label


# ---------------------------------------------------------------------------
# Geometry  (corner radius, border widths, standard widget dimensions)
# ---------------------------------------------------------------------------

# Corner radii
RADIUS        = 6    # default widget rounding
RADIUS_SM     = 4    # small widgets (alarm rows, tags)
RADIUS_LG     = 8    # large containers / HMI panels
RADIUS_NONE   = 0    # sharp corners (PlantPAx sidebar panels)

# Border widths
BORDER_W      = 1    # standard
BORDER_W_FOCUS = 2   # active / forced-value state

# Button dimensions
BTN_H         = 32   # standard button height
BTN_H_LG      = 40   # large action buttons (bulk generator, fault manager)
BTN_W_ICON    = 24   # square icon-only buttons (delete ✕, close ×)

# Entry / row dimensions
ENTRY_H       = 24   # row-level entry boxes (UDT inspector, var rows)
CHECKBOX_SZ   = 16   # checkbox_width and checkbox_height


# ---------------------------------------------------------------------------
# Window utilities  (import individually — not re-exported by *)
# ---------------------------------------------------------------------------
import ctypes as _ctypes
import sys as _sys


def apply_dark_titlebar(window) -> None:
    """Force dark title bar chrome on Windows via DWM API. Call from after()."""
    if _sys.platform != "win32":
        return
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        hwnd = _ctypes.windll.user32.GetParent(window.winfo_id())
        value = _ctypes.c_int(2)
        _ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            _ctypes.byref(value), _ctypes.sizeof(value),
        )
    except Exception:
        pass


def center_on_parent(window, parent, w: int, h: int) -> None:
    """Position window (w×h) centred over parent using absolute screen coords."""
    parent.update_idletasks()
    x = max(0, parent.winfo_rootx() + (parent.winfo_width()  - w) // 2)
    y = max(0, parent.winfo_rooty() + (parent.winfo_height() - h) // 2)
    window.geometry(f"{w}x{h}+{x}+{y}")


def center_on_screen(window, w: int, h: int) -> None:
    """Position window (w×h) centred on the primary display."""
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    window.geometry(f"{w}x{h}+{x}+{y}")
