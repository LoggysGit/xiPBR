import json
import random
from pathlib import Path

import modules.lib as lib
import modules.ai_driver as AIManager

stateWatcher = AIManager.XGB(1, 1024, 12, "StateWatcher")   # Output -> Culture health state (%)
harvester    = AIManager.XGB(1, 1024, 12, "Harvester")      # Output -> Ready for harvest (%)

def apply_noise(val, fluct_val, scale=1.0):
    noise = random.uniform(-fluct_val * scale, fluct_val * scale)
    shifts.append(noise / (fluct_val * scale) if fluct_val != 0 else 0)
    return val + noise

def run_state_watcher_tests(model, test_cases):    
    print("\n" + "="*85)
    print(f"{'ENVIRONMENT STATE':<30} | {'ACTUAL':<8} | {'PREDICT':<8} | {'ERROR DELTA':<11}")
    print("="*85)
    
    for features, real, description in test_cases:
        prediction = model.predict(features)[0] 
        
        pred_str = f"{prediction:.2f}%" if prediction >= 0 else f"{int(prediction)}"
        real_str = f"{real}%" if real >= 0 else f"{real}"
        
        if real <= -1: error_str = "OK" if int(prediction) <= -1 else "ERR_MISSED"
        else: error_str = f"{prediction - real:+.2f}%"
            
        print(f"{description:<30} | {real_str:<8} | {pred_str:<8} | {error_str:<11}")
        
    print("="*85 + "\n")

sw_train_chunks = [
    [
        {"input": [9.50, 33.0, 0.80, 0.25, 0.05, 80, 80, 80, 3.0], "output": [95]},
        {"input": [9.35, 32.8, 0.78, 0.22, 0.04, 85, 85, 85, 2.5], "output": [92]},
        {"input": [9.20, 32.5, 0.75, 0.20, 0.04, 90, 90, 90, 2.0], "output": [89]},
        {"input": [9.40, 33.0, 0.20, 0.10, 0.03, 80, 80, 80, 0.5], "output": [88]},
    ], [
        {"input": [9.70, 34.0, 0.85, 0.15, 0.02, 70, 70, 70, 4.5], "output": [82]},
        {"input": [9.90, 34.5, 0.90, 0.05, 0.00, 60, 60, 60, 6.0], "output": [70]},
        {"input": [8.90, 29.0, 0.45, 0.08, 0.02, 100, 100, 100, 1.2], "output": [65]},
        {"input": [10.10, 34.8, 0.91, -0.01, 0.00, 50, 50, 50, 7.0], "output": [58]}
    ], [
        {"input": [8.50, 26.0, 0.40, -0.04, -0.01, 100, 100, 100, 2.0], "output": [45]},
        {"input": [10.30, 36.2, 0.89, -0.08, -0.03, 100, 100, 100, 5.5], "output": [38]},
        {"input": [8.30, 24.5, 0.38, -0.08, -0.02, 100, 100, 100, 2.2], "output": [30]}
    ], [
        {"input": [7.80, 21.0, 0.32, -0.18, -0.06, 0, 0, 0, 3.5], "output": [15]},
        {"input": [10.70, 38.5, 0.85, -0.15, -0.05, 100, 100, 100, 6.5], "output": [8]},
        {"input": [7.20, 18.0, 0.25, -0.25, -0.08, 0, 0, 0, 4.0], "output": [2]}
    ], [
        {"input": [-9.00, 33.0, 0.80, 0.00, 0.00, 80, 80, 80, 3.0], "output": [-1]},
        {"input": [9.50, -99.0, 0.80, 0.25, 0.05, 80, 80, 80, 3.0], "output": [-1]},
        {"input": [9.50, 33.0, -1.00, 0.25, 0.05, 80, 80, 80, 3.0], "output": [-1]},
        {"input": [-9.00, -99.0, -1.00, 0.00, 0.00, 0, 0, 0, 0.0], "output": [-1]},
    ]
]

h_train_chunks = [
    # Class 1: Definite Harvest (85-100) -> High density, stable pH, enough time elapsed
    [
        {"input": [10.0, 500, 0.85, 0.05, 0.22, 9.6, 9.5, 9.4, 4.0, 450, 0.80, 33.2], "output": [96]},
        {"input": [10.0, 400, 0.90, 0.03, 0.25, 9.7, 9.6, 9.5, 5.2, 500, 0.82, 34.0], "output": [98]},
        {"input": [12.0, 600, 0.82, 0.06, 0.20, 9.5, 9.4, 9.3, 3.5, 550, 0.78, 32.8], "output": [92]},
        {"input": [8.0,  350, 0.88, 0.04, 0.24, 9.6, 9.5, 9.4, 4.5, 350, 0.81, 33.5], "output": [95]},
        {"input": [10.0, 500, 0.95, 0.01, 0.28, 9.8, 9.7, 9.5, 6.0, 450, 0.83, 34.5], "output": [99]},
        {"input": [10.0, 450, 0.80, 0.07, 0.19, 9.4, 9.3, 9.2, 3.1, 400, 0.75, 32.5], "output": [86]},
        {"input": [15.0, 750, 0.84, 0.05, 0.21, 9.5, 9.5, 9.3, 3.8, 700, 0.79, 33.0], "output": [91]}
    ],
    # Class 2: Wait / Conditional Harvest (50-84) -> Medium density, growth slowing down, or early days
    [
        {"input": [10.0, 500, 0.65, 0.04, 0.15, 9.3, 9.2, 9.1, 2.5, 450, 0.80, 31.5], "output": [75]},
        {"input": [10.0, 400, 0.72, 0.02, 0.11, 9.4, 9.4, 9.3, 2.9, 500, 0.82, 32.0], "output": [79]},
        {"input": [12.0, 600, 0.58, 0.05, 0.18, 9.2, 9.1, 9.0, 2.1, 550, 0.78, 30.8], "output": [62]},
        {"input": [8.0,  350, 0.70, 0.01, 0.09, 9.5, 9.4, 9.4, 3.0, 350, 0.81, 32.2], "output": [71]},
        {"input": [10.0, 500, 0.78, -0.01, 0.05, 9.6, 9.7, 9.6, 4.0, 450, 0.83, 33.8], "output": [82]}, # Density is fine but flatlining
        {"input": [10.0, 450, 0.52, 0.06, 0.22, 9.1, 9.0, 8.9, 1.8, 400, 0.75, 30.2], "output": [55]},
        {"input": [15.0, 750, 0.68, 0.03, 0.14, 9.3, 9.3, 9.2, 2.7, 700, 0.79, 31.9], "output": [77]}
    ],
    # Class 3: Wait / Don't Touch (0-49) -> Low concentration, post-harvest state, or stressed culture
    [
        {"input": [10.0, 500, 0.25, 0.08, -0.10, 9.2, 9.0, 9.3, 0.5, 450, 0.80, 32.0], "output": [15]}, # Just harvested yesterday
        {"input": [10.0, 400, 0.35, 0.05, -0.05, 9.3, 9.1, 9.4, 1.1, 500, 0.82, 32.5], "output": [25]},
        {"input": [12.0, 600, 0.18, 0.02, -0.20, 8.9, 8.8, 9.1, 0.2, 550, 0.78, 29.5], "output": [5]},
        {"input": [8.0,  350, 0.42, 0.03, 0.02,  9.4, 9.3, 9.3, 1.5, 350, 0.81, 31.8], "output": [38]},
        {"input": [10.0, 500, 0.48, -0.05, -0.15, 8.5, 8.8, 9.2, 3.5, 450, 0.83, 26.0], "output": [20]}, # Acid shock / stalling
        {"input": [10.0, 450, 0.30, 0.04, -0.08, 9.1, 9.0, 9.2, 0.8, 400, 0.75, 30.0], "output": [18]},
        {"input": [15.0, 750, 0.38, 0.06, -0.02, 9.2, 9.1, 9.3, 1.2, 700, 0.79, 31.0], "output": [30]}
    ],
    # Class 4: Sensor Faults (-1024) -> Drop targeted variables into deep freeze
    [
        {"input": [10.0, 500, -1.00, 0.00, 0.00, 9.6, 9.5, 9.4, 4.0, 450, 0.80, 33.2], "output": [-1024]}, # Turbidity fail
        {"input": [10.0, 400, 0.90, 0.03, 0.25, -9.0, 9.6, 9.5, 5.2, 500, 0.82, 34.0], "output": [-1024]}, # pH fail
        {"input": [12.0, 600, 0.82, 0.06, 0.20, 9.5, 9.4, 9.3, 3.5, 550, 0.78, -99.0], "output": [-1024]}, # Temp fail
        {"input": [-1.0, 350, -1.00, 0.00, 0.00, -9.0, 9.5, -9.0, 4.5, 350, 0.81, -99.0], "output": [-1024]}, # Multi crash
        {"input": [10.0, 500, 0.95, 0.01, 0.28, 9.8, -9.0, 9.5, 6.0, 450, 0.83, 34.5], "output": [-1024]}, # Avg pH fail
        {"input": [10.0, 450, -1.00, 0.00, 0.00, 9.4, 9.3, 9.2, 3.1, 400, -1.00, 32.5], "output": [-1024]}, # Density logs fail
        {"input": [15.0, 750, 0.84, 0.05, 0.21, -9.0, -9.0, -9.0, 3.8, 700, 0.79, 33.0], "output": [-1024]}  # Entire pH vector dead
    ]
]

# ======== Generate train data for state watcher ========
with open(lib.AI_DIR / stateWatcher.get_name() / "train_data.jsonl", 'w', encoding='utf-8') as sw_train:
    for chunk_idx, chunk in enumerate(sw_train_chunks):
        for _ in range(500):
            base_obj = random.choice(chunk)
            base_in = base_obj["input"]
            base_out = base_obj["output"][0]
            
            if chunk_idx == 4:
                ph, temp, turb = base_in[0], base_in[1], base_in[2]
                d_ph, d_turb = base_in[3], base_in[4]
                l1, l2, l3 = base_in[5], base_in[6], base_in[7]
                elapsed = base_in[8]
                target = -1024
            else:
                fluct = random.uniform(0.5, 2.0)
                
                shifts = []

                ph = round(apply_noise(base_in[0], fluct, scale=0.15), 2)
                temp = round(apply_noise(base_in[1], fluct, scale=1.0), 1)

                turb = round(max(0.01, apply_noise(base_in[2], fluct, scale=0.05)), 2)
                
                d_ph = round(apply_noise(base_in[3], fluct, scale=0.03), 2)
                d_turb = round(apply_noise(base_in[4], fluct, scale=0.01), 3)

                l1 = int(max(0, min(100, apply_noise(base_in[5], fluct, scale=5.0))))
                l2 = int(max(0, min(100, apply_noise(base_in[6], fluct, scale=5.0))))
                l3 = int(max(0, min(100, apply_noise(base_in[7], fluct, scale=5.0))))
                
                elapsed = round(max(0.0, apply_noise(base_in[8], fluct, scale=0.3)), 1)

                mean_shift = sum(shifts) / len(shifts)

                target_drift = int(mean_shift * fluct * 3.0)
                calculated_target = base_out + target_drift

                if chunk_idx == 0: target = max(85, min(100, calculated_target))
                elif chunk_idx == 1: target = max(50, min(84, calculated_target))
                elif chunk_idx == 2: target = max(25, min(49, calculated_target))
                elif chunk_idx == 3: target = max(0, min(24, calculated_target))

            generated_line = {
                "input": [ph, temp, turb, d_ph, d_turb, l1, l2, l3, elapsed],
                "output": [target]
            }
            sw_train.write(json.dumps(generated_line) + "\n")
# Test cases: [features, real_target, log_description]
sw_test_cases = [
        # 1. Ideal State (85-100)
        ([9.55, 33.1, 0.82, 0.26, 0.052, 80, 80, 80, 2.9], 96, "Ideal (Growth Peak)"),
        ([9.38, 32.7, 0.22, 0.11, 0.032, 82, 80, 85, 0.6], 89, "Ideal (Post-Harvest)"),
        
        # 2. Medium State (50-84)
        ([9.75, 34.2, 0.87, 0.12, 0.015, 68, 70, 65, 4.8], 78, "Medium (Stagnation/Plateau)"),
        ([8.95, 29.5, 0.48, 0.09, 0.022, 95, 95, 100, 1.4], 68, "Medium (Young/Chilled)"),
        
        # 3. Critical State (25-49)
        ([8.42, 25.5, 0.42, -0.05, -0.012, 100, 100, 100, 2.1], 42, "Critical (Acid/Cold Shock)"),
        ([10.38, 36.5, 0.88, -0.09, -0.034, 95, 95, 95, 5.8], 35, "Critical (Light/Heat Shock)"),
        
        # 4. Lethal State (0-24)
        ([7.65, 20.5, 0.30, -0.21, -0.065, 0, 0, 0, 3.7], 12, "Lethal (Freezing Death)"),
        ([10.75, 38.9, 0.83, -0.17, -0.058, 100, 100, 100, 6.9], 6, "Lethal (Culture Bleaching)"),
        
        # 5. Sensor Faults (-1)
        ([-9.00, 32.5, 0.78, 0.00, 0.00, 80, 80, 80, 3.0], -1, "Fault (pH Disconnect)"),
        ([9.45, 33.2, -1.00, 0.22, 0.045, 0, 0, 0, 1.5], -1, "Fault (Turbidity Disconnect)")
    ]

# ======== Generate train data for harvester ========
fault_inputs = [item["input"] for item in h_train_chunks[3]]
param_pools = [list(p) for p in zip(*fault_inputs)]
with open(lib.AI_DIR / harvester.get_name() / "train_data.jsonl", 'w', encoding='utf-8') as h_train:
    for chunk_idx, chunk in enumerate(h_train_chunks):
        for _ in range(500):
            if chunk_idx == 3:
                # Sensor Faults -> Fully shuffle parameters across different test cases
                shuffled_in = []
                for i in range(12):
                    # Randomly pick a value from the pool of the i-th parameter
                    shuffled_in.append(random.choice(param_pools[i]))
                
                # Apply reduced fluctuations to non-fault variables
                fluct = random.uniform(0.1, 0.5)
                
                # 1. Config constants (Keep rock solid)
                max_liters = shuffled_in[0]
                harv_amount = shuffled_in[1]
                # 2. Turbidity check
                curr_conc = shuffled_in[2] if shuffled_in[2] == -1.0 else round(shuffled_in[2] + random.uniform(-fluct * 0.02, fluct * 0.02), 2)
                d_conc = shuffled_in[3] if shuffled_in[2] == -1.0 else round(shuffled_in[3] + random.uniform(-fluct * 0.01, fluct * 0.01), 2)
                w_conc = shuffled_in[4] if shuffled_in[2] == -1.0 else round(shuffled_in[4] + random.uniform(-fluct * 0.02, fluct * 0.02), 2)
                # 3. pH check
                curr_ph = shuffled_in[5] if shuffled_in[5] == -9.0 else round(shuffled_in[5] + random.uniform(-fluct * 0.05, fluct * 0.05), 2)
                d_ph = shuffled_in[6] if shuffled_in[6] == -9.0 else round(shuffled_in[6] + random.uniform(-fluct * 0.05, fluct * 0.05), 2)
                w_ph = shuffled_in[7] if shuffled_in[7] == -9.0 else round(shuffled_in[7] + random.uniform(-fluct * 0.05, fluct * 0.05), 2)
                # 4. Logs and temperature checks
                prev_days = round(max(0.0, shuffled_in[8] + random.uniform(-fluct * 0.1, fluct * 0.1)), 1)
                prev_ml = int(max(0, shuffled_in[9] + random.uniform(-fluct * 10, fluct * 10)))
                prev_conc = shuffled_in[10] if shuffled_in[10] == -1.0 else round(shuffled_in[10] + random.uniform(-fluct * 0.02, fluct * 0.02), 2)
                
                inner_temp = shuffled_in[11] if shuffled_in[11] == -99.0 else round(shuffled_in[11] + random.uniform(-fluct * 0.3, fluct * 0.3), 1)
                
                target = -1024
                
            else:
                # Standard cases (1, 2, 3) -> Synced shift logic
                base_obj = random.choice(chunk)
                base_in = base_obj["input"]
                base_out = base_obj["output"][0]
                
                fluct = random.uniform(0.5, 2.0)
                shifts = []
                
                def apply_noise(val, scale=1.0):
                    noise = random.uniform(-fluct * scale, fluct * scale)
                    shifts.append(noise / (fluct * scale) if fluct != 0 else 0)
                    return val + noise

                # Apply proportional noise to active biological values
                max_liters = base_in[0]  # Constant
                harv_amount = base_in[1] # Constant
                
                curr_conc = round(max(0.01, apply_noise(base_in[2], scale=0.03)), 2)
                d_conc = round(apply_noise(base_in[3], scale=0.01), 2)
                w_conc = round(apply_noise(base_in[4], scale=0.04), 2)
                
                curr_ph = round(apply_noise(base_in[5], scale=0.10), 2)
                d_ph = round(apply_noise(base_in[6], scale=0.05), 2)
                w_ph = round(apply_noise(base_in[7], scale=0.05), 2)
                
                prev_days = round(max(0.0, apply_noise(base_in[8], scale=0.2)), 1)
                prev_ml = int(max(0, apply_noise(base_in[9], scale=15.0)))
                prev_conc = round(max(0.01, apply_noise(base_in[10], scale=0.03)), 2)
                
                inner_temp = round(apply_noise(base_in[11], scale=0.8), 1)

                # Dynamically shift target based on average parameter drift
                mean_shift = sum(shifts) / len(shifts)
                target_drift = int(mean_shift * fluct * 2.5)
                calculated_target = base_out + target_drift

                # Enforce absolute boundaries per class matrix
                if chunk_idx == 0:   target = max(85, min(100, calculated_target))
                elif chunk_idx == 1: target = max(50, min(84, calculated_target))
                elif chunk_idx == 2: target = max(0, min(49, calculated_target))

            # Pack vector and dump to jsonl
            generated_line = {
                "input": [
                    max_liters, harv_amount, curr_conc, d_conc, w_conc, 
                    curr_ph, d_ph, w_ph, prev_days, prev_ml, prev_conc, inner_temp
                ],
                "output": [target]
            }
            h_train.write(json.dumps(generated_line) + "\n")
# Test cases: [features, real_target, log_description]
harv_test_cases = [
    # 1. Definite Harvest (85-100)
    ([10.0, 500, 0.88, 0.04, 0.23, 9.65, 9.55, 9.42, 4.2, 450, 0.81, 33.5], 95, "Harvest (Ready Peak)"),
    ([12.0, 600, 0.81, 0.05, 0.19, 9.45, 9.38, 9.28, 3.3, 550, 0.76, 32.6], 88, "Harvest (Optimal Growth)"),
    
    # 2. Wait / Conditional Harvest (50-84)
    ([10.0, 500, 0.68, 0.03, 0.13, 9.35, 9.25, 9.15, 2.3, 450, 0.79, 31.8], 74, "Wait (Linear Growth)"),
    ([10.0, 400, 0.79, -0.02, 0.04, 9.62, 9.68, 9.58, 4.2, 450, 0.82, 33.9], 80, "Wait (Density High/Flatline)"),
    
    # 3. Wait / Don't Touch (0-49)
    ([10.0, 500, 0.22, 0.07, -0.12, 9.15, 9.02, 9.32, 0.4, 450, 0.78, 32.2], 12, "Wait (Just Harvested)"),
    ([10.0, 500, 0.46, -0.04, -0.13, 8.55, 8.85, 9.18, 3.3, 450, 0.81, 26.5], 22, "Wait (Acid/Cold Stalling)"),
    
    # 4. Sensor Faults (-1024)
    ([10.0, 500, -1.00, 0.00, 0.00, 9.60, 9.50, 9.40, 4.0, 450, 0.80, 33.2], -1024, "Fault (Turbidity Fail)"),
    ([10.0, 400, 0.90, 0.03, 0.25, -9.00, 9.60, 9.50, 5.2, 500, 0.82, 34.0], -1024, "Fault (pH Matrix Crash)"),
    ([12.0, 600, 0.82, 0.06, 0.20, 9.50, 9.40, 9.30, 3.5, 550, 0.78, -99.0], -1024, "Fault (Temp Disconnect)")
]

### ========================= ###

stateWatcher.train()
harvester.train()

print("\n------------- State Watcher -------------")
run_state_watcher_tests(stateWatcher, sw_test_cases)
print("\n------------- Harvester -------------")
run_state_watcher_tests(harvester, harv_test_cases)

stateWatcher.save_model()
harvester.save_model()