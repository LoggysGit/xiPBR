# === IMPORTS === #
import os
import json

import time

import queue
import threading

# === MODULES === #
import modules.lib as lib

import modules.data_manager as DataManager
import modules.ai_driver as AIManager
import modules.bridge as PortManager
import modules.gui as GUI

# === CONSTANTS === #
V_LITERS = 9
MAX_TEMP = 50

ASSISTANT_MODEL = "Qwen2.5-1.5B-Q8.gguf"
ASSISTANT_PATH = os.path.join(lib.AI_DIR, "LLM", "model", ASSISTANT_MODEL)


# === VARIABLES === #
selected_culture = "Arthrospira"

culture_profile_path = os.path.join(lib.RESOURCES_DIR / "flora_profiles", f"{selected_culture}.json")
with open(culture_profile_path, 'r', encoding='utf-8') as file: culture_profile = json.load(file)

sys_cmd_buffer = queue.Queue()
ai_cmd_buffer = queue.Queue()
gui_cmd_buffer = queue.Queue()

# === APP INIT (START) === #
lib.init_logger(gui_cmd_buffer)
with open(lib.TELEMETRY_FILE_DIR, "r") as f: database_json = json.load(f)

# === OBJECTS === #

stateWatcher = AIManager.XGB(2, 1024, 12, "StateWatcher")
harvester    = AIManager.XGB(1, 1024, 12, "Harvester")

assistant = AIManager.AIAssistant(ASSISTANT_PATH)
#translator = AIManager.Translator("rus", "eng")
#speechRec = AIManager.SpeechRecognizer("rus")
#voice = AIManager.TTS("")

port_bridge = PortManager.PortBridge(lib.SPINE_PORT)

data_manager = DataManager.DataManager(gui_cmd_buffer, sys_cmd_buffer, database_json)

# === THREADS === #
def system_thread():
    last_update_time = time.time()
    last_cleanup_time = time.time()
    
    while True:
        try:
            command_type, payload = sys_cmd_buffer.get(block=True, timeout=0.1)
            match(command_type):
                case "HARVEST_REQUEST":
                    port_bridge.send("HARVEST")
                    lib.log("[SYS] Harvest request satisfied.")

                case "CMD":
                    # Execute inner command (Placeholder)
                    lib.log(f"[SYS] Command '{payload}' executed successfully.")
                
                case "": continue
                case _: continue

        except queue.Empty: pass

        current_time = time.time()

        # Time-based trigger to update in-code telemetry object (Every 5 secs)
        if current_time - last_update_time >= 5.0:
            try:
                with open(lib.TELEMETRY_FILE_DIR, "r") as f: fresh_data = json.load(f)
                database_json.clear()
                database_json.update(fresh_data)
            
            except (FileNotFoundError, json.JSONDecodeError) as e:
                lib.log(f"[SYS] Telemetry object sync failed: {e}")
                
            last_update_time = current_time

        # Clear AI history that older than 1 month (everyday trigger)
        if current_time - last_cleanup_time >= 86400.0:
            data_manager.clean_month_ai_history()
            last_cleanup_time = current_time

        time.sleep(0.1)

def assistant_thread():
    while True:
        try:
            # Queue ["CMD", "PLD"]
            command_type, payload = ai_cmd_buffer.get(block=True, timeout=1.0)

            if command_type == "AI_REQUEST":
                lib.log(f"[AI] Assistant triggered.")
                assistant.ask(payload, database_json)

            ai_cmd_buffer.task_done()
            lib.log(f"[AI] Assistant answered.")
        except queue.Empty: continue

        # Update daily notification in 12:00 AM every day

        time.sleep(0.1)

def serial_thread():
    port_bridge._read_loop()

# === MAIN LOOP === #
port_bridge.start()
if __name__ == "__main__":
    print("[SYS] PBRmOS launched.")

    # --- THREAD 1: System ---
    sys_thread = threading.Thread(
        target=system_thread, 
        daemon=True, 
        name="System_Thread"
    )
    sys_thread.start()

    # --- THREAD 2: AI Assistant ---
    ai_thread = threading.Thread(
        target=assistant_thread, 
        daemon=True, 
        name="AI_Assistant_Thread"
    )
    ai_thread.start()

    # --- THREAD 3: Port Listener ---
    port_thread = threading.Thread(
        target=serial_thread, 
        daemon=True, 
        name="Serial_Thread"
    )
    port_thread.start()

    # --- MAIN THREAD: GUI ---
    app = GUI.App(port_bridge, data_manager, database_json, gui_cmd_buffer, sys_cmd_buffer, ai_cmd_buffer)
    app.mainloop()