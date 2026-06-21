import sys
import os
import math

import time
import queue

from datetime import datetime, timedelta
import calendar

import customtkinter as ctk

import modules.lib as lib

import customtkinter

class ValidatedNumberEntry(customtkinter.CTkEntry):
    def __init__(self, master, min_val=0, max_val=100, allow_float=False, default_val=None, **kwargs):
        # Default placeholder
        if default_val is not None and "placeholder_text" not in kwargs: kwargs["placeholder_text"] = str(default_val)
            
        super().__init__(master, **kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.allow_float = allow_float
        self.default_val = default_val
        
        vcmd = (self.register(self._validate_input), '%P')
        self.configure(validate="key", validatecommand=vcmd)

        self.bind("<FocusOut>", self._on_focus_out)
        
    def _validate_input(self, new_value):
        # Empty
        if new_value == "": return True
        # Sign
        if new_value == "-" and self.min_val < 0: return True
        # Float
        if self.allow_float:
            if new_value.endswith(".") and new_value.count(".") == 1:
                try:
                    base = new_value[:-1]
                    if base == "" or base == "-": return True
                    return self.min_val <= float(base) <= self.max_val
                except ValueError: return False
            try: return self.min_val <= float(new_value) <= self.max_val
            except ValueError: return False
        # Int
        else:
            if not new_value.lstrip('-').isdigit(): return False
            return self.min_val <= int(new_value) <= self.max_val
        
    def _on_focus_out(self, event):
        raw_value = self.get()
        if raw_value == "" or raw_value == "-":
            if self.default_val is not None:
                self.delete(0, "end")
                self.insert(0, str(self.default_val))

    def get_val(self):
        raw_value = self.get()
        
        if raw_value == "" or raw_value == "-":
            if self.default_val is not None: return self.default_val
            return self.min_val
            
        return float(raw_value) if self.allow_float else int(raw_value)
    
class StatusBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=8, **kwargs)
        
        # Wi-Fi & Time
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)

        # Wi-FI style
        self.wifi_badge = ctk.CTkFrame(
            self, width=35, height=35, corner_radius=6,
            fg_color=("#DBDBDB", "#2D2D2D"), border_width=1, border_color=("#CCCCCC", "#444444")
        )
        self.wifi_badge.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        self.wifi_badge.grid_propagate(False)
        self.wifi_badge.grid_columnconfigure(0, weight=1)
        self.wifi_badge.grid_rowconfigure(0, weight=1)

        self.lbl_wifi = ctk.CTkLabel(self.wifi_badge, text="V", font=master.font_text_bold, text_color=("black", "white"))
        self.lbl_wifi.grid(row=0, column=0)

        # Time style
        self.time_badge = ctk.CTkFrame(
            self, width=70, height=35, corner_radius=6,
            fg_color=("#DBDBDB", "#2D2D2D"), border_width=1, border_color=("#CCCCCC", "#444444")
        )
        self.time_badge.grid(row=0, column=1, sticky="nsew")
        self.time_badge.grid_propagate(False)
        self.time_badge.grid_columnconfigure(0, weight=1)
        self.time_badge.grid_rowconfigure(0, weight=1)

        self.lbl_time = ctk.CTkLabel(self.time_badge, text="12:37", font=master.font_text_med, text_color=("black", "white"))
        self.lbl_time.grid(row=0, column=0)

    def update_time(self, new_time_str):
        self.lbl_time.configure(text=new_time_str)

    def update_wifi(self, status_text):
        self.lbl_wifi.configure(text=status_text)

class VirtualKeyboard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.current_target = None
        self.is_shift = False
        self.layout = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
        ["a", "s", "d", "f", "g", "h", "j", "k", "l", "-"],
        ["z", "x", "c", "v", "b", "n", "m", ",", ".", "?"],
        ["Shift", "Space", "Backspace", "Close", "Done"]
        ]

        # Generate keyboard grid
        for i in range(5): self.grid_rowconfigure(i, weight=1)
        for i in range(10): self.grid_columnconfigure(i, weight=1)
        self.init_keys()

    def init_keys(self):
        # Clear all
        for child in self.winfo_children(): child.destroy()
        # Draw
        for row_idx, row in enumerate(self.layout):
            for col_idx, key in enumerate(row):
                    colspan = 1
                    if key == "Space": colspan = 4
                    #"Close", "Done"
                    elif key in ["Backspace", "Shift"]: colspan = 2

                    # Style
                    btn = ctk.CTkButton(
                        self, text=key,
                        font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"),
                        height=45, corner_radius=6,
                        fg_color=("#D0D0D0", "#2D2D2D") if key not in ["Close", "Backspace", "Done"] else "#1F6AA5",
                        text_color=("black", "white"),
                        command=lambda k=key: self.on_key_click(k)
                    )

                    # Functional buttons
                    current_col = col_idx
                    if row_idx == 4:
                        if key == "Close": current_col = 0
                        elif key == "Shift": current_col = 1
                        elif key == "Space": current_col = 3
                        elif key == "Backspace": current_col = 7
                        elif key == "Done": current_col = 9

                    btn.grid(row=row_idx, column=current_col, columnspan=colspan, padx=4, pady=4, sticky="nsew")

    def set_target(self, widget): self.current_target = widget

    def get_shift_key(self, k):
        specials = {
        ".": ":",
        "?": "!",
        ",": ";"
        }
        specials_reverse = {v: k for k, v in specials.items()}

        if self.is_shift:
            if k in specials: return specials[k]
            elif len(k) == 1: return k.upper()
        else:
            if k in specials_reverse: return specials_reverse[k]
            elif len(k) == 1: return k.lower()
        return k

    def on_key_click(self, key):
        if not self.current_target: return

        if key == "Close":
            lib.log("[UI] Virtual keyboard closed.")
            self.grid_remove()
            return
       
        elif key == "Done":
            lib.log("[UI] Virtual keyboard enter.")
            if self.current_target: self.master.focus()
            self.grid_remove()
            return

        elif key == "Backspace":
            target_type = self.current_target.__class__.__name__.lower()

            if "entry" in target_type:
                    real_entry = self.current_target._entry if hasattr(self.current_target, "_entry") else self.current_target
                    cursor_pos = real_entry.index("insert")
                    if cursor_pos > 0: real_entry.delete(cursor_pos - 1, cursor_pos)

            elif "textbox" in target_type:
                    real_textbox = self.current_target._textbox if hasattr(self.current_target, "_textbox") else self.current_target
                    try: real_textbox.delete("insert - 1 chars", "insert")
                    except Exception as e: lib.log(f"[UI] Backspace key Error {e}")

        elif key == "Shift":
            self.is_shift = not self.is_shift
            self.layout = [[self.get_shift_key(k) for k in row] for row in self.layout]
            self.init_keys()
            print(f"Shift clicked! {self.is_shift}")
       
        elif key == "Space": self.insert_text(" ")
        else: 
            self.insert_text(key)

            self.is_shift = False
            self.layout = [[self.get_shift_key(k) for k in row] for row in self.layout]
            self.init_keys()

    def insert_text(self, text):
        if not self.current_target: return

        # Get class name
        target_type = self.current_target.__class__.__name__.lower()

        # Insert (Entry)
        if "entry" in target_type:
            if hasattr(self.current_target, "_entry"): self.current_target._entry.insert("insert", text)
            else: self.current_target.insert("insert", text)
        # Insert (Textbox)
        elif "textbox" in target_type:
            if hasattr(self.current_target, "_textbox"): self.current_target._textbox.insert("insert", text)
            else: self.current_target.insert("insert", text)

class ExtendedChart(ctk.CTkFrame):
    def __init__(self, parent, font_semibold, font_reg_small, database_json):
        super().__init__(parent, fg_color=("#F5F5F5", "#1A1A1A"), corner_radius=0)
        
        self.font_semibold = font_semibold
        self.font_reg_small = font_reg_small
        self.database_json = database_json
        self.data_key = None
        self.period_days = 7
        
        # Touch & Drag memory blocks
        self.drag_start_x = 0
        self.drag_offset_x = 30
        
        # Set layout architecture
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.build_ui()

    def build_ui(self):
        # 1. TOP HEADER
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.lbl_title = ctk.CTkLabel(self.header_frame, text="CHART DETAILED VIEW", font=self.font_semibold, text_color=("#111111", "#EEEEEE"))
        self.lbl_title.grid(row=0, column=0, sticky="w")

        # Timeframe Selector
        self.timeframe_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.timeframe_frame.grid(row=0, column=1, sticky="e", padx=20)
        
        periods = [("1D", 1), ("7D", 7), ("30D", 30)]
        for idx, (label, days) in enumerate(periods):
            btn = ctk.CTkButton(
                self.timeframe_frame, text=label, width=60, height=35,
                font=self.font_semibold,
                fg_color="#1F6AA5" if days == self.period_days else ("#DBDBDB", "#2B2B2B"),
                text_color="white" if days == self.period_days else ("#111111", "#EEEEEE"),
                command=lambda d=days: self.change_period(d)
            )
            btn.grid(row=0, column=idx, padx=5)

        # Large Touch Exit Button
        btn_close = ctk.CTkButton(
            self.header_frame, text="✕", width=45, height=45,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=("#E0E0E0", "#2B2B2B"),
            hover_color=("#CDCDCD", "#3A3A3A"),
            text_color=("#111111", "#EEEEEE"),
            corner_radius=12,
            command=self.close_extended_view
        )
        btn_close.grid(row=0, column=2, sticky="e")

        # 2. EXPANDED CANVAS AREA
        self.canvas_card = ctk.CTkFrame(self, fg_color=("#FFFFFF", "#111111"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        self.canvas_card.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
        self.canvas_card.grid_columnconfigure(0, weight=1)
        self.canvas_card.grid_rowconfigure(0, weight=1)

        self.canvas = ctk.CTkCanvas(
            self.canvas_card, bg="#111111" if ctk.get_appearance_mode() == "Dark" else "#FFFFFF", 
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        # Touch screen event bindings
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.execute_drag)
        self.canvas.bind("<Configure>", lambda event: self.redraw_graph())

    def set_data_key(self, data_key, title_text=""):
        self.data_key = data_key
        if title_text:
            self.lbl_title.configure(text=title_text.upper())
        self.drag_offset_x = 0  # Reset viewport drag state
        self.redraw_graph()

    def change_period(self, days):
        self.period_days = days
        self.drag_offset_x = 0
        # Re-render active state highlights on buttons
        for child in self.timeframe_frame.winfo_children():
            if child.cget("text") == f"{days}D" or (days == 1 and child.cget("text") == "1D"):
                child.configure(fg_color="#1F6AA5", text_color="white")
            else:
                child.configure(fg_color=("#DBDBDB", "#2B2B2B"), text_color=("#111111", "#EEEEEE"))
        self.redraw_graph()

    # - Functions -
    def start_drag(self, event): self.drag_start_x = event.x

    def execute_drag(self, event):
        delta_x = event.x - self.drag_start_x

        self.drag_offset_x += delta_x
        if self.drag_offset_x > 30: self.drag_offset_x = 30

        self.drag_start_x = event.x
        self.redraw_graph()

    def close_extended_view(self): self.grid_forget()

    def redraw_graph(self):
        self.canvas.delete("all")
        if not self.data_key: return

        raw_data = self.database_json.get(self.data_key, [])
        if not raw_data:
            self.canvas.create_text(
                self.canvas.winfo_width()/2, self.canvas.winfo_height()/2,
                text="NO METRICS AVAILABLE", font=self.font_reg_small, fill="gray"
            )
            return

        W = self.canvas.winfo_width()
        H = self.canvas.winfo_height()
        if W <= 1 or H <= 1: return

        pad_y_top = 40
        pad_y_bottom = 60
        pad_x_left = 110
        pad_x_right = 40

        if self.period_days == 1: points = raw_data[-12:]
        elif self.period_days == 7: points = raw_data[-40:]
        else: points = raw_data[-80:]

        if not points: return

        values = [float(pt[1]) for pt in points]
        raw_min, raw_max = min(values), max(values)
        if raw_min == raw_max:
            raw_min -= 1.0
            raw_max += 1.0

        import math
        if self.data_key == "ph":
            # Round to fractions for pH
            min_val = math.floor(raw_min * 10) / 10.0
            max_val = math.ceil(raw_max * 10) / 10.0
            if max_val - min_val < 0.5:
                max_val = min_val + 0.5
        else:
            # Integer step for other
            min_val = math.floor(raw_min)
            max_val = math.ceil(raw_max)
            if max_val - min_val < 5:
                max_val = min_val + 5
        # ------------------------------

        # Draw grid lines
        grid_lines = 6
        for i in range(grid_lines):
            f = i / (grid_lines - 1)
            y_pos = pad_y_top + f * (H - pad_y_top - pad_y_bottom)
            cur_scale_val = max_val - f * (max_val - min_val)

            self.canvas.create_line(
                pad_x_left, y_pos, W - pad_x_right, y_pos,
                fill="#222222" if ctk.get_appearance_mode() == "Dark" else "#E5E5E5",
                dash=(2, 4)
            )
            
            # Smart Y formatting
            if self.data_key == "ph":
                scale_text = f"{cur_scale_val:.2f}" if (max_val - min_val) <= 1.0 else f"{cur_scale_val:.1f}"
            elif self.data_key in ["temp_out", "temp_in"]:
                scale_text = f"{int(cur_scale_val)}°"
            else:
                scale_text = f"{int(cur_scale_val)}"

            self.canvas.create_text(
                pad_x_left - 15, y_pos,
                text=scale_text, font=self.font_reg_small,
                fill="gray", anchor="e"
            )

        num_points = len(points)
        x_step = (W - pad_x_left - pad_x_right) / max(1, num_points - 1)

        coords = []
        for idx, (timestamp, val) in enumerate(points):
            x = pad_x_left + idx * x_step + self.drag_offset_x
            y = pad_y_top + (1.0 - (float(val) - min_val) / (max_val - min_val)) * (H - pad_y_top - pad_y_bottom)
            coords.append((x, y, timestamp))

        time_label_step = max(1, num_points // 4) if not self.period_days == 1 else 1
        
        for idx in range(0, num_points, time_label_step):
            x_pos = coords[idx][0]
            timestamp = coords[idx][2]
            
            if pad_x_left <= x_pos <= (W - pad_x_right):
                self.canvas.create_line(
                    x_pos, H - pad_y_bottom, x_pos, H - pad_y_bottom + 8,
                    fill="#444444" if ctk.get_appearance_mode() == "Dark" else "#CCCCCC"
                )
                
                if "-" in timestamp:
                    date_part, time_part = timestamp.split("-")
                    formatted_text = f"{time_part}\n{date_part}"
                else: formatted_text = timestamp
                
                self.canvas.create_text(
                    x_pos, H - pad_y_bottom + 15,
                    text=formatted_text, font=self.font_reg_small,
                    fill="gray", anchor="n", justify="center"
                )

        # Layer 1: Geometry paths
        for idx in range(len(coords) - 1):
            x1, y1, _ = coords[idx]
            x2, y2, _ = coords[idx + 1]

            if pad_x_left <= x1 <= (W - pad_x_right) or pad_x_left <= x2 <= (W - pad_x_right):
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill="#1F6AA5", width=4, smooth=True
                )
                self.canvas.create_oval(
                    x1 - 4, y1 - 4, x1 + 4, y1 + 4,
                    fill="#1F6AA5" if ctk.get_appearance_mode() == "Dark" else "white",
                    outline="#1F6AA5", width=2
                )

        if num_points > 0:
            x_last, y_last, _ = coords[-1]
            if pad_x_left <= x_last <= (W - pad_x_right):
                self.canvas.create_oval(
                    x_last - 4, y_last - 4, x_last + 4, y_last + 4,
                    fill="#1F6AA5" if ctk.get_appearance_mode() == "Dark" else "white",
                    outline="#1F6AA5", width=2
                )

        # Layer 2: Text on top
        for idx in range(num_points):
            if idx % time_label_step != 0:
                continue

            x, y, _ = coords[idx]
            if not (pad_x_left <= x <= (W - pad_x_right)):
                continue

            is_local_min = False
            prev_y = coords[idx - 1][1] if idx > 0 else None
            next_y = coords[idx + 1][1] if idx < num_points - 1 else None

            if prev_y is not None and next_y is not None:
                if y > prev_y and y > next_y: is_local_min = True
            elif prev_y is not None and y > prev_y: is_local_min = True
            elif next_y is not None and y > next_y: is_local_min = True

            if is_local_min:
                y_offset = 15
                text_anchor = "n"
            else:
                y_offset = -15
                text_anchor = "s"

            # Node text precise rule
            if self.data_key == "ph":
                node_text = f"{values[idx]:.2f}"
            elif self.data_key in ["temp_out", "temp_in"]:
                node_text = f"{values[idx]:.1f}°"
            else:
                node_text = f"{int(values[idx])}"

            self.canvas.create_text(
                x, y + y_offset,
                text=node_text, font=self.font_reg_small,
                fill="#1F6AA5" if ctk.get_appearance_mode() == "Dark" else "#111111",
                anchor=text_anchor
            )

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self, port_bridge, data_manager, telemetry_json, cmd_buff, sys_commands, ai_commands):
        super().__init__()

        self.title("PBRmOS")
        self.geometry("1200x540")
        self.minsize(800, 360)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.port_bridge = port_bridge
        self.data_manager = data_manager

        self.cmd_buffer = cmd_buff
        self.sys_cmd_buff = sys_commands
        self.ai_cmd_buff = ai_commands

        self.database_json = telemetry_json

        # Load fonts
        self.init_fonts()

        self.grid_columnconfigure(0, weight=0, minsize=200) # Tab bar row
        self.grid_columnconfigure(1, weight=1)              # Pages content row
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)                 # Keyboard row

        # Class variables
        self.pages = {}
        self.menu_buttons = {}
        self.current_page_name = None

        self.current_calendar_view_year = datetime.now().year
        self.current_calendar_view_month = datetime.now().month

        self.culture_health = -1

        self._updating_light = False

        # Main UI initialization
        self.init_sidebar()
        self.init_pages()
        
        # Status bar
        self.global_status_bar = StatusBar(self)
        self.global_status_bar.place(relx=1.0, rely=0.0, x=-60, y=48, anchor="ne")

        # Keyboard initialization
        self.keyboard = VirtualKeyboard(self, fg_color=("#E5E5E5", "#151515"), height=220)
        self.keyboard.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.keyboard.grid_remove()

        # Chart window
        self.extended_chart_view = ExtendedChart(self, self.font_text_semibold, self.font_text_reg_small, self.database_json)

        self.data_manager.read_logs()
        self.data_manager.read_ai_history()

        self.read_buffer()

        self.select_page("Home")

        lib.log("[UI] Tabbed interface initialized.")

    def init_fonts(self):
        """Font load."""
        fonts_dir = os.path.join(lib.UI_ELEMENTS_DIR, "fonts/Montserrat")
        
        font_files = {
            "Regular": "Montserrat-Regular.ttf",
            "Medium": "Montserrat-Medium.ttf",
            "SemiBold": "Montserrat-SemiBold.ttf",
            "Bold": "Montserrat-Bold.ttf"
        }
        
        for name, file_name in font_files.items():
            font_path = os.path.join(fonts_dir, file_name)
            if os.path.exists(font_path): ctk.FontManager.load_font(font_path)
            else: lib.log(f"[UI WARNING] Font file not found: {file_name}")

        # Styles
        self.font_logo = ctk.CTkFont(family=None, size=32, weight="bold")

        self.font_text_reg_small = ctk.CTkFont(family="Montserrat", size=14, weight="normal")
        self.font_text_reg = ctk.CTkFont(family="Montserrat", size=18, weight="normal")
        self.font_text_reg_big = ctk.CTkFont(family="Montserrat", size=26, weight="normal")

        self.font_text_med_small = ctk.CTkFont(family="Montserrat Medium", size=14, weight="normal")
        self.font_text_med = ctk.CTkFont(family="Montserrat Medium", size=18, weight="normal")
        self.font_text_med_big = ctk.CTkFont(family="Montserrat Medium", size=26, weight="normal")

        self.font_text_semibold = ctk.CTkFont(family="Montserrat SemiBold", size=18, weight="normal")
        self.font_text_semibold_big = ctk.CTkFont(family="Montserrat SemiBold", size=26, weight="normal")
        self.font_text_semibold_really_big = ctk.CTkFont(family="Montserrat SemiBold", size=36, weight="normal")
        self.font_text_semibold_enormous = ctk.CTkFont(family="Montserrat SemiBold", size=48, weight="bold")

        self.font_text_bold = ctk.CTkFont(family="Montserrat Bold", size=20, weight="normal")
        self.font_text_bold_big = ctk.CTkFont(family="Montserrat Bold", size=26, weight="normal")
        self.font_text_bold_really_big = ctk.CTkFont(family="Montserrat Bold", size=38, weight="bold")
        self.font_button = ctk.CTkFont(family="Montserrat", size=16, weight="normal")

    def init_sidebar(self):
        """Initialize left slidebar"""
        self.sidebar_frame = ctk.CTkFrame(self, corner_radius=0, width=200)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # Main logo
        logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="PBRmOS", 
            font=self.font_logo
        )
        logo_label.grid(row=0, column=0, padx=20, pady=30)

        # Tabs list
        tabs = [
            ("Home", "Home"),
            ("State", "Flora State"),
            ("Trends", "Trends"),
            ("Harvest", "Harvest"),
            ("Assistant", "Assistant"),
            ("Console", "Console"),
            ("Settings", "Settings")
        ]

        # Tab buttons
        for i, (page_name, button_text) in enumerate(tabs):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=button_text,
                corner_radius=8,
                height=40,
                border_spacing=10,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                anchor="w",
                font=self.font_button,
                command=lambda name=page_name: self.select_page(name)
            )
            btn.grid(row=i+1, column=0, padx=10, pady=5, sticky="ew")
            self.menu_buttons[page_name] = btn

    # --------------------------------- PAGES ---------------------------------
    def home_page(self, id):      
        home_page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.pages[id] = home_page
        
        home_page.grid_columnconfigure(0, weight=1)
        home_page.grid_rowconfigure(4, weight=1)

        # O. LOAD DATA
        curr_telemetry = self.data_manager.get_last_telemetry()
        curr_state = self.data_manager.get_last_state()
        culture_profile = self.data_manager.get_culture_profile()

        # A. HEADER ROW
        header_frame = ctk.CTkFrame(home_page, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(15, 25))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_header = ctk.CTkLabel(header_frame, text="Home", font=self.font_text_bold_really_big)
        lbl_header.grid(row=0, column=0, sticky="w")

        # B. FLORA INFO BLOCK
        flora_frame = ctk.CTkFrame(home_page, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        flora_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=15)
        
        flora_frame.grid_columnconfigure(0, weight=0)
        flora_frame.grid_columnconfigure(1, weight=1)
        flora_frame.grid_columnconfigure(2, weight=0)
        flora_frame.grid_rowconfigure(0, weight=1)

        # General flora state
        health_col = self.data_manager.get_health_color(self.culture_health)
        
        health_badge = ctk.CTkFrame(flora_frame, corner_radius=14, width=150, height=130, fg_color=("#EAEAEA", "#252525"), border_width=3, border_color=health_col)
        health_badge.grid(row=0, column=0, padx=25, pady=30, sticky="nsew")
        health_badge.grid_propagate(False)
        health_badge.grid_columnconfigure(0, weight=1)
        health_badge.grid_rowconfigure((0,1), weight=1)

        lbl_health_num = ctk.CTkLabel(health_badge, text=self.data_manager.get_health_val(self.culture_health), font=self.font_text_bold_really_big, text_color=health_col)
        lbl_health_num.grid(row=0, column=0, pady=(15,0), sticky="s")
        lbl_health_status = ctk.CTkLabel(health_badge, text=self.data_manager.get_health_text(self.culture_health), font=self.font_text_bold, text_color=health_col)
        lbl_health_status.grid(row=1, column=0, pady=(0,15), sticky="n")

        # Info container
        center_info_container = ctk.CTkFrame(flora_frame, fg_color="transparent")
        center_info_container.grid(row=0, column=1, padx=(10, 15), pady=20, sticky="ew")
        center_info_container.grid_columnconfigure(0, weight=1)
        center_info_container.grid_rowconfigure((0, 1), weight=1)

        # Culture name
        lbl_flora_name = ctk.CTkLabel(center_info_container, text=culture_profile["name"], font=self.font_text_semibold_really_big)
        lbl_flora_name.grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Culture profile
        status_lines_frame = ctk.CTkFrame(center_info_container, fg_color=("#EAEAEA", "#252525"), corner_radius=10)
        status_lines_frame.grid(row=1, column=0, sticky="ew")
        status_lines_frame.grid_columnconfigure(0, weight=1)

        lbl_mini_status = ctk.CTkLabel(status_lines_frame, text=f"> Appropriate temperature: {culture_profile["optimal_temp_range"][0]} - {culture_profile["optimal_temp_range"][1]} °C\n> Double period: {culture_profile["avg_double_period"]}h\n> Appropriate pH: {culture_profile["appropriate_ph"]}", font=self.font_text_reg_small, justify="left")
        lbl_mini_status.grid(row=0, column=0, padx=15, pady=12, sticky="w")

        # Parameter container
        right_sensors_container = ctk.CTkFrame(flora_frame, fg_color="transparent", border_width=2, border_color="#1F6AA5", corner_radius=12)
        right_sensors_container.grid(row=0, column=2, padx=(5, 25), pady=20, sticky="w")
        
        # Parameters
        mini_flask_1 = ctk.CTkFrame(right_sensors_container, width=60, height=100, fg_color=("#E0E0E0", "#2A2A2A"), corner_radius=8)
        mini_flask_1.grid(row=0, column=0, padx=10, pady=10)
        mini_flask_1.grid_propagate(False)
        mini_flask_1.grid_columnconfigure(0, weight=1)
        mini_flask_1.grid_rowconfigure(0, weight=1)
        lbl_mf1_val = ctk.CTkLabel(mini_flask_1, text=f"{curr_telemetry["concentration"]}\n%", font=self.font_text_bold, justify="center")
        lbl_mf1_val.grid(row=0, column=0)

        mini_flask_2 = ctk.CTkFrame(right_sensors_container, width=60, height=85, fg_color=("#E0E0E0", "#2A2A2A"), corner_radius=8)
        mini_flask_2.grid(row=0, column=1, padx=10, pady=10)
        mini_flask_2.grid_propagate(False)
        mini_flask_2.grid_columnconfigure(0, weight=1)
        mini_flask_2.grid_rowconfigure(0, weight=1)
        lbl_mf2_val = ctk.CTkLabel(mini_flask_2, text=f"{curr_telemetry["temp_in"]}\n°C", font=self.font_text_bold, justify="center")
        lbl_mf2_val.grid(row=0, column=0)

        # C. HARVEST BLOCK
        harvest_frame = ctk.CTkFrame(home_page, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        harvest_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=15)
        harvest_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Harvested total label
        harv_volume_frame = ctk.CTkFrame(harvest_frame, fg_color=("#EAEAEA", "#252525"), corner_radius=12, border_width=1, border_color=("#CCCCCC", "#333333"))
        harv_volume_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        harv_volume_frame.grid_columnconfigure(0, weight=1)
        harv_volume_frame.grid_rowconfigure((0, 1), weight=1)

        lbl_harv_vol_lbl = ctk.CTkLabel(harv_volume_frame, text="Harvested total:", font=self.font_text_bold)
        lbl_harv_vol_lbl.grid(row=0, column=0, padx=15, pady=(15, 2), sticky="s")

        lbl_harv_vol = ctk.CTkLabel(harv_volume_frame, text=f"{-1} L", font=self.font_text_bold_really_big, text_color="#1F6AA5")
        lbl_harv_vol.grid(row=1, column=0, padx=15, pady=(2, 15), sticky="n")

        # Flask indicator
        flasks_container = ctk.CTkFrame(harvest_frame, fg_color="transparent",
                                        border_width=2, border_color=self.data_manager.get_flask_state(curr_state["flasks"]["left"], curr_state["flasks"]["right"]), corner_radius=12)
        flasks_container.grid(row=0, column=1, padx=20, pady=15)
        
        # Flask symbols
        self.flask_1 = ctk.CTkLabel(flasks_container, width=70, text=" ", height=90, fg_color=self.data_manager.get_flask_color(curr_state["flasks"]["left"]), corner_radius=8)
        self.flask_1.grid(row=0, column=0, padx=12, pady=12)

        self.flask_2 = ctk.CTkLabel(flasks_container, width=70, text=" ", height=90, fg_color=self.data_manager.get_flask_color(curr_state["flasks"]["right"]), corner_radius=8)
        self.flask_2.grid(row=0, column=1, padx=12, pady=12)

        # Control button
        buttons_container = ctk.CTkFrame(harvest_frame, fg_color="transparent")
        buttons_container.grid(row=0, column=2, padx=20, pady=15, sticky="ew")
        buttons_container.grid_columnconfigure(0, weight=1)

        btn_add_water = ctk.CTkButton(buttons_container, text="Add water", font=self.font_text_bold, height=40, corner_radius=10, fg_color=("#D0D0D0", "#2D2D2D"), text_color=("black", "white"), command=self.on_add_water_click)
        btn_add_water.grid(row=0, column=0, pady=(0, 10), sticky="ew")

        btn_harvest_now = ctk.CTkButton(buttons_container, text="Harvest now", font=self.font_text_bold_big, height=40, corner_radius=10, fg_color="#1F6AA5", command=self.on_harvest_now_click)
        btn_harvest_now.grid(row=1, column=0, sticky="ew")

        # D. DAILY NOTIFICATION BLOCK 
        lbl_notif_title = ctk.CTkLabel(home_page, text="Daily Notification", font=self.font_text_med_big)
        lbl_notif_title.grid(row=3, column=0, sticky="w", padx=65, pady=(15, 5))

        self.notif_panel = ctk.CTkTextbox(home_page, font=self.font_text_med, corner_radius=16, border_width=1, border_color=("#CCCCCC", "#2B2B2B"), fg_color=("#FFFFFF", "#151515"))
        self.notif_panel.grid(row=4, column=0, sticky="nsew", padx=60, pady=(0, 20))

        self.notif_panel.configure(spacing1=8, spacing3=8)
        self.notif_panel.insert("0.0", f"{self.data_manager.get_daily_notif()}")
        self.notif_panel.configure(state="disabled")

    def stats_page(self, id):
        state_page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.pages[id] = state_page

        state_page.grid_columnconfigure(0, weight=1)

        # O. LOAD DATA
        curr_telemetry = self.data_manager.get_last_telemetry()
        curr_state = self.data_manager.get_last_state()
        culture_profile = self.data_manager.get_culture_profile()
        machine_cfg = self.data_manager.get_machine_configuration()

        # A. HEADER ROW [Header, Verdict]
        header_frame = ctk.CTkFrame(state_page, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_header = ctk.CTkLabel(header_frame, text="Flora state", font=self.font_text_bold_really_big)
        lbl_header.grid(row=0, column=0, sticky="w")

        # State Watcher Verdict Banner
        health_col = self.data_manager.get_health_color(self.culture_health)

        verdict_frame = ctk.CTkFrame(state_page, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=12, border_width=1, border_color=(health_col, health_col))
        verdict_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=10)
        verdict_frame.grid_columnconfigure(0, weight=1)

        self.lbl_verdict = ctk.CTkLabel(verdict_frame, text=f"State Watcher Verdict: {self.data_manager.get_health_val(self.culture_health)} - {self.data_manager.get_health_text(self.culture_health)}", font=self.font_text_bold_big, text_color=health_col)
        self.lbl_verdict.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        # B. MIDDLE GRID CONTAINER [Main parameters]
        top_cards_frame = ctk.CTkFrame(state_page, fg_color="transparent")
        top_cards_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=15)
        top_cards_frame.grid_columnconfigure(0, weight=1)
        top_cards_frame.grid_columnconfigure(1, weight=1)

        # = Flora Temperature =
        temp_card = ctk.CTkFrame(top_cards_frame, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        temp_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        temp_card.grid_columnconfigure(0, weight=1)

        thermometer_frame = ctk.CTkFrame(temp_card, fg_color="transparent")
        thermometer_frame.grid(row=0, column=0, padx=40, pady=(25, 10), sticky="ew")
        thermometer_frame.grid_columnconfigure(0, weight=1)

        self.temp_canvas = ctk.CTkCanvas(thermometer_frame, height=30, bg="#1E1E1E" if ctk.get_appearance_mode() == "Dark" else "#F5F5F5", highlightthickness=0)
        self.temp_canvas.grid(row=0, column=0, sticky="ew")

        self.temp_canvas.bind("<Configure>", lambda e: self.draw_thermometer(lib.ABS_MIN_TEMP, lib.ABS_MAX_TEMP, culture_profile["optimal_temp_range"][0], culture_profile["optimal_temp_range"][1], curr_telemetry["temp_in"]))

        # Temp info
        temp_info_frame = ctk.CTkFrame(temp_card, fg_color="transparent")
        temp_info_frame.grid(row=1, column=0, padx=40, pady=(0, 25), sticky="w")
       
        self.lbl_flora_temp = ctk.CTkLabel(temp_info_frame, text=f"Flora temperature:  {curr_telemetry["temp_in"]} °C", font=self.font_text_semibold)
        self.lbl_flora_temp.grid(row=0, column=0, sticky="w", pady=3)
        self.lbl_min_temp = ctk.CTkLabel(temp_info_frame, text=f"Minimal temperature:  {culture_profile["optimal_temp_range"][0]} °C", font=self.font_text_reg)
        self.lbl_min_temp.grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_max_temp = ctk.CTkLabel(temp_info_frame, text=f"Maximal temperature:  {culture_profile["optimal_temp_range"][1]} °C", font=self.font_text_reg)
        self.lbl_max_temp.grid(row=2, column=0, sticky="w", pady=2)

        # = Concentration & pH =
        conc_card = ctk.CTkFrame(top_cards_frame, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        conc_card.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
       
        conc_card.grid_columnconfigure((0, 1), weight=1)
        conc_card.grid_rowconfigure((0, 4), weight=1)

        # Concentration
        lbl_conc_title = ctk.CTkLabel(conc_card, text="Concentration", font=self.font_text_med_small, text_color="gray")
        lbl_conc_title.grid(row=1, column=0, pady=(0, 5))
       
        self.flask_conc_square = ctk.CTkFrame(conc_card, width=65, height=65, corner_radius=8, fg_color=("#E0E0E0", "#2A2A2A"), border_width=1, border_color="gray")
        self.flask_conc_square.grid(row=2, column=0, pady=5)
        self.flask_conc_square.grid_propagate(False)
       
        self.lbl_conc_val = ctk.CTkLabel(conc_card, text=f"{curr_telemetry["concentration"]}%", font=self.font_text_bold_big)
        self.lbl_conc_val.grid(row=3, column=0, pady=(5, 0))

        # pH
        lbl_ph_title = ctk.CTkLabel(conc_card, text="Solution pH", font=self.font_text_med_small, text_color="gray")
        lbl_ph_title.grid(row=1, column=1, pady=(0, 5))
       
        self.ph_rect = ctk.CTkFrame(conc_card, width=35, height=65, corner_radius=6, fg_color=("#E0E0E0", "#2A2A2A"), border_width=1, border_color="gray")
        self.ph_rect.grid(row=2, column=1, pady=5)
        self.ph_rect.grid_propagate(False)
       
        self.lbl_ph_val = ctk.CTkLabel(conc_card, text=f"{curr_telemetry["ph"]}", font=self.font_text_bold_big)
        self.lbl_ph_val.grid(row=3, column=1, pady=(5, 0))

        # C. LOWER CARDS ROW [Volume, Flasks/Heater, Lights Configuration]
        bottom_cards_frame = ctk.CTkFrame(state_page, fg_color="transparent")
        bottom_cards_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=10)
        bottom_cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # = Volume =
        vol_card = ctk.CTkFrame(bottom_cards_frame, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        vol_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        vol_card.grid_columnconfigure(0, weight=1)
       
        lbl_vol_title = ctk.CTkLabel(vol_card, text="Volume", font=self.font_text_semibold_big)
        lbl_vol_title.grid(row=0, column=0, pady=(10, 5))

        vol_tank_col = self.data_manager.get_vol_color(curr_state["volume"]["low"], curr_state["volume"]["high"])
       
        self.vol_tank_shape = ctk.CTkFrame(vol_card, width=90, height=110, corner_radius=10, fg_color=("#E0E0E0", "#2A2A2A"),
                                           border_width=2, border_color=vol_tank_col)
        self.vol_tank_shape.grid(row=1, column=0, pady=8)
       
        self.lbl_vol_status = ctk.CTkLabel(vol_card, text=self.data_manager.get_vol_text(curr_state["volume"]["low"], curr_state["volume"]["high"]),
                                           font=self.font_text_med_big, text_color=vol_tank_col)
        self.lbl_vol_status.grid(row=2, column=0, pady=(5, 15))

        # = Flasks & Hardware State =
        hw_card = ctk.CTkFrame(bottom_cards_frame, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        hw_card.grid(row=0, column=1, sticky="nsew", padx=8)
        hw_card.grid_columnconfigure(0, weight=1)

        flasks_sub = ctk.CTkFrame(hw_card, fg_color="transparent")
        flasks_sub.grid(row=0, column=0, pady=(12, 2))
       
        lbl_flasks_title = ctk.CTkLabel(flasks_sub, text="Flasks", font=self.font_text_semibold_big)
        lbl_flasks_title.pack(pady=(0, 5))
       
        flasks_container = ctk.CTkFrame(flasks_sub, fg_color="transparent")
        flasks_container.pack()
       
        # Left flask
        self.flask_1 = ctk.CTkLabel(flasks_container, width=64, height=80, text=" ", fg_color=("#E0E0E0", "#2A2A2A"), corner_radius=8)
        self.flask_1.grid(row=0, column=0, padx=10, pady=(5, 3))
       
        self.lbl_weight_x = ctk.CTkLabel(flasks_container, text=f"{curr_state["flasks"]["grams_left"]} g", font=self.font_text_med_small)
        self.lbl_weight_x.grid(row=1, column=0, pady=(0, 5))

        # Right flask
        self.flask_2 = ctk.CTkLabel(flasks_container, width=64, height=80, text=" ", fg_color=("#E0E0E0", "#2A2A2A"), corner_radius=8)
        self.flask_2.grid(row=0, column=1, padx=10, pady=(5, 3))
       
        self.lbl_weight_y = ctk.CTkLabel(flasks_container, text=f"{curr_state["flasks"]["grams_right"]} g", font=self.font_text_med_small)
        self.lbl_weight_y.grid(row=1, column=1, pady=(0, 4))

        sys_status_frame = ctk.CTkFrame(hw_card, fg_color="transparent")
        sys_status_frame.grid(row=1, column=0, padx=20, pady=(4, 12), sticky="w")
       
        # Heater
        heater_line = ctk.CTkFrame(sys_status_frame, fg_color="transparent")
        heater_line.grid(row=0, column=0, sticky="w", pady=1)
       
        lbl_heater_prefix = ctk.CTkLabel(heater_line, text="Heater: ", font=self.font_text_med)
        lbl_heater_prefix.grid(row=0, column=0, sticky="w")
       
        self.lbl_heater_state = ctk.CTkLabel(heater_line, text=f"{self.data_manager.strBooleanFormat(curr_state["state"]["H"], "ON", "OFF")}", font=self.font_text_bold, text_color="#1F6AA5")
        self.lbl_heater_state.grid(row=0, column=1, sticky="w")

        # Carbonizer
        carbon_line = ctk.CTkFrame(sys_status_frame, fg_color="transparent")
        carbon_line.grid(row=1, column=0, sticky="w", pady=1)
       
        lbl_carbon_prefix = ctk.CTkLabel(carbon_line, text="Carbonizer: ", font=self.font_text_med)
        lbl_carbon_prefix.grid(row=0, column=0, sticky="w")
       
        self.lbl_carbon_state = ctk.CTkLabel(carbon_line, text=f"{self.data_manager.strBooleanFormat(curr_state["state"]["C"], "Work", "Rest")}", font=self.font_text_bold, text_color="#1F6AA5")
        self.lbl_carbon_state.grid(row=0, column=1, sticky="w")

        # = Lights =
        light_card = ctk.CTkFrame(bottom_cards_frame, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        light_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        light_card.grid_columnconfigure((0, 1), weight=1)
        light_card.grid_rowconfigure((0, 2), weight=1)

        # Light status
        light_lines_frame = ctk.CTkFrame(light_card, fg_color="transparent")
        light_lines_frame.grid(row=1, column=0, padx=(30, 10), sticky="w")
       
        self.lbl_light1 = ctk.CTkLabel(light_lines_frame, text=f"Light 1: {self.data_manager.percOrOffFormat(curr_state["state"]["L0"])}", font=self.font_text_reg_big)
        self.lbl_light1.grid(row=0, column=0, sticky="w", pady=8)
        self.lbl_light2 = ctk.CTkLabel(light_lines_frame, text=f"Light 2: {self.data_manager.percOrOffFormat(curr_state["state"]["L1"])}", font=self.font_text_reg_big)
        self.lbl_light2.grid(row=1, column=0, sticky="w", pady=8)
        self.lbl_light3 = ctk.CTkLabel(light_lines_frame, text=f"Light 3: {self.data_manager.percOrOffFormat(curr_state["state"]["L2"])}", font=self.font_text_reg_big)
        self.lbl_light3.grid(row=2, column=0, sticky="w", pady=8)

        # Light graphic
        circle_bg = ("#E0E0E0", "#252525")
       
        graphic_circle_radius = 210
        graphic_circle = ctk.CTkFrame(light_card, width=graphic_circle_radius, height=graphic_circle_radius,
                                      corner_radius=105, fg_color=circle_bg, border_width=2, border_color=("#CCCCCC", "#444444"))
        graphic_circle.grid(row=1, column=1, padx=(5, 20))
        graphic_circle.grid_propagate(False)
        graphic_circle.grid_columnconfigure(0, weight=1)
        graphic_circle.grid_rowconfigure(0, weight=1)

        # Canvas
        self.reactor_canvas = ctk.CTkCanvas(
            graphic_circle,
            width=graphic_circle_radius / math.sqrt(2) - 10,
            height=graphic_circle_radius / math.sqrt(2) - 10,
            bg=circle_bg[0] if ctk.get_appearance_mode() == "Light" else circle_bg[1],
            highlightthickness=0
        )
        self.reactor_canvas.grid(row=0, column=0, padx=3, pady=3)
        self.draw_reactor_schematic(curr_state["state"]["L0"], curr_state["state"]["L1"], curr_state["state"]["L2"])

        # D. BOTTOM PERIODS CONFIGURATION
        periods_frame = ctk.CTkFrame(state_page, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        periods_frame.grid(row=4, column=0, sticky="ew", padx=30, pady=15)
        
        periods_frame.grid_columnconfigure(0, weight=1)
        periods_frame.grid_columnconfigure(1, weight=0)
        periods_frame.grid_columnconfigure(2, weight=1)
        periods_frame.grid_rowconfigure(0, weight=1)

        # = Light Period =
        light_period_frame = ctk.CTkFrame(periods_frame, fg_color="transparent")
        light_period_frame.grid(row=0, column=0, padx=20, pady=25, sticky="nsew")
        
        light_period_frame.grid_columnconfigure(0, weight=1)
        light_period_frame.grid_rowconfigure(0, weight=0)
        light_period_frame.grid_rowconfigure(1, weight=1)

        lbl_lp_title = ctk.CTkLabel(light_period_frame, text="Light period", font=self.font_text_bold_big, anchor="center")
        lbl_lp_title.grid(row=0, column=0, sticky="n", pady=(0, 20))

        lp_center_wrapper = ctk.CTkFrame(light_period_frame, fg_color="transparent")
        lp_center_wrapper.grid(row=1, column=0, sticky="n")

        lp_content_left = ctk.CTkFrame(lp_center_wrapper, fg_color="transparent")
        lp_content_left.grid(row=0, column=0, padx=(0, 30))

        lp_inputs_frame = ctk.CTkFrame(lp_content_left, fg_color="transparent")
        lp_inputs_frame.grid(row=0, column=0, sticky="w")

        # Inputfield variables
        self.light_on_var = customtkinter.StringVar(value=str(machine_cfg["machine_config"]["light_day_period_h"]))
        self.light_off_var = customtkinter.StringVar(value=str((24 - machine_cfg["machine_config"]["light_day_period_h"])))
       
        # Light ON (Left)
        self.ent_light_on = ValidatedNumberEntry(
            lp_inputs_frame,
            min_val=0, 
            max_val=24,
            allow_float=False,
            default_val=12,
            textvariable=self.light_on_var,
            width=55,
            height=32,
            font=self.font_text_bold_big,
            justify="center"
        )
        self.ent_light_on.grid(row=0, column=0)
        self.ent_light_on.bind("<Button-1>", self.global_keyboard_handler)
       
        # Divider (Middle)
        lbl_h_slash = ctk.CTkLabel(lp_inputs_frame, text=" h. / ", font=self.font_text_bold_big)
        lbl_h_slash.grid(row=0, column=1)
       
        # Light OFF (Right)
        self.ent_light_off = ValidatedNumberEntry(
            lp_inputs_frame,
            min_val=0, 
            max_val=24,
            allow_float=False,
            default_val=12,
            textvariable=self.light_off_var,
            width=55,
            height=32,
            font=self.font_text_bold_big,
            justify="center"
        )
        self.ent_light_off.grid(row=0, column=2)
        self.ent_light_off.bind("<Button-1>", self.global_keyboard_handler)
        
        # End Label
        lbl_h_end = ctk.CTkLabel(lp_inputs_frame, text=" h.", font=self.font_text_bold_big)
        lbl_h_end.grid(row=0, column=3)

        self.light_on_var.trace_add("write", self._sync_light_hour_on)
        self.light_off_var.trace_add("write", self._sync_light_hour_off)

        # Save Light config
        btn_save_light = ctk.CTkButton(lp_content_left, text="Save", font=self.font_button, width=120, height=36, corner_radius=8, fg_color=("#D0D0D0", "#2D2D2D"),
                                       text_color=("black", "white"), command=lambda: self.save_light_period())
        btn_save_light.grid(row=1, column=0, sticky="w", pady=(15, 0))

        self.light_dial_bg = "#E0E0E0" if ctk.get_appearance_mode() == "Light" else "#252525"

        self.light_dial_canvas = ctk.CTkCanvas(lp_center_wrapper, width=150, height=150, bg=self.light_dial_bg, highlightthickness=0)
        self.light_dial_canvas.grid(row=0, column=1)

        # Diagramm
        self.draw_time_dial(self.light_dial_canvas, machine_cfg["machine_config"]["light_day_period_h"], (24 - machine_cfg["machine_config"]["light_day_period_h"]),
                            self.light_dial_bg, 150)

        # = Separator =
        separator = ctk.CTkFrame(periods_frame, width=2, fg_color=("#DBDBDB", "#2B2B2B"))
        separator.grid(row=0, column=1, sticky="ns", pady=20)

        # = Carbonizer Period =
        carb_period_frame = ctk.CTkFrame(periods_frame, fg_color="transparent")
        carb_period_frame.grid(row=0, column=2, padx=20, pady=20, sticky="nsew")
        
        carb_period_frame.grid_columnconfigure(0, weight=1)
        carb_period_frame.grid_rowconfigure(0, weight=0)
        carb_period_frame.grid_rowconfigure(1, weight=1)

        lbl_cp_title = ctk.CTkLabel(carb_period_frame, text="Carbonizer period", font=self.font_text_bold_big, anchor="center")
        lbl_cp_title.grid(row=0, column=0, sticky="n", pady=(0, 20))

        carb_center_wrapper = ctk.CTkFrame(carb_period_frame, fg_color="transparent")
        carb_center_wrapper.grid(row=1, column=0, sticky="n")

        carb_content_left = ctk.CTkFrame(carb_center_wrapper, fg_color="transparent")
        carb_content_left.grid(row=0, column=0, padx=(0, 30), sticky="ns")

        carb_inputs_grid = ctk.CTkFrame(carb_content_left, fg_color="transparent")
        carb_inputs_grid.grid(row=0, column=0, sticky="w")

        # Inputs
        lbl_work = ctk.CTkLabel(carb_inputs_grid, text="Work: ", font=self.font_text_bold)
        lbl_work.grid(row=0, column=0, sticky="w", pady=6)
        self.ent_carb_work = ValidatedNumberEntry(
            carb_inputs_grid,
            min_val=1, 
            max_val=60,
            allow_float=False,
            default_val=10,
            width=60,
            height=32,
            font=self.font_text_bold,
            justify="center"
        )
        self.ent_carb_work.insert(0, machine_cfg["machine_config"]["compressor_active_min"])
        self.ent_carb_work.grid(row=0, column=1, pady=6, padx=5)
        self.ent_carb_work.bind("<Button-1>", self.global_keyboard_handler)

        lbl_work_min = ctk.CTkLabel(carb_inputs_grid, text=" min", font=self.font_text_med)
        lbl_work_min.grid(row=0, column=2, sticky="w", pady=6)

        lbl_rest = ctk.CTkLabel(carb_inputs_grid, text="Rest: ", font=self.font_text_bold)
        lbl_rest.grid(row=1, column=0, sticky="w", pady=6)
        self.ent_carb_rest = ValidatedNumberEntry(
            carb_inputs_grid, 
            min_val=1, 
            max_val=60,
            allow_float=False,
            default_val=2,
            width=60, 
            height=32, 
            font=self.font_text_bold, 
            justify="center"
        )
        self.ent_carb_rest.insert(0, machine_cfg["machine_config"]["compressor_rest_min"])
        self.ent_carb_rest.grid(row=1, column=1, pady=6, padx=5)
        self.ent_carb_rest.bind("<Button-1>", self.global_keyboard_handler)

        lbl_rest_min = ctk.CTkLabel(carb_inputs_grid, text=" min", font=self.font_text_med)
        lbl_rest_min.grid(row=1, column=2, sticky="w", pady=6)

        btn_save_carb = ctk.CTkButton(carb_content_left, text="Save", font=self.font_button, width=120, height=36, corner_radius=8, fg_color=("#D0D0D0", "#2D2D2D"),
                                      text_color=("black", "white"), command=lambda: self.save_carb_shedule())
        btn_save_carb.grid(row=1, column=0, sticky="w", pady=(15, 0))

        # Cycles
        cycles_badge = ctk.CTkFrame(carb_center_wrapper, fg_color=("#EAEAEA", "#252525"), corner_radius=12, border_width=1, border_color=("#CCCCCC", "#333333"))
        cycles_badge.grid(row=0, column=1, sticky="ns", ipadx=15)
        cycles_badge.grid_columnconfigure(0, weight=1)
        cycles_badge.grid_rowconfigure((0, 1), weight=1)

        lbl_cycles_title = ctk.CTkLabel(cycles_badge, text="Cycles / Day", font=self.font_text_reg_small, text_color="gray")
        lbl_cycles_title.grid(row=0, column=0, padx=10, pady=(15, 0), sticky="s")
       
        self.lbl_cycles_val = ctk.CTkLabel(cycles_badge, text=f"{24 * (60 / (machine_cfg["machine_config"]["compressor_active_min"] + machine_cfg["machine_config"]["compressor_rest_min"])):.2f}",
                                           font=self.font_text_bold_big, text_color="#1F6AA5")
        self.lbl_cycles_val.grid(row=1, column=0, padx=10, pady=(0, 18), sticky="n")

    def trends_page(self, id):
        trends_page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.pages[id] = trends_page

        trends_page.grid_columnconfigure(0, weight=1)

        # A. HEADER ROW
        header_frame = ctk.CTkFrame(trends_page, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_header = ctk.CTkLabel(header_frame, text="Environment Trends", font=self.font_text_bold_really_big)
        lbl_header.grid(row=0, column=0, sticky="w")

        # B. TOP METRICS GRID
        metrics_grid = ctk.CTkFrame(trends_page, fg_color="transparent")
        metrics_grid.grid(row=1, column=0, sticky="ew", padx=30, pady=15)
        
        for i in range(4): metrics_grid.grid_columnconfigure(i, weight=1)
        
        self.metrics_labels = {}

        # Top metrics data array
        stats_data = [
            # Day
            {"title": "Avg External Temp", "val": f"{self.data_manager.get_avg_telemetry('temp_out', 1):.2f}°C", "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Day", "col": 0, "row": 0, "key": "avg_out_1"},
            {"title": "Avg Internal Temp", "val": f"{self.data_manager.get_avg_telemetry('temp_in', 1):.2f}°C", "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Day", "col": 1, "row": 0, "key": "avg_in_1"},
            {"title": "Avg Solution pH",   "val": f"{self.data_manager.get_avg_telemetry('ph', 1):.1f}",    "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Day", "col": 2, "row": 0, "key": "ph_1"},
            {"title": "Delta Concentration","val": f"{self.data_manager.get_value_mark(self.data_manager.get_delta_telemetry('concentration', 1))}%",  "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Day", "col": 3, "row": 0, "key": "delta_conc_1"},
            # Week
            {"title": "Avg External Temp", "val": f"{self.data_manager.get_avg_telemetry('temp_out', 7):.2f}°C", "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Week", "col": 0, "row": 1, "key": "avg_out_7"},
            {"title": "Avg Internal Temp", "val": f"{self.data_manager.get_avg_telemetry('temp_in', 7):.2f}°C", "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Week", "col": 1, "row": 1, "key": "avg_in_7"},
            {"title": "Avg Solution pH",   "val": f"{self.data_manager.get_avg_telemetry('ph', 7):.1f}",    "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Week", "col": 2, "row": 1, "key": "ph_7"},
            {"title": "Delta Concentration","val": f"{self.data_manager.get_value_mark(self.data_manager.get_delta_telemetry('concentration', 7))}%",  "font_v": self.font_text_bold_big, "font_t": self.font_text_med_small, "font_p": self.font_text_reg_small, "period": "Week", "col": 3, "row": 1, "key": "delta_conc_7"},
        ]

        for stat in stats_data:
            card = ctk.CTkFrame(metrics_grid, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=12, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
            card.grid(row=stat["row"], column=stat["col"], padx=6, pady=6, sticky="nsew")
            card.grid_columnconfigure(0, weight=1)
            # Period
            lbl_p = ctk.CTkLabel(card, text=stat["period"].upper(), font=stat["font_p"], text_color="#1F6AA5" if stat["period"] == "Day" else "gray")
            lbl_p.grid(row=0, column=0, padx=12, pady=(8, 0), sticky="w")
            # Title
            lbl_t = ctk.CTkLabel(card, text=stat["title"], font=stat["font_t"], text_color="gray")
            lbl_t.grid(row=1, column=0, padx=12, pady=(2, 2), sticky="w")
            # Value
            lbl_v = ctk.CTkLabel(card, text=stat["val"], font=stat["font_v"])
            lbl_v.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="w")
            # Save
            self.metrics_labels[stat["key"]] = lbl_v

        # C. DATA CHARTS
        self.charts_frame = ctk.CTkFrame(trends_page, fg_color="transparent")
        self.charts_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=10)
        self.charts_frame.grid_columnconfigure(0, weight=1)

        self.refresh_ui_plots()

    def harvest_page(self, id):
        harvest_page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        harvest_page.grid_columnconfigure(0, weight=1)

        # --- A. HEADER ROW ---
        header_frame = ctk.CTkFrame(harvest_page, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_header = ctk.CTkLabel(header_frame, text="Harvest Menu", font=self.font_text_bold_really_big)
        lbl_header.grid(row=0, column=0, sticky="w")

        # --- B. CALENDAR SECTION ---
        cal_card = ctk.CTkFrame(harvest_page, corner_radius=15)
        cal_card.grid(row=1, column=0, sticky="ew", padx=30, pady=10)
        cal_card.grid_columnconfigure(0, weight=1)

        self.draw_calendar(cal_card)

        # --- C. STATS ROW ---
        stats_frame = ctk.CTkFrame(harvest_page, fg_color="transparent")
        stats_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=10)
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        amount_card = ctk.CTkFrame(stats_frame, corner_radius=15)
        amount_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        lbl_amount = ctk.CTkLabel(amount_card, text="Harvest Share", font=self.font_text_bold)
        lbl_amount.pack(pady=(15, 0))
        
        self.harvest_slider = ctk.CTkSlider(amount_card, from_=0, to=100, number_of_steps=20)
        self.harvest_slider.pack(padx=20, pady=10, fill="x")
        
        self.lbl_share_val = ctk.CTkLabel(amount_card, text="25%", font=self.font_text_bold_big, text_color="#1F6AA5")
        self.lbl_share_val.pack(pady=(0, 15))

        total_card = ctk.CTkFrame(stats_frame, corner_radius=15)
        total_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        lbl_total_title = ctk.CTkLabel(total_card, text="TOTAL HARVESTED", font=self.font_text_bold)
        lbl_total_title.pack(pady=(15, 5))
        
        lbl_total_val = ctk.CTkLabel(total_card, text="12.4 L", font=self.font_text_bold_really_big, text_color="green")
        lbl_total_val.pack(pady=5)
        
        lbl_count = ctk.CTkLabel(total_card, text="Collected 42 times", font=self.font_text_reg_small, text_color="gray")
        lbl_count.pack(pady=(0, 15))

        # --- D. SETTINGS SECTION ---
        settings_card = ctk.CTkFrame(harvest_page, corner_radius=15)
        settings_card.grid(row=3, column=0, sticky="ew", padx=30, pady=10)
        
        # Power Pump
        pwr_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        pwr_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(pwr_frame, text="H-Pump Power:", font=self.font_text_bold).pack(side="left")
        ctk.CTkSegmentedButton(pwr_frame, values=["20%", "50%", "80%", "100%"]).pack(side="right")

        # Add water after
        water_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        water_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(water_frame, text="Auto-refill water after harvest:", font=self.font_text_bold).pack(side="left")
        ctk.CTkCheckBox(water_frame, text="").pack(side="right")

        # --- SAVE BTN ---
        btn_save = ctk.CTkButton(harvest_page, text="START MANUAL HARVEST", height=50, 
                                 fg_color="#1F6AA5", font=self.font_text_bold, command=self.on_harvest_now_click)
        btn_save.grid(row=4, column=0, padx=30, pady=30, sticky="ew")

        self.pages[id] = harvest_page

    def ai_page(self, id):
        ai_page = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        ai_page.grid_columnconfigure(0, weight=1)
        ai_page.grid_rowconfigure(1, weight=1)

        # A. HEADER ROW
        header_frame = ctk.CTkFrame(ai_page, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_header = ctk.CTkLabel(header_frame, text="AI Assistant", font=self.font_text_bold_really_big)
        lbl_header.grid(row=0, column=0, sticky="w")

        # B. CHAT HISTORY AREA
        self.chat_canvas = ctk.CTkScrollableFrame(ai_page, fg_color="#1E1E1E", corner_radius=8)
        self.chat_canvas.grid(row=1, column=0, sticky="nsew", padx=10)
        self.chat_canvas.columnconfigure(0, weight=1)

        # C. INPUT AREA
        input_card = ctk.CTkFrame(ai_page, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=20, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        input_card.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        input_card.grid_columnconfigure(0, weight=1)

        self.ai_entry = ctk.CTkEntry(
            input_card, 
            placeholder_text="Ask RAIS something...", 
            font=self.font_text_reg_small,
            height=45,
            border_width=0,
            fg_color="transparent"
        )
        self.ai_entry.grid(row=0, column=0, sticky="ew", padx=(20, 10), pady=5)
        self.ai_entry.bind("<Button-1>", self.global_keyboard_handler)
        self.ai_entry.bind("<Return>", lambda e: self.send_ai_message())

        btn_send = ctk.CTkButton(
            input_card, 
            text="▲", 
            font=self.font_text_semibold,
            width=40, height=40,
            corner_radius=15,
            fg_color="#1F6AA5",
            hover_color="#144871",
            command=self.send_ai_message
        )
        btn_send.grid(row=0, column=1, padx=10, pady=5)

        self.pages[id] = ai_page

    def console_page(self, id):
        console_page = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        console_page.grid_columnconfigure(0, weight=1)
        console_page.grid_rowconfigure(1, weight=1)

        # A. HEADER ROW
        header_frame = ctk.CTkFrame(console_page, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_header = ctk.CTkLabel(header_frame, text="Console", font=self.font_text_bold_really_big)
        lbl_header.grid(row=0, column=0, sticky="w")

        # B. MAIN LOG CONSOLE
        terminal_card = ctk.CTkFrame(console_page, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        terminal_card.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        terminal_card.grid_columnconfigure(0, weight=1)
        terminal_card.grid_rowconfigure(0, weight=1)

        self.txt_console = ctk.CTkTextbox(
            terminal_card, 
            font=ctk.CTkFont(family="Courier New", size=12) if hasattr(self, "font_text_reg_small") else ("monospace", 12),
            fg_color=("#EAEAEA", "#1A1A1A"), 
            text_color=("#222222", "#00FF66"),
            border_width=1,
            border_color=("#DBDBDB", "#2B2B2B")
        )
        self.txt_console.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        self.txt_console.configure(state="disabled")

        # C. CONSOLE INPUTFIELD
        input_wrapper = ctk.CTkFrame(terminal_card, fg_color="transparent")
        input_wrapper.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        input_wrapper.grid_columnconfigure(0, weight=1)

        self.ent_command = ctk.CTkEntry(
            input_wrapper, 
            placeholder_text="Enter system command...", 
            font=self.font_text_reg_small,
            fg_color=("#FFFFFF", "#151515"),
            border_color=("#DBDBDB", "#2B2B2B")
        )
        self.ent_command.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.ent_command.bind("<Return>", lambda event: self.execute_console_command())

        btn_send = ctk.CTkButton(
            input_wrapper, 
            text="EXECUTE", 
            font=self.font_text_semibold,
            width=100,
            fg_color="#1F6AA5",
            hover_color="#144871",
            command=self.execute_console_command
        )
        btn_send.grid(row=0, column=1, sticky="e")

        self.pages[id] = console_page

    def settings_page(self, id):
        settings_page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        settings_page.grid_columnconfigure(0, weight=1)
        settings_page.grid_rowconfigure(1, weight=1)

        # A. HEADER ROW
        header_frame = ctk.CTkFrame(settings_page, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_header = ctk.CTkLabel(header_frame, text="Settings", font=self.font_text_bold_really_big)
        lbl_header.grid(row=0, column=0, sticky="w")

        #

        self.pages[id] = settings_page

    # -------------------------------------------------------------------------

    # ------------------------------- PAGE METHODS -------------------------------
    
    def init_pages(self):
        self.home_page("Home")
        self.stats_page("State")
        self.trends_page("Trends")
        self.harvest_page("Harvest")
        self.ai_page("Assistant")
        self.console_page("Console")
        self.settings_page("Settings")

    def select_page(self, page_name):
        if self.current_page_name == page_name: return
        # Reset active tab button
        if self.current_page_name in self.menu_buttons:
            self.menu_buttons[self.current_page_name].configure(fg_color="transparent")
        # Remove old page
        if self.current_page_name in self.pages:
            self.pages[self.current_page_name].grid_forget()
        # Button highlighting
        self.menu_buttons[page_name].configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        # Show new page
        self.pages[page_name].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        # Update UI is memory
        self.current_page_name = page_name
        lib.log(f"[UI] Switched to tab: {page_name}")

    # -----------------------------------------------------------------------

    # ------------------------------- CHARTS & STATISTICS METHODS -------------------------------

    def refresh_ui_plots(self):
        if hasattr(self, "metrics_labels"):
            try:
                self.metrics_labels["avg_out_1"].configure(text=f"{self.data_manager.get_avg_telemetry('temp_out', 1):.2f}°C")
                self.metrics_labels["avg_in_1"].configure(text=f"{self.data_manager.get_avg_telemetry('temp_in', 1):.2f}°C")
                self.metrics_labels["ph_1"].configure(text=f"{self.data_manager.get_avg_telemetry('ph', 1):.1f}")
                self.metrics_labels["delta_conc_1"].configure(text=f"{self.data_manager.get_value_mark(self.data_manager.get_delta_telemetry('concentration', 1))}%")
                
                self.metrics_labels["avg_out_7"].configure(text=f"{self.data_manager.get_avg_telemetry('temp_out', 7):.2f}°C")
                self.metrics_labels["avg_in_7"].configure(text=f"{self.data_manager.get_avg_telemetry('temp_in', 7):.2f}°C")
                self.metrics_labels["ph_7"].configure(text=f"{self.data_manager.get_avg_telemetry('ph', 7):.1f}")
                self.metrics_labels["delta_conc_7"].configure(text=f"{self.data_manager.get_value_mark(self.data_manager.get_delta_telemetry('concentration', 7))}%")
            except Exception as e: lib.log(f"[UI] Metrics refresh error: {e}")

        self.redraw_all_metrics()

        self.after(5000, self.refresh_ui_plots)

    def on_charts_frame_resize(self, event):
        if hasattr(self, "_resize_after_id"): self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(100, self.redraw_all_metrics)

    def redraw_all_metrics(self):
        for child in self.charts_frame.winfo_children(): child.destroy()

        self.chart_temp_ex = self.draw_trend_chart("temp_out", self.charts_frame, row_idx=0, title="External Temperature Trend (°C)")
        self.chart_temp_in = self.draw_trend_chart("temp_in", self.charts_frame, row_idx=1, title="Internal Temperature Trend (°C)")
        self.chart_ph = self.draw_trend_chart("ph", self.charts_frame, row_idx=2, title="Solution pH Level Stability")
        self.chart_concentration = self.draw_trend_chart("concentration", self.charts_frame, row_idx=3, title="Biomass Concentration Growth Curve (%)")

        self.bind_click_to_widget(self.chart_temp_ex, "temp_out", "External Temperature Trend (°C)")
        self.bind_click_to_widget(self.chart_temp_in, "temp_in", "Internal Temperature Trend (°C)")
        self.bind_click_to_widget(self.chart_ph, "ph", "Solution pH Level Stability")
        self.bind_click_to_widget(self.chart_concentration, "concentration", "Biomass Concentration Growth Curve (%)")

    def bind_click_to_widget(self, widget, data_key, title):
        if widget is None: return
        
        widget.bind("<Button-1>", lambda event: self.on_trend_card_click(data_key, title))
        for child in widget.winfo_children(): child.bind("<Button-1>", lambda event: self.on_trend_card_click(data_key, title))

    def on_trend_card_click(self, data_key, title):
        self.extended_chart_view.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="nsew")
        self.extended_chart_view.set_data_key(data_key, title)

    # -----------------------------------------------------------------------

    # ------------------------------- SPECIAL METHODS -------------------------------

    def read_buffer(self):
        has_log_updates = False

        while not self.cmd_buffer.empty():
            try:
                command_type, payload = self.cmd_buffer.get_nowait()
                
                match command_type:
                    case "LOGS":
                        self.draw_log(payload)
                        has_log_updates = True
                        
                    case "AI_CHAT":
                        self.render_ai_history(payload)
                        lib.log("[UI] AI Chat loaded.")

                    case "STATEWATCHER_RESULT":
                        if type(payload) == float:
                            self.culture_health = payload
                            lib.log(f"[UI] Culture health updated: {payload}%.")
                        else: lib.log(f"[UI] Culture health update error. Payload is NaN.")

                    case _: lib.log(f"[UI] Unknown GUI command: {command_type}")

                self.cmd_buffer.task_done()
                
            except queue.Empty: break

        if has_log_updates: self.txt_console.see("end")

        self.after(100, self.read_buffer)

    def execute_console_command(self):
        # Extract user input strike (like "COMMAND X1 X2 X3")
        command_line = self.ent_command.get().strip()
        if not command_line: return

        # Split into command and arguments string
        parts = command_line.split(maxsplit=1)
        command = parts[0].upper()
        payload = parts[1].strip() if len(parts) > 1 else ""

        # Write into the file
        lib.log(f"> {command_line}")
        # Put command into execution list
        self.sys_cmd_buff.put((command, payload))

        # Clear input field
        self.ent_command.delete(0, "end")

    def render_ai_history(self, history_list):
        # Clear current view
        for child in self.chat_canvas.winfo_children(): child.destroy()
        # Read list
        try:
            for msg in history_list:
                author = msg.get("author", "").upper()
                content = msg.get("content", "")
                timestamp = msg.get("time", "")
                if content:
                    if author == "USER": self.draw_chat_bubble("USER", content, timestamp)
                    elif author == "ASSISTANT": self.draw_chat_bubble("RAIS", content, timestamp)
        except Exception as e: lib.log(f"[UI] AI History failed: {e}")

    def send_ai_message(self):
        query = self.ai_entry.get().strip()
        if not query: return
        
        # Update UI locally (immediate feedback)
        now = time.strftime("%d.%m.%Y-%H:%M")
        self.draw_chat_bubble("USER", query, now)
        self.ai_entry.delete(0, "end")
        
        # Put command
        self.ai_cmd_buff.put(("AI_REQUEST", query))

    # -----------------------------------------------------------------------

    # ------------------------------- CALENDAR METHODS -------------------------------

    def change_month(self, container_frame, direction):
        self.current_calendar_view_month += direction
        if self.current_calendar_view_month > 12:
            self.current_calendar_view_month = 1
            self.current_calendar_view_year += 1
        elif self.current_calendar_view_month < 1:
            self.current_calendar_view_month = 12
            self.current_calendar_view_year -= 1
            
        self.draw_calendar(container_frame)

    # -----------------------------------------------------------------------

    # ------------------------------- KEYBOARD METHODS -------------------------------

    def global_keyboard_handler(self, event_or_widget):
        if hasattr(event_or_widget, "widget"): widget = event_or_widget.widget
        else: widget = event_or_widget

        widget_type = widget.__class__.__name__.lower()
        
        if "entry" in widget_type or "textbox" in widget_type:
            self.keyboard.set_target(widget)
            self.keyboard.grid()
            # Find scrollable parent
            print("[UI] Searching for the parent...")
            scroll_parent = self.find_scrollable_parent(widget)
            if scroll_parent: self.scroll_to_widget(scroll_parent, widget)

    def find_scrollable_parent(self, widget):
        current = widget.master
        highest_scroll_parent = None

        while current:
            # Find CTkScrollableFrame
            if current.__class__.__name__ == "CTkScrollableFrame":
                highest_scroll_parent = current
                break
            current = current.master

        print(f"[UI] Parent found: {highest_scroll_parent}")
        return highest_scroll_parent   

    def scroll_to_widget(self, scroll_frame, target_widget):
        try:
            scroll_frame.update_idletasks()
            target_widget.update_idletasks()

            # Check scrollability
            if not hasattr(scroll_frame, "_scrollbar"):
                print("[UI] Scrollbar not found on this frame.")
                return

            scrollbar = scroll_frame._scrollbar

            # Input position
            widget_relative_y = 0
            current = target_widget
            while current and current != scroll_frame:
                widget_relative_y += current.winfo_y()
                current = current.master

            # Visible frame height
            frame_height = scroll_frame.winfo_height()

            # Get scroll value
            scroll_top, scroll_bottom = scrollbar.get()
            visible_ratio = scroll_bottom - scroll_top

            # Count full content size
            if visible_ratio > 0: total_height = frame_height / visible_ratio
            else: total_height = frame_height

            if total_height <= frame_height:
                print("[UI] Everything fits, no scroll needed.")
                return

            # Calculate target point
            target_y_pixels = widget_relative_y - (frame_height / 3)
            
            fraction = target_y_pixels / total_height
            fraction = 9 * (max(0.0, min(1.0, fraction)))

            # Move scrollbar
            if scrollbar.cget("command"):
                scrollbar.cget("command")("moveto", fraction)
                print(f"[UI] Auto-scrolled via Scrollbar command to fraction: {fraction:.2f}")
            else: print("[UI] Scrollbar command is empty.")

        except Exception as e: print(f"[UI] Scroll failed critically: {e}")

    # -----------------------------------------------------------------------

    # ------------------------------- DRAWERS -------------------------------

    def draw_thermometer(self, min, max, lowest, highest, curr):
        self.temp_canvas.delete("all")
       
        w = self.temp_canvas.winfo_width()
        h = self.temp_canvas.winfo_height()
        if w < 10: return

        bar_y1, bar_y2 = 12, 22
        r_offset = 6
       
        def t_to_x(temp):
            prop = (temp - min) / (max - min)
            return r_offset + prop * (w - 2 * r_offset)

        x_1 = t_to_x(min)
        x_2 = t_to_x(lowest)
        x_3 = t_to_x(highest)
        x_4 = t_to_x(max)

        # Zones
        self.temp_canvas.create_rectangle(x_1, bar_y1, x_2, bar_y2, fill="#0059FF", outline="")
        self.temp_canvas.create_rectangle(x_2, bar_y1, x_3, bar_y2, fill="#6CB96C", outline="")
        self.temp_canvas.create_rectangle(x_3, bar_y1, x_4, bar_y2, fill="#8B0000", outline="")

        curr_x = t_to_x(curr)
       
        self.temp_canvas.create_line(curr_x, 2, curr_x, 28, fill="#1F6AA5", width=3)
        self.temp_canvas.create_rectangle(curr_x - 4, 2, curr_x + 4, 8, fill="#1F6AA5", outline="")

    def draw_reactor_schematic(self, l1, l2, l3):
        self.reactor_canvas.delete("all")
       
        # Canvas size
        canvas_width = self.reactor_canvas.winfo_width()
        canvas_height = self.reactor_canvas.winfo_height()
       
        # Secure dimensions
        if canvas_width < 10:
            canvas_width = int(210 / math.sqrt(2))
            canvas_height = int(210 / math.sqrt(2))

        stroke_color = "#1E1E1E" if ctk.get_appearance_mode() == "Light" else "#FFFFFF"
        body_fill = "#D5D5D5" if ctk.get_appearance_mode() == "Light" else "#2D2D2D"
       
        margin_x = int(canvas_width * 0.15)
        margin_y = int(canvas_height * 0.1)
       
        x1, y1 = margin_x, margin_y
        x2, y2 = canvas_width - margin_x, canvas_height - margin_y

        inner_w = x2 - x1
        inner_h = y2 - y1
       
        top_thickness = int(inner_h * 0.14)
        right_thickness = int(inner_w * 0.14)
        bottom_thickness = top_thickness * 2.5

        # Body struct
        reactor_points = [
            x1, y1,
            x2, y1,
            x2, y2,
            x1, y2,
            x1, y2 - bottom_thickness,
            x2 - right_thickness, y2 - bottom_thickness,
            x2 - right_thickness, y1 + top_thickness,
            x1, y1 + top_thickness
        ]
        self.reactor_canvas.create_polygon(reactor_points, fill=body_fill, outline=stroke_color, width=2)

        # Color generation
        def get_glow_color(val):
            val_norm = val / 100.0
            if val_norm <= 0.05:
                return "#444444" if ctk.get_appearance_mode() == "Dark" else "#999999"
            brightness = int(130 + (val_norm * 125))
            if ctk.get_appearance_mode() == "Dark":
                return f"#00{int(brightness*0.85):02x}{brightness:02x}"
            else:
                return f"#0000{brightness:02x}"


        lamp_w = int(inner_w * 0.55)  
        lamp_h = int(inner_h * 0.08)

        l1_color = get_glow_color(l1)
        lx1_1 = x1 + 8
        ly1_1 = y2 - bottom_thickness - lamp_h
        lx2_1 = lx1_1 + lamp_w
        ly2_1 = y2 - bottom_thickness
        self.reactor_canvas.create_rectangle(lx1_1, ly1_1, lx2_1, ly2_1, fill=l1_color, outline=stroke_color, width=1)
        self.reactor_canvas.create_text((lx1_1 + lx2_1)/2, (ly1_1 + ly2_1)/2, text="1", fill=stroke_color, font=("Montserrat", 8, "bold"))

        l2_color = get_glow_color(l2)
        lx1_2 = x2 - 1.7 * right_thickness
        ly1_2 = y1 + top_thickness + 8
        lx2_2 = x2 - 1.7 * right_thickness + lamp_h
        ly2_2 = y2 - bottom_thickness - 8
        self.reactor_canvas.create_rectangle(lx1_2, ly1_2, lx2_2, ly2_2, fill=l2_color, outline=stroke_color, width=1)
        self.reactor_canvas.create_text((lx1_2 + lx2_2)/2, (ly1_2 + ly2_2)/2, text="2", fill=stroke_color, font=("Montserrat", 8, "bold"))

        l3_color = get_glow_color(l3)
        lx1_3 = x1 + 8
        ly1_3 = y1 + top_thickness
        lx2_3 = lx1_3 + lamp_w
        ly2_3 = y1 + top_thickness + lamp_h
        self.reactor_canvas.create_rectangle(lx1_3, ly1_3, lx2_3, ly2_3, fill=l3_color, outline=stroke_color, width=1)
        self.reactor_canvas.create_text((lx1_3 + lx2_3)/2, (ly1_3 + ly2_3)/2, text="3", fill=stroke_color, font=("Montserrat", 8, "bold"))
            
    def draw_time_dial(self, canvas, hours_on, hours_off, dial_bg, size):   
        canvas.delete("all")
        
        canvas.configure(width=size, height=size)
        
        stroke = "#1E1E1E" if ctk.get_appearance_mode() == "Light" else "#FFFFFF"
        total = hours_on + hours_off if (hours_on + hours_off) > 0 else 24
        extent_on = (hours_on / total) * 360
        
        pad = 2
        x1, y1 = pad, pad
        x2, y2 = size - pad, size - pad
        
        # Sector "Active"
        canvas.create_arc(x1, y1, x2, y2, start=90, extent=-extent_on, fill="#1F6AA5", outline=stroke, width=1.5)
        # Sector "Inactive"
        canvas.create_arc(x1, y1, x2, y2, start=90 - extent_on, extent=-(360 - extent_on), fill="#333333", outline=stroke, width=1.5)

        inner_pad = size * 0.3
        ix1, iy1 = inner_pad, inner_pad
        ix2, iy2 = size - inner_pad, size - inner_pad
        canvas.create_oval(ix1, iy1, ix2, iy2, fill=dial_bg, outline=stroke, width=1.5)
        
        # Text
        center = size / 2
        r_text = (size / 2 + (size / 2 - inner_pad)) / 2 
        sector_font = ("Montserrat", int(size * 0.08), "bold")

        angle_active_mid = 90 - (extent_on / 2)
        angle_inactive_mid = (90 - extent_on) - ((360 - extent_on) / 2)

        if hours_on > 0:
            rad_active = math.radians(angle_active_mid)
            tx_active = center + r_text * math.cos(rad_active)
            ty_active = center - r_text * math.sin(rad_active)
            canvas.create_text(tx_active, ty_active, text=f"{hours_on}h", fill=stroke, font=sector_font)

        if hours_off > 0:
            rad_inactive = math.radians(angle_inactive_mid)
            tx_inactive = center + r_text * math.cos(rad_inactive)
            ty_inactive = center - r_text * math.sin(rad_inactive)
            text_color_inactive = "#FFFFFF" if ctk.get_appearance_mode() == "Dark" else "#E0E0E0"
            canvas.create_text(tx_inactive, ty_inactive, text=f"{hours_off}h", fill=text_color_inactive, font=sector_font)

        canvas.create_text(center, center, text="Day", fill=stroke, font=("Montserrat", int(size * 0.1), "bold"))

    def draw_trend_chart(self, data_key, parent_frame, row_idx, title):
        chart_card = ctk.CTkFrame(parent_frame, fg_color=("#F5F5F5", "#1E1E1E"), corner_radius=16, border_width=1, border_color=("#DBDBDB", "#2B2B2B"))
        chart_card.grid(row=row_idx, column=0, sticky="ew", pady=10)
        chart_card.grid_columnconfigure(0, weight=1)

        lbl_ct = ctk.CTkLabel(chart_card, text=title, font=self.font_text_semibold, text_color=("#111111", "#EEEEEE"))
        lbl_ct.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        canvas_widget = ctk.CTkCanvas(chart_card, height=200, bg="#1E1E1E" if ctk.get_appearance_mode() == "Dark" else "#F5F5F5", highlightthickness=0)
        canvas_widget.grid(row=1, column=0, padx=20, pady=(5, 15), sticky="ew")

        # Load telemetry data
        raw_data = self.database_json.get(data_key, [])
        points = raw_data[-10:]

        if not points:
            canvas_widget.create_text(
                250, 100, text="NO DATA AVAILABLE", 
                font=self.font_text_med_small, fill="gray"
            )
            return chart_card

        canvas_widget.update_idletasks()
        W = canvas_widget.winfo_width()
        H = canvas_widget.winfo_height()

        if W <= 1 or H <= 1:
            W = 500  
            H = 200  

        pad_y_top = 30
        pad_y_bottom = 55
        pad_x_left = 70  
        pad_x_right = 35 

        # Calculate math limits
        values = [float(pt[1]) for pt in points]
        raw_min = min(values)
        raw_max = max(values)

        if raw_min == raw_max:
            raw_min -= 1.0
            raw_max += 1.0

        # Align edges
        import math
        min_val = math.floor(raw_min)
        max_val = math.ceil(raw_max)

        if max_val - min_val < 4: max_val = min_val + 4

        # Draw grid lines
        grid_lines = 5  
        for i in range(grid_lines):
            f = i / (grid_lines - 1)
            y_pos = pad_y_top + f * (H - pad_y_top - pad_y_bottom)
            cur_scale_val = max_val - f * (max_val - min_val)

            canvas_widget.create_line(
                pad_x_left, y_pos, W - pad_x_right, y_pos,
                fill="#333333" if ctk.get_appearance_mode() == "Dark" else "#E0E0E0",
                dash=(4, 4)
            )

            # Data formatting
            if data_key == "concentration": text_label = f"{int(cur_scale_val)}%"
            elif data_key in ["temp_out", "temp_in"]: text_label = f"{int(cur_scale_val)}°"
            else: text_label = f"{cur_scale_val:.1f}"

            canvas_widget.create_text(
                pad_x_left - 25, y_pos,
                text=text_label, font=self.font_text_reg_small,
                fill="gray", anchor="e"
            )

        # Plot axis coordinates
        num_points = len(points)
        x_step = (W - pad_x_left - pad_x_right) / 9 

        coords = []
        for idx, (timestamp, val) in enumerate(points):
            x = pad_x_left + idx * x_step
            y = pad_y_top + (1.0 - (float(val) - min_val) / (max_val - min_val)) * (H - pad_y_top - pad_y_bottom)
            coords.append((x, y, timestamp, float(val)))

        # Layer 1: Render geometry paths
        for idx in range(num_points - 1):
            x1, y1, _, _ = coords[idx]
            x2, y2, _, _ = coords[idx + 1]

            canvas_widget.create_line(
                x1, y1, x2, y2,
                fill="#1F6AA5", width=3,
                smooth=True
            )
            canvas_widget.create_oval(
                x1 - 3, y1 - 3, x1 + 3, y1 + 3,
                fill="#1F6AA5" if ctk.get_appearance_mode() == "Dark" else "white",
                outline="#1F6AA5", width=1
            )
        
        if num_points > 0:
            x_last, y_last, _, _ = coords[-1]
            canvas_widget.create_oval(
                x_last - 3, y_last - 3, x_last + 3, y_last + 3,
                fill="#1F6AA5" if ctk.get_appearance_mode() == "Dark" else "white",
                outline="#1F6AA5", width=1
            )

        # Overlay dynamic labels & text ticks
        for idx in range(num_points):
            x, y, timestamp, val = coords[idx]

            raw_date, raw_time = timestamp.split("-") if "-" in timestamp else ("", timestamp)
            if len(raw_date) == 10: display_date = f"{raw_date[0:6]}{raw_date[8:10]}"
            else: display_date = raw_date

            display_time = ":".join(raw_time.split(":")[:2]) if ":" in raw_time else raw_time

            canvas_widget.create_text(
                x, H - 32,
                text=display_time, font=self.font_text_reg_small,
                fill="gray", anchor="n"
            )
            canvas_widget.create_text(
                x, H - 16,
                text=display_date, font=self.font_text_reg_small,
                fill="gray", anchor="n"
            )

            # Node values
            if data_key == "concentration":  node_label = f"{val:.1f}%"
            elif data_key in ["temp_out", "temp_in"]: node_label = f"{val:.2f}°"
            else: node_label = f"{val:.1f}"

            # Calculate adaptive local offset trends
            is_local_min = False
            prev_y = coords[idx - 1][1] if idx > 0 else None
            next_y = coords[idx + 1][1] if idx < num_points - 1 else None

            if prev_y is not None and next_y is not None:
                if y > prev_y and y > next_y: is_local_min = True
            elif prev_y is not None and y > prev_y: is_local_min = True
            elif next_y is not None and y > next_y: is_local_min = True

            y_offset = 12 if is_local_min else -12
            text_anchor = "n" if is_local_min else "s"

            canvas_widget.create_text(
                x, y + y_offset,
                text=node_label, font=self.font_text_reg_small,
                fill="#1F6AA5" if ctk.get_appearance_mode() == "Dark" else "#111111",
                anchor=text_anchor
            )

        return chart_card
    
    def draw_calendar(self, container_frame):
        for widget in container_frame.winfo_children(): widget.destroy()

        # Get data
        logs_dict = self.data_manager.get_harvest_logs_dict()
        today_date = datetime.now().date()

        # --- CALENDAR HEADER ---
        header_nav = ctk.CTkFrame(container_frame, fg_color="transparent")
        header_nav.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 15))
        header_nav.grid_columnconfigure(1, weight=1)

        # Months
        month_names = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        month_title = f"{month_names[self.current_calendar_view_month - 1]} {self.current_calendar_view_year}"

        btn_prev = ctk.CTkButton(header_nav, text="◀", width=40, height=35, font=self.font_text_med_small,
                                  command=lambda: self.change_month(container_frame, -1))
        btn_prev.grid(row=0, column=0, sticky="w")

        lbl_month = ctk.CTkLabel(header_nav, text=month_title, font=self.font_text_bold)
        lbl_month.grid(row=0, column=1)

        btn_next = ctk.CTkButton(header_nav, text="▶", width=40, height=35, font=self.font_text_med_small,
                                  command=lambda: self.change_month(container_frame, 1))
        btn_next.grid(row=0, column=2, sticky="e")

        # --- WEEK DAYS ---
        days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for col, day_name in enumerate(days_of_week):
            lbl = ctk.CTkLabel(container_frame, text=day_name, font=self.font_text_med_small, text_color="gray")
            lbl.grid(row=1, column=col, pady=(0, 10), sticky="nsew")

        # --- CALENDAR GRID ---
        first_weekday, num_days = calendar.monthrange(self.current_calendar_view_year, self.current_calendar_view_month)
        
        for i in range(7): container_frame.grid_columnconfigure(i, weight=1, uniform="equal_cols")
        for r in range(2, 8): container_frame.grid_rowconfigure(r, weight=1, uniform="equal_rows")

        # Previous days
        prev_year = self.current_calendar_view_year if self.current_calendar_view_month > 1 else self.current_calendar_view_year - 1
        prev_month = self.current_calendar_view_month - 1 if self.current_calendar_view_month > 1 else 12
        _, prev_num_days = calendar.monthrange(prev_year, prev_month)
        
        start_day_of_prev = prev_num_days - first_weekday + 1
        
        grid_row = 2
        for col in range(first_weekday):
            day_num = start_day_of_prev + col
            btn_dummy = ctk.CTkButton(container_frame, text=str(day_num), font=self.font_text_reg_small,
                                       width=55, height=55, corner_radius=8,
                                       fg_color="transparent", text_color="gray", state="disabled")
            btn_dummy.grid(row=grid_row, column=col, padx=4, pady=4, sticky="nsew")

        for day in range(1, num_days + 1):
            grid_col = (first_weekday + day - 1) % 7
            
            cell_date = datetime(self.current_calendar_view_year, self.current_calendar_view_month, day).date()
            date_key = cell_date.strftime("%d.%m.%Y")
            
            has_harvest = date_key in logs_dict
            
            if cell_date > today_date:
                # Future
                fg_color = ("#E0E0E0", "#2B2B2B")
                hover_color = ("#D0D0D0", "#383838")
                text_color = "gray"
                click_command = lambda d=date_key: self.on_future_calendar_day_click(d)
            else:
                # Past & Present
                click_command = lambda d=date_key, data=logs_dict.get(date_key): self.on_past_calendar_day_click(d, data)
                
                if has_harvest:
                    fg_color = "#2E7D32"  # Harvested (Green)
                    hover_color = "#1B5E20"
                    text_color = "white"
                elif cell_date == today_date:
                    fg_color = "#1F6AA5"  # Taday's date (Blue)
                    hover_color = "#144970"
                    text_color = "white"
                else:
                    fg_color = ("#F5F5F5", "#212121")  # Past day (Gray)
                    hover_color = ("#EAEAEA", "#2A2A2A")
                    text_color = ("black", "white")

            btn_day = ctk.CTkButton(
                container_frame, 
                text=str(day),
                font=self.font_text_reg_small,
                width=55,
                height=55,
                corner_radius=8,
                fg_color=fg_color,
                hover_color=hover_color,
                text_color=text_color,
                command=click_command
            )
            btn_day.grid(row=grid_row, column=grid_col, padx=4, pady=4, sticky="nsew")
            
            if grid_col == 6 and day < num_days:
                grid_row += 1

        total_slots_used = first_weekday + num_days
        next_month_days_to_draw = (7 - (total_slots_used % 7)) % 7
        if total_slots_used <= 35: next_month_days_to_draw += 7
            
        for next_day in range(1, next_month_days_to_draw + 1):
            grid_col = (total_slots_used + next_month_days_to_draw - next_month_days_to_draw + next_day - 1) % 7
            btn_dummy = ctk.CTkButton(container_frame, text=str(next_day), font=self.font_text_reg_small,
                                       width=55, height=55, corner_radius=8,
                                       fg_color="transparent", text_color="gray", state="disabled")
            btn_dummy.grid(row=grid_row, column=grid_col, padx=4, pady=4, sticky="nsew")
            if grid_col == 6 and next_day < next_month_days_to_draw:
                grid_row += 1

    def draw_chat_bubble(self, sender, text, timestamp):
        # Determine alignment and colors
        is_user = (sender.lower() == "user")
        side = "e" if is_user else "w"
        bubble_color = ("#DBDBDB", "#2B2B2B") if not is_user else ("#1F6AA5", "#144871")
        text_color = ("#111111", "#EEEEEE") if not is_user else "white"

        # Bubble Container
        bubble_frame = ctk.CTkFrame(self.chat_canvas, fg_color="transparent")
        bubble_frame.grid(column=0, sticky=side, padx=20, pady=5)
        # Content Card
        card = ctk.CTkFrame(bubble_frame, fg_color=bubble_color, corner_radius=15)
        card.pack(side="top", anchor=side)
        # Name and Time tag
        tag_text = f"{sender.upper()}  {timestamp}"
        lbl_tag = ctk.CTkLabel(card, text=tag_text, font=ctk.CTkFont(size=9, weight="bold"), text_color="gray" if not is_user else "#B0C4DE")
        lbl_tag.pack(padx=15, pady=(8, 0), anchor="w")
        # Message Text
        lbl_msg = ctk.CTkLabel(card, text=text, font=self.font_text_reg_small, text_color=text_color, wraplength=400, justify="left")
        lbl_msg.pack(padx=15, pady=(2, 10), anchor="w")

        # Scroll canvas
        try:
            self.chat_canvas.update_idletasks()
   
            if hasattr(self.chat_canvas, "_parent_canvas"): self.chat_canvas._parent_canvas.yview_moveto(1.0)
            elif hasattr(self.chat_canvas, "_canvas"): self.chat_canvas._canvas.yview_moveto(1.0)
            else: self.chat_canvas.yview("moveto", 1.0)
                
        except Exception as e: lib.log(f"[UI Scroll Error] Ошибка автоскролла перехвачена: {e}")

    def draw_log(self, log):
        self.txt_console.configure(state="normal")
        self.txt_console.insert("end", str(log) + "\n")
        self.txt_console.configure(state="disabled")

    # -----------------------------------------------------------------------

    # ------------------------------- EVENT FUNCTIONS -------------------------------

    def _sync_light_hour_on(self, *args):
        if self._updating_light: return

        raw_val = self.light_on_var.get()
        if raw_val == "" or raw_val == "-": return
        try:
            on_hours = int(raw_val)
            if 0 <= on_hours <= 24: 
                off_hours = 24 - on_hours
                
                self._updating_light = True
                self.light_off_var.set(str(off_hours))
                self._updating_light = False

        except ValueError: self._updating_light = False

    def _sync_light_hour_off(self, *args):
        if self._updating_light: return
        
        raw_val = self.light_off_var.get()
        if raw_val == "" or raw_val == "-": return
        try:
            off_hours = int(raw_val)
            if 0 <= off_hours <= 24: 
                on_hours = 24 - off_hours
                
                self._updating_light = True
                self.light_on_var.set(str(on_hours))
                self._updating_light = False

        except ValueError: self._updating_light = False

    def save_light_period(self):
        hours_on = self.ent_light_on.get_val()
        # Save
        self.data_manager.save_light_config(hours_on)
        # Display
        self.draw_time_dial(self.light_dial_canvas, hours_on, (24 - hours_on), self.light_dial_bg, 150)
        lib.log(f"[UI] Light period saved: {hours_on} hours ON")
        
    def save_carb_shedule(self):
        minutes_active = self.ent_carb_work.get_val()
        minutes_rest = self.ent_carb_rest.get_val()
        # Save
        self.data_manager.save_compressor_config(minutes_active, minutes_rest)
        # Display
        self.lbl_cycles_val.configure(text=f"{24 * (60 / (minutes_active + minutes_rest)):.2f}")
        lib.log(f"[UI] Carbonizer schedule saved: ON for {minutes_active} min, REST for {minutes_rest} min")  

    def on_harvest_now_click(self):
        self.sys_cmd_buff.put(("HARVEST_REQUEST", 1))
        lib.log("[UI] 'Harvest Now' action triggered.")

    def on_add_water_click(self):
        self.sys_cmd_buff.put(("ADD_WATER", 1))
        lib.log("[UI] 'Add Water' action triggered.")

    def on_past_calendar_day_click(self, date_str, harvest_info):
        if harvest_info:
            lib.log(f"[UI] Past day clicked: {date_str} -> Harvested: {harvest_info['ml']}ml, Turbidity: {harvest_info['turbidity']}")
        else: 
            lib.log(f"[UI] Past day clicked: {date_str} -> No harvest logs.")

    def on_future_calendar_day_click(self, date_str):
        lib.log(f"[UI] Future day clicked: {date_str} -> Planning functionality coming soon.")

    def on_closing(self):
        self.destroy()
        sys.exit(0)
 
    # -------------------------------------------------------------------------