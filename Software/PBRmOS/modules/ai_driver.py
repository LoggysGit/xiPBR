import os
import json

import numpy as np
from datetime import datetime

from sklearn.model_selection import train_test_split
import xgboost as xgb
from llama_cpp import Llama

import modules.lib as lib

class XGB:
    def __init__(self, model_count, estimators, depth, name, lr=0.01):
        self.name = name
        self.folder = lib.AI_DIR / name
        
        self.model_count = model_count
        self.models = []

        for i in range(model_count):
            self.models.append(xgb.XGBRegressor(
                n_estimators=estimators,
                max_depth=depth,
                learning_rate=lr,
                random_state=67
            ))
        self.is_trained = False

    def get_name(self): return self.name

    def train(self):
        """XGB Training"""
        lib.log(f"[XGB] {self.name}'s training started.")
        dataset_path = self.folder / "train_data.jsonl"
        
        # Parse JSONL
        X, Y = [], []
        with open(dataset_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                X.append(data['input'])
                Y.append(data['output'])

        #if len(Y.shape) == 1: Y = Y.reshape(-1, 1)
        X, Y = np.array(X), np.array(Y)

        lib.log(f"[XGB] > Training data loaded.")

        if Y.shape[1] != self.model_count:
            lib.log(f"[XGB] Output size in ({Y.shape[1]}) dataset is not corresponding with model_count ({self.model_count})")
            raise Exception(f"[XGB] Output size in ({Y.shape[1]}) dataset is not corresponding with model_count ({self.model_count})")
        
        # Split dataset: Train - 80%, Valid - 20%
        X_train, X_val, Y_train, Y_val = train_test_split(X, Y, test_size=0.2, random_state=42)
        
        # Learn every model
        for i in range(self.model_count):
            lib.log(f"[XGB] > Training submodel #{i}")
            self.models[i].fit(
                X_train, Y_train[:, i],
                eval_set=[(X_val, Y_val[:, i])],
                verbose=False
            )
        
        self.is_trained = True
        lib.log(f"[XGB] {self.name} trained.")

    def predict(self, input_vector):
        if not self.is_trained:
            lib.log(f"[XGB] {self.name} has not trained.")
            raise Exception(f"[XGB] {self.name} has not trained.")
            
        X_input = np.array([input_vector])
        res = [float(m.predict(X_input)[0]) for m in self.models]
        
        return res

    def save_model(self):
        """Save XGB model"""
        for i in range(self.model_count):
            path = self.folder / f"model_{i}"
            self.models[i].save_model(path)
        lib.log(f"[XGB] {self.name} saved.")

    def load_model(self):
        """Load XGB model"""
        for i in range(self.model_count):
            path = self.folder / f"model_{i}"
            self.models[i].load_model(path)
        self.is_trained = True
        lib.log(f"[XGB] {self.name} loaded.")

class AIAssistant:
    def __init__(self, path):
        self.data_folder = os.path.join(lib.AI_DIR, "LLM")
        self.model = Llama(
            model_path=path,
            n_ctx=32768,
            n_threads=4,
            verbose=False
        )
        self.answer_tokens = 384

    def save(self, user, content):
        history_path = os.path.join(self.data_folder, "history.json")

        timestamp = datetime.now().strftime("%d.%m.%Y-%H:%M:%S:%f")[:-3]

        new_entry = {
            "time": timestamp,
            "author": user,
            "content": content
        }

        history_data = []
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    if not isinstance(history_data, list): history_data = []
            except (json.JSONDecodeError, IOError): history_data = []
        history_data.append(new_entry)

        try:
            with open(history_path, 'w', encoding='utf-8') as f: json.dump(history_data, f, ensure_ascii=False, indent=4)
        except IOError as e: print(f"[AI] History error: {e}")

    def get_context(self, data="", machine_state="", hist_window=6):
        # 1. Load Personality Matrix
        personality_file_path = os.path.join(self.data_folder, "personality.json")
        try:
            with open(personality_file_path, 'r', encoding='utf-8') as f: 
                pers_data = json.load(f)

            p_rules = pers_data.get('rules', {})
            forbidden = "\n".join([f"- {r}" for r in p_rules.get('never', [])])
            forced = "\n".join([f"- {r}" for r in p_rules.get('always', [])])
            
            formatted_examples = ""
            for ex in p_rules.get('examples', []): 
                formatted_examples += f"\nUser: {ex.get('user')}\nRAIS: {ex.get('answer')}"

            personality = (
                f"Role: {pers_data.get('role', 'RAIS Peer')}\n"
                f"Tone: {pers_data.get('tone', '')}\n"
                f"Never:\n{forbidden}\nAlways:\n{forced}\n"
                f"Examples:{formatted_examples}"
            )
        except Exception: 
            personality = "Standard RAIS configuration active."

        # 2. Load Instructions & Strip Heavy DB Datasets
        instructions_file_path = os.path.join(self.data_folder, "instructions.json")
        try:
            with open(instructions_file_path, 'r', encoding='utf-8') as f: 
                inst_data = json.load(f)

            rules_str = "\n".join([f"- {rule}" for rule in inst_data.get("main_rules", [])])
            raw_db = inst_data.get('database', {})

            cleaned_db = {}
            if isinstance(raw_db, dict):
                for k, v in raw_db.items():
                    if isinstance(v, list):
                        cleaned_db[k] = f"Array validation profile: Active. Tail sequence: {v[-2:] if v else 'Empty'}"
                    elif isinstance(v, dict):
                        cleaned_db[k] = {sub_k: (sub_v if not isinstance(sub_v, list) else "Array Data") for sub_k, sub_v in v.items()}
                    else:
                        cleaned_db[k] = v
            else:
                cleaned_db = "Static framework profile loaded."

            instructions = (
                f"Context: {inst_data.get('context')}\n"
                f"Static DB Reference: {json.dumps(cleaned_db, separators=(',', ':'))}\n"
                f"Rules:\n{rules_str}"
            )
        except Exception: 
            instructions = "Default execution constants implemented."

        # 3. Process Conversation History Window
        history_file_path = os.path.join(self.data_folder, "history.json")
        formatted_history = ""
        try:
            with open(history_file_path, 'r', encoding='utf-8') as f: hist_data = json.load(f)

            history_list = hist_data if isinstance(hist_data, list) else hist_data.get("history", [])
            active_turns = history_list[-hist_window:]
            
            for turn in active_turns:
                author = turn.get("author", "")
                content = turn.get("content", "")
                
                if author == "user": formatted_history += f"<start_of_turn>user\n{content}<end_of_turn>\n"
                elif author == "assistant": formatted_history += f"<start_of_turn>model\n{content}<end_of_turn>\n"
        except Exception: formatted_history = ""

        # 4. Parse History Logs and Extract Latest Machine State Profile
        if len(data) > 900:
            data = data[-900:] + "\n[Telemetry log truncated for resource optimization]"

        hardware_context = ""
        if machine_state and isinstance(machine_state, dict):
            try:
                # Extract the latest entry [timestamp, value_dict/bool] safely for each domain
                latest_conn   = machine_state.get("connection", [])[-1] if machine_state.get("connection") else ["UNKNOWN", False]
                latest_state  = machine_state.get("state", [])[-1]      if machine_state.get("state")      else ["UNKNOWN", {}]
                latest_volume = machine_state.get("volume", [])[-1]     if machine_state.get("volume")     else ["UNKNOWN", {}]
                latest_flasks = machine_state.get("flasks", [])[-1]     if machine_state.get("flasks")     else ["UNKNOWN", {}]

                # Compress into a lightweight structural snapshot
                snapshot = {
                    "last_sync": latest_conn[0],
                    "hardware_active": latest_conn[1],
                    "actuators_state": latest_state[1],
                    "liquid_volume": latest_volume[1],
                    "nutrient_flasks": latest_flasks[1]
                }
                hardware_context = f"CURRENT HARDWARE SNAPSHOT:\n{json.dumps(snapshot, indent=2)}\n\n"
            except Exception as e:
                hardware_context = f"CURRENT HARDWARE SNAPSHOT:\n[Parsing failed: {str(e)}]\n\n"

        system_directive = (
            f"<start_of_turn>system\n"
            f"SYSTEM INSTRUCTIONS:\n{instructions}\n\n"
            f"CORE PERSONALITY MATRIX:\n{personality}\n\n"
            f"{hardware_context}"
            f"REAL-TIME LOG DATA INPUT:\n{data}\n"
            f"YOU MUST FOLLOW THIS INSTRUCTIONS.\n<end_of_turn>\n"
        )
        
        return system_directive, formatted_history
    
    def ask(self, prompt, data="", mstate="", save=True):
        lib.log("[AI] AI Assistant started to think...")

        system_directive, formatted_history = self.get_context(data, mstate)
        
        formatted_prompt = (
            f"{system_directive}"
            f"{formatted_history}"
            f"<start_of_turn>user\n{prompt}<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )

        if save: self.save("user", prompt)

        output = self.model(
            formatted_prompt,
            max_tokens=self.answer_tokens,
            stop=["<end_of_turn>"],
            echo=False
        )
        res = output['choices'][0]['text']

        if save: self.save("assistant", res)

        lib.log("[AI] AI Assistant returned an answer.")
        lib.AI_UI_CHANGED = True

        return res

class Translator:
    def __init__(self, input_lang, output_lang):
        self.source_language = input_lang
        self.target_language = output_lang

class TTS:
    def __init__(self, model_path):
        pass

class SpeechRecognizer:
    def __init__(self, lang):
        pass