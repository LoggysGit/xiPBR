import os
import sys

import json

import time
from datetime import datetime, timedelta

import modules.lib as lib

class DataManager:
    def __init__(self, gui_cmds, sys_cmds, db, culture):
        self.gui_cmd_buff = gui_cmds
        self.sys_cmd_buff = sys_cmds
        self.database_json = db
        self.selected_culture = culture

    def get_avg_telemetry(self, data_key, period_days):
        # Load telemetry entries
        raw_data = self.database_json.get(data_key, [])
        if not raw_data: return 0.0

        # Calculate time threshold
        current_time = time.time()
        seconds_in_period = period_days * 86400
        threshold_time = current_time - seconds_in_period

        # Filter valid records
        valid_values = []
        for timestamp, val in raw_data:
            try:
                struct_time = time.strptime(timestamp, "%d.%m.%Y-%H:%M")
                epoch_time = time.mktime(struct_time)
                if epoch_time >= threshold_time: valid_values.append(float(val))
            except (ValueError, TypeError) as e: lib.log(f"[UI] Avg telemetry calculation error:{e}")

        # Compute average value
        if not valid_values: return 0.0
            
        return sum(valid_values) / len(valid_values)
    def get_delta_telemetry(self, data_key, period_days):
        points = self.database_json.get(data_key, [])
        if not points: return 0.0

        try:
            last_time_str, last_val = points[-1]
            last_dt = datetime.strptime(last_time_str, "%d.%m.%Y-%H:%M")
            
            target_dt = last_dt - timedelta(days=period_days)
            
            closest_val = float(points[0][1])
            min_delta = abs((datetime.strptime(points[0][0], "%d.%m.%Y-%H:%M") - target_dt).total_seconds())

            for time_str, val in reversed(points[:-1]):
                current_dt = datetime.strptime(time_str, "%d.%m.%Y-%H:%M")
                current_delta = abs((current_dt - target_dt).total_seconds())
                
                if current_delta < min_delta:
                    min_delta = current_delta
                    closest_val = float(val)
                elif current_dt < target_dt and current_delta > min_delta: break

            return round(float(last_val) - closest_val, 2)
            
        except Exception: return 0.0
    def get_value_mark(self, val): return f"+{val}" if val >= 0 else f"-{val}"
    
    def get_last_telemetry(self):
        file_path = lib.TELEMETRY_FILE_DIR
        default_data = {"temp_out": 0.0, "temp_in": 0.0, "ph": 7.0, "concentration": 0.0}
        
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0: return default_data
            
        try:
            with open(file_path, "r", encoding="utf-8") as f: db = json.load(f)
                
            return {
                "temp_out": float(db.get("temp_out", [[None, 0.0]])[-1][1]),
                "temp_in":  float(db.get("temp_in",  [[None, 0.0]])[-1][1]),
                "ph":       float(db.get("ph",       [[None, 7.0]])[-1][1]),
                "concentration": float(db.get("concentration", [[None, 0.0]])[-1][1])
            }
        except Exception as e:
            lib.log(f"[DATA] Failed to get last telemetry: {e}")
            return default_data
    def get_last_state(self):
        file_path = getattr(lib, "STATE_FILE_DIR", os.path.join(lib.RESOURCES_DIR, "state.json"))
        default_state = {
            "connection": False,
            "state": {"L0": 0, "L1": 0, "L2": 0, "C": 0, "H": 0, "P": 0},
            "volume": {"low": 0, "high": 0},
            "flasks": {"left": 0, "right": 0, "grams_left": 0.0, "grams_right": 0.0}
        }
        
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0: return default_state
            
        try:
            with open(file_path, "r", encoding="utf-8") as f: db = json.load(f)
                
            return {
                "connection": bool(db.get("connection", [[None, False]])[-1][1]),
                "state":      db.get("state",      [[None, default_state["state"]]])[-1][1],
                "volume":     db.get("volume",     [[None, default_state["volume"]]])[-1][1],
                "flasks":     db.get("flasks",     [[None, default_state["flasks"]]])[-1][1]
            }
        except Exception as e:
            lib.log(f"[DATA] Failed to get last state: {e}")
            return default_state

    def get_daily_notif(self):
        # Just read file resources/daily.txt
        return ""

    def percOrOffFormat(self, integer): return f"{integer}%" if integer > 0 else "Off"
    def strBooleanFormat(self, b, y, n): return y if b else n

    def get_harvest_logs_dict(self):
        file_path = os.path.join(lib.RESOURCES_DIR, "harvest_calendar.json")
        # Read file
        harvest_data = {}
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, "r", encoding="utf-8") as f: harvest_data = json.load(f)
            except Exception as e: lib.log(f"[UI] Calendar read error: {e}")
        # Format: {"DD.MM.YYYY": entry}
        logs_dict = {}
        if "calendar" in harvest_data:
            for entry in harvest_data["calendar"]:
                try:
                    date_str = entry["timestamp"].split("-")[0]
                    logs_dict[date_str] = entry
                except KeyError: continue
        return logs_dict
    
    def add_future_harvest_data(self):
        # Open harvest_calendar.json ["planned"]
        # Save current datetime + 24h
        pass

    def get_culture_profile(self):
        culture_profile_path = lib.RESOURCES_DIR / "flora_profiles" / f"{self.selected_culture}.json"
        with open(culture_profile_path, 'r', encoding='utf-8') as file: culture_profile = json.load(file)
        return culture_profile

    def get_statewatcher_input_list(self):
        # [current_ph, current_temp_in, current_turbidity, day_delta_ph, day_delta_turbidity, l1_pow_percent, l2_pow_percent, l3_pow_percent, last_harvest_day_elapsed]

        telemetry = self.get_last_telemetry()
        state = self.get_last_state()

        # Deltas
        day_ph = self.get_avg_telemetry("ph", 1)
        day_concentration = self.get_delta_telemetry("concentration", 1)

        # Last harvest data
        harvest_logs = self.get_harvest_logs_dict()

        last_harvest_date = ""
        days_elapsed = 0.0

        if harvest_logs:
            last_date_str = max(harvest_logs.keys(), key=lambda d: datetime.strptime(d, "%d.%m.%Y"))

            last_harvest_date = last_date_str

            current_time = datetime.now()
            last_harvest_datetime = datetime.strptime(last_harvest_date, "%d.%m.%Y")

            days_elapsed = (current_time - last_harvest_datetime).total_seconds() / 86400.0
        else: days_elapsed = float('inf')

        # Collect all
        return [telemetry["ph"], telemetry["temp_in"], telemetry["concentration"], day_ph, day_concentration,
                state["state"]["L0"], state["state"]["L1"], state["state"]["L2"], days_elapsed]
    
    def get_harvester_input_list(self):
        # input: [maximum_liters, harvest_amount, curr_concentration, day_delta_concentration, week_delta_concentration, curr pH, day avg pH, week avg pH, previous_harvest_days_elapsed, 
        # previous_harvest_ml, previous_harvest_concentration, current_inner_temp] # (12 arguments)

        telemetry = self.get_last_telemetry()

        # Concentration delta
        day_concentration = self.get_delta_telemetry("concentration", 1)
        week_concentration = self.get_delta_telemetry("concentration", 7)

        # pH delta
        day_ph = self.get_avg_telemetry("ph", 1)
        week_ph = self.get_avg_telemetry("ph", 7)

        # Last harvest data
        harvest_logs = self.get_harvest_logs_dict()

        last_harvest_date = ""
        last_harvest_vol = 0
        last_harvest_conc = 0

        days_elapsed = 0.0

        if harvest_logs:
            last_date_str = max(harvest_logs.keys(), key=lambda d: datetime.strptime(d, "%d.%m.%Y"))

            last_entry = harvest_logs[last_date_str]

            last_harvest_date = last_date_str
            last_harvest_vol = last_entry.get("ml", 0)
            last_harvest_conc = last_entry.get("turbidity", 0)

            current_time = datetime.now()
            last_harvest_datetime = datetime.strptime(last_harvest_date, "%d.%m.%Y")

            days_elapsed = (current_time - last_harvest_datetime).total_seconds() / 86400.0
        else: days_elapsed = float('inf')

        # Collect all
        return [lib.V_LITERS, -1, telemetry["concentration"], day_concentration, week_concentration, 
                telemetry["ph"], day_ph, week_ph, days_elapsed, last_harvest_vol, last_harvest_conc, telemetry["temp_in"]]
    
    def read_logs(self):
        try:
            with open(lib.LOGS_FILE_DIR, "r", encoding="utf-8") as f:
                for line in f:
                    clean_line = line.strip()
                    if clean_line: self.gui_cmd_buff.put(("LOGS", clean_line))
                 
        except (FileNotFoundError, IOError): lib.log("[UI] No log file found.")

    def read_ai_history(self):
        try:
            with open(lib.AI_CHAT_HISTORY_DIR, "r", encoding="utf-8") as f:
                data = json.load(f)
                history_list = data if isinstance(data, list) else data.get("history", [])
                
                self.gui_cmd_buff.put(("AI_CHAT", history_list))

        except (FileNotFoundError, IOError): lib.log("[UI] No AI history file found.")
    def clean_month_ai_history(self):
        try:
            with open(lib.AI_CHAT_HISTORY_DIR, "r", encoding="utf-8") as f: data = json.load(f)
            
            # Universal JSON read method
            is_list = isinstance(data, list)
            history_list = data if is_list else data.get("history", [])
            
            if not history_list: return

            now = datetime.now()
            initial_count = len(history_list)
            
            filtered_history = []
            for msg in history_list:
                msg_time_str = msg.get("time", "")
                try:
                    msg_date = datetime.strptime(msg_time_str[:10], "%d.%m.%Y")
                    if (now - msg_date).days < 30: filtered_history.append(msg)
                except ValueError: filtered_history.append(msg)

            # Avoid empty updates
            if len(filtered_history) != initial_count:
                if is_list: new_data = filtered_history
                else:
                    data["history"] = filtered_history
                    new_data = data

                with open(lib.AI_CHAT_HISTORY_DIR, "w", encoding="utf-8") as f: json.dump(new_data, f, ensure_ascii=False, indent=4)
                
                lib.log(f"[SYS] AI history cleaned. Removed {initial_count - len(filtered_history)} old messages.")
                
                self.gui_cmd_buff.put(("AI_CHAT", filtered_history))

        except (FileNotFoundError, json.JSONDecodeError, IOError) as e: lib.log(f"[SYS] AI history cleanup failed: {e}")