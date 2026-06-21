import sys
import os
import json
from pathlib import Path
from datetime import datetime

V_LITERS = 8

ABS_MIN_TEMP = 18
ABS_MAX_TEMP = 50

### Paths & Ports ###

if getattr(sys, 'frozen', False): BASE_DIR = Path(sys.executable).parent
else: BASE_DIR = Path(__file__).resolve().parent.parent

ENV = "win" if os.name == "nt" else "linux"

RESOURCES_DIR = BASE_DIR / "resources"
AI_DIR = RESOURCES_DIR / "ai_data"
UI_ELEMENTS_DIR = RESOURCES_DIR / "ui_elements"

CONFIG_DIR = RESOURCES_DIR / "app_config.json"

with open(CONFIG_DIR, 'r', encoding='utf-8') as f: app_config = json.load(f)

SPINE_PORT = app_config[ENV]["spine_port"]

TELEMETRY_FILE_DIR = RESOURCES_DIR / "telemetry.json"
STATE_FILE_DIR = RESOURCES_DIR / "machine_state.json"

LOGS_FILE_DIR = RESOURCES_DIR / "logs.log"
HARVEST_CALENDAR_DATA_DIR = RESOURCES_DIR / "harvest_calendar.json"
AI_CHAT_HISTORY_DIR = AI_DIR / "LLM" / "history.json"
MACHINE_CONFIG_DIR = RESOURCES_DIR / "machine_config.json"

### Global variables & triggers ###
LAST_COMMAND_COMPLETED = False

_gui_cmd_buff = None


### Functions ###

def init_logger(gui_cmds):
    global _gui_cmd_buff
    _gui_cmd_buff = gui_cmds

def log(data):
    timestamp = datetime.now().strftime("%d.%m.%Y-%H:%M:%S:%f")[:-3]
    log_str = f"[{timestamp}] | {data}"

    try:
        with open(LOGS_FILE_DIR, "a", encoding="utf-8") as l: l.write(f"{log_str}\n")
    except Exception as e: print(f"[CRITICAL] Failed to write log file: {e}")

    if _gui_cmd_buff is not None: _gui_cmd_buff.put(("LOGS", log_str))

    print(data)