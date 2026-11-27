""" Configuration file: Settings and constants """

from pathlib import Path

# Path configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "logs.log"
DB_FILE = DATA_DIR / "telemetry.db"

# UI Configuration
WINDOW_W, WINDOW_H = 1024, 472
GAP = 10
CYCLE_SIZE, RING_W = 132, 12
R_HERO, R_CARD, R_TILE = 22, 16, 12
CLOCK_FORMAT = "%H:%M  %d.%m.%Y"

C_BG, C_SIDEBAR = "#0D1412", "#0A100E"
C_CARD, C_CARD_ALT, C_BORDER = "#15201C", "#1B2A25", "#26372F"
C_ACCENT, C_ACCENT_DIM = "#2EE6B0", "#1D9C78"
C_TEXT, C_MUTED = "#E7F1ED", "#8AA198"
C_DAY, C_NIGHT, C_MOON = "#F2B84B", "#5E6EDB", "#C7CEF5"

SANS_FONTS = ("Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", "Noto Sans", "DejaVu Sans", "Arial")
MONO_FONTS = ("JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New")

CONSOLE_PROMPT = ">_"
CONSOLE_LINES, CONSOLE_CHARS, CONSOLE_HISTORY = 4, 52, 500

# Other configuration
BAUDRATE = 115200
STM_PORT = ""
OS = "STM_PORT"

SECONDS_DAY = 86400
ALLOWED_TELEMETRY_COLUMNS = {
    "temp_in_100",
    "ph_10",
    "turbidity_ntu_100",
    "water_level_ok",
    "uptime_sec",
    "state_code",
}