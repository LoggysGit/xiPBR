# === IMPORTS === #
import os
import json

import time
from datetime import datetime

import queue
import threading

# === MODULES === #
import modules.lib as lib

import modules.data_manager as DataManager
import modules.ai_driver as AIManager
import modules.bridge as PortManager
import modules.gui as GUI

# === CONSTANTS === #
ASSISTANT_MODEL = "Qwen2.5-1.5B-Q8.gguf"
ASSISTANT_PATH = os.path.join(lib.AI_DIR, "LLM", "model", ASSISTANT_MODEL)

# === VARIABLES === #

sys_cmd_buffer = queue.Queue()
ai_cmd_buffer = queue.Queue()
gui_cmd_buffer = queue.Queue()

# === PRE-INIT === #
lib.init_logger(gui_cmd_buffer)
with open(lib.TELEMETRY_FILE_DIR, "r") as f: database_json = json.load(f)
with open(lib.STATE_FILE_DIR, "r") as f: state_json = json.load(f)

selected_culture = "Arthrospira" # transmit to "machine_config.json"

# === OBJECTS === #
stateWatcher = AIManager.XGB(1, 1024, 12, "StateWatcher")
harvester    = AIManager.XGB(1, 1024, 12, "Harvester")

assistant = AIManager.AIAssistant(ASSISTANT_PATH)

port_bridge = PortManager.PortBridge(lib.SPINE_PORT)

data_manager = DataManager.DataManager(gui_cmd_buffer, sys_cmd_buffer, database_json, selected_culture)

# === APP INIT (START) === #
dn_executed_today = False

stateWatcher.load_model()
harvester.load_model()

state_data = data_manager.get_statewatcher_input_list()
statewatcher_res = stateWatcher.predict(state_data)
gui_cmd_buffer.put(("STATEWATCHER_RESULT", statewatcher_res))

# === THREADS === #
def system_thread():
    last_update_time = time.time()
    last_cleanup_time = time.time()

    last_health_update_time = time.time()
    last_harvest_verdict_update_time = time.time()
    
    while True:
        try:
            command_type, payload = sys_cmd_buffer.get(block=True, timeout=0.1)
            match(command_type):
                case "HARVEST_REQUEST":
                    port_bridge.send("HARVEST")
                    lib.log("[SYS] Harvest request satisfied.")

                case "ADD_WATER":
                    port_bridge.send("ADDWATER")
                    lib.log(f"[SYS] Water request satisfied.")
                
                case "": continue
                case _: lib.log(f"[SYS] Unknown command was requested.")
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

        # StateWatcher XGB
        if current_time - last_health_update_time >= 600.0:
            state_data = data_manager.get_statewatcher_input_list()
            statewatcher_res = stateWatcher.predict(state_data)

            gui_cmd_buffer.put(("STATEWATCHER_RESULT", float(statewatcher_res[0])))

            last_health_update_time = current_time

        # Harvester XGB
        if current_time - last_harvest_verdict_update_time >= 1.5 * 86400.0:
            harv_data = data_manager.get_harvester_input_list()
            harvester_res = harvester.predict(harv_data)

            if (harvester_res >= 85): data_manager.add_future_harvest_data()

            last_harvest_verdict_update_time = current_time

        time.sleep(0.1)

def assistant_thread():
    global dn_executed_today

    while True:
        try:
            command_type, payload = ai_cmd_buffer.get(block=True, timeout=1.0)

            if command_type == "AI_REQUEST":
                lib.log(f"[AI] Assistant triggered.")
                assistant.ask(payload, database_json, state_json)

            ai_cmd_buffer.task_done()
            lib.log(f"[AI] Assistant answered.")
        except queue.Empty: pass

        # Update daily notification at 12:00 AM every day
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            if not dn_executed_today:
                dn_prompt = (
                    "Generate a brief, high-density daily system notification for the photobioreactor operator. "
                    "Structure it exactly into 3 short parts: "
                    "* REVIEW: A hyper-short analysis of the recent telemetry or state logs. "
                    "* ADVICE: One practical technical tip/warning or optimization step for a culture growth. "
                    "* JOKE: A dry, witty, or sarcastic engineer/biology joke related to hardware, systems, or cells. "
                    "Constraint: Keep the entire output under 3-4 sentences total. No markdown titles, no fluff."
                )
                res = assistant.ask(dn_prompt, database_json, state_json, save=False)
                data_manager.update_daily_notification(res)
                dn_executed_today = True
        else: dn_executed_today = False

        time.sleep(0.1)

def serial_thread(): port_bridge._read_loop()

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