import os
import json
import time

from datetime import datetime

import threading
import serial

import modules.lib as lib

class PortBridge:
    def __init__(self, port, baudrate=115200, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        
        self.ser = None
        self.is_running = False
        
        # Lock
        self.write_lock = threading.Lock()
        
        # Timings
        self.last_ping_sent = 0.0
        self.last_pong_received = time.time()

        self.ping_interval = 3.0
        self.connection_timeout = 9.0
        self.is_connected = False

        self.last_telemetry_request = 0
        self.telemetry_interval = 3600.0 * 1
        
        self.current_data = {
            "connection": True,
            "state": {"L0": 0, "L1": 0, "L2": 0, "C": 0, "H": 0, "P": 0},
            "temp": {"out": 0.0, "in": 0.0},
            "turbidity": 0,
            "volume": {"low": 0, "high": 0},
            "flasks": {"left": 0, "right": 0, "grams_left": 0, "grams_right": 0},
            "ph": 7.0
        }

    def start(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            self.is_running = True
            self.last_pong_received = time.time()
            self.is_connected = True
            lib.log(f"[SERIAL] Connected to {self.port} at {self.baudrate}")
            return True
        except serial.SerialException as e:
            lib.log(f"[SERIAL] Connection error on {self.port}: {e}")
            self.is_connected = False
            return False

    def _read_loop(self):
        while self.is_running:
            current_time = time.time()
            
            # Send Ping
            if current_time - self.last_ping_sent >= self.ping_interval:
                self.send("PING")
                self.last_ping_sent = current_time
            
            # Check Pong
            if current_time - self.last_pong_received > self.connection_timeout:
                if self.is_connected:
                    self.is_connected = False
                    lib.log("[SERIAL] Warning: Controller heartbeat lost!")

                    self.current_data["connection"] = False
                    self.data_buffer_ref.put(self.current_data.copy())

            # Request state
            if current_time - self.last_telemetry_request > self.telemetry_interval and self.is_connected:
                self.send("REQUESTSTATE")
                self.last_telemetry_request = current_time
            
            # Read port buffer
            if self.ser and self.ser.in_waiting > 0:
                try:
                    raw_line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if not raw_line: continue                    
                    self._parse_incoming(raw_line)
                except Exception as e: lib.log(f"[SERIAL] Error reading serial: {e}")
                    
            time.sleep(0.01)

    def _parse_incoming(self, line):
        parts = line.split(" ")
        cmd = parts[0]
        
        is_environment_data = False 

        try:
            match cmd:
                case "PONG":
                    self.last_pong_received = time.time()
                    if not self.is_connected:
                        self.is_connected = True
                        self.current_data["connection"] = True
                        lib.log("[SERIAL] Controller heartbeat restored.")
                        is_environment_data = True

                case "ACK": pass

                case "NACK":
                    lib.log(f"[SERIAL] Controller rejected command: {line}")

                case "LOG":
                    lib.log(f"[STM32] {parts[1]}")

                case "CURRENTSTATE":
                    # CURRENTSTATE B0 B1 B2 C H P (Values either 0-1 or 0-255)
                    self.current_data["state"] = {
                        "L0": int(parts[1]), "L1": int(parts[2]), "L2": int(parts[3]),
                        "C": int(parts[4]), "H": int(parts[5]), "P": int(parts[6])
                    }

                    self.send("DATAVALIDATED")
                    is_environment_data = True

                case "TEMP":
                    # TEMP T1 T2 (X - Temp num; T1 - out, T2 - in)
                    t1, t2 = map(float, parts[1:3])

                    self.current_data["temp"]["out"] = t1
                    self.current_data["temp"]["in"] = t2

                    self.send("DATAVALIDATED")
                    is_environment_data = True

                case "TURBIDITY":
                    # TURBIDITY V (V - Value)
                    self.current_data["turbidity"] = int(parts[1])

                    self.send("DATAVALIDATED")
                    is_environment_data = True

                case "VOLUME":
                    # VOLUME X (X - Binary mask 0-3 (0bxy); x - low, y - high)
                    mask = int(parts[1])

                    self.current_data["volume"]["low"] = 1 if (mask & 0b10) else 0
                    self.current_data["volume"]["high"] = 1 if (mask & 0b01) else 0

                    self.send("DATAVALIDATED")
                    is_environment_data = True

                case "FLASKS":
                    # FLASKS X L R (X - Binary mask 0-3 (0bxy); L, R - Gramms)
                    mask = int(parts[1])
                    l, r = map(float, parts[2:4])

                    self.current_data["flasks"]["right"] = 1 if (mask & 0b10) else 0
                    self.current_data["flasks"]["left"] = 1 if (mask & 0b01) else 0
                    
                    self.current_data["flasks"]["grams_left"] = l
                    self.current_data["flasks"]["grams_right"] = r

                    self.send("DATAVALIDATED")
                    is_environment_data = True

                case "PH":
                    # PH V (V - Value)
                    self.current_data["ph"] = float(parts[1])

                    self.send("DATAVALIDATED")
                    is_environment_data = True

                case "HARVESTLOG":
                    # HARVESTLOG L T (L - ml; T - turbidity at the moment)
                    ml, t = map(float, parts[1:3])
                    # 2. Get date
                    harvest_calendar_path = os.path.join(lib.RESOURCES_DIR, "harvest_calendar.json")
                    # 3. Save into
                    pass

                case "COMPLETED":
                    lib.LAST_COMMAND_COMPLETED = True

                case _:
                    lib.log(f"[SERIAL] Command {cmd} not found.")
            
            if is_environment_data:
                #self.data_buffer_ref.put(self.current_data.copy())
                self.save_current_telemetry()
                self.save_current_state()

        except (IndexError, ValueError):
            lib.log(f"[SERIAL] Warning: Corrupted data packet: {line}")
            self.send("DATACORRUPTED")

    def get_all(self): return self.current_data

    def send(self, cmd):
        if not self.ser or not self.ser.is_open: return False
            
        with self.write_lock:
            try:
                packet = f"{cmd.strip().upper()}\n"
                self.ser.write(packet.encode('utf-8'))
                self.ser.flush()
                return True
            except serial.SerialException as e:
                lib.log(f"[SERIAL] Write error: {e}")
                return False
            
    def save_current_telemetry(self):
        timestamp = datetime.now().strftime("%d.%m.%Y-%H:%M")
        file_path = getattr(lib, "TELEMETRY_FILE_DIR", os.path.join(lib.RESOURCES_DIR, "telemetry.json"))
        
        # Read data file
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, "r", encoding="utf-8") as f: telemetry_db = json.load(f)
            except Exception as e:
                lib.log(f"[SERIAL] Error reading file, creating new: {e}")
                telemetry_db = {}
        else: telemetry_db = {}

        # Check all keys
        target_keys = ["temp_out", "temp_in", "ph", "concentration"]
        for key in target_keys:
            if key not in telemetry_db: telemetry_db[key] = []

        # Format data
        try:
            current_temp_out = float(self.current_data["temp"]["out"])
            current_temp_in  = float(self.current_data["temp"]["in"])
            current_ph       = float(self.current_data["ph"])
            current_conc     = float(self.current_data["turbidity"])
            
            telemetry_db["temp_out"].append([timestamp, current_temp_out])
            telemetry_db["temp_in"].append([timestamp, current_temp_in])
            telemetry_db["ph"].append([timestamp, current_ph])
            telemetry_db["concentration"].append([timestamp, current_conc])
            
            with open(file_path, "w", encoding="utf-8") as f: json.dump(telemetry_db, f, ensure_ascii=False, indent=4)
                
            lib.log(f"[SERIAL] Telemetry data successfully saved in {file_path}")
            
        except KeyError as ke: lib.log(f"[SERIAL] Key {ke} is missing.")
        except Exception as e: lib.log(f"[SERIAL] Telemetry save error: {e}")

    def save_current_state(self):
        timestamp = datetime.now().strftime("%d.%m.%Y-%H:%M")
        file_path = getattr(lib, "STATE_FILE_DIR", os.path.join(lib.RESOURCES_DIR, "machine_state.json"))

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, "r", encoding="utf-8") as f: state_db = json.load(f)
            except Exception as e:
                lib.log(f"[SERIAL] Error reading state file, creating new: {e}")
                state_db = {}
        else: state_db = {}

        target_keys = ["connection", "state", "volume", "flasks"]
        for key in target_keys:
            if key not in state_db: state_db[key] = []

        try:
            current_conn   = bool(self.current_data.get("connection", False))
            current_state  = self.current_data.get("state", {"L0": 0, "L1": 0, "L2": 0, "C": 0, "H": 0, "P": 0})
            current_volume = self.current_data.get("volume", {"low": 0, "high": 0})
            current_flasks = self.current_data.get("flasks", {"left": 0, "right": 0, "grams_left": 0.0, "grams_right": 0.0})

            state_db["connection"].append([timestamp, current_conn])
            state_db["state"].append([timestamp, current_state])
            state_db["volume"].append([timestamp, current_volume])
            state_db["flasks"].append([timestamp, current_flasks])
            
            with open(file_path, "w", encoding="utf-8") as f: json.dump(state_db, f, ensure_ascii=False, indent=4)
                
            lib.log(f"[SERIAL] Hardware state history successfully updated in {file_path}")
            
        except Exception as e: lib.log(f"[SERIAL] State history save error: {e}")

    def close(self):
        self.is_running = False
        if self.ser and self.ser.is_open: self.ser.close()
        lib.log("[SERIAL] Serial port closed.")