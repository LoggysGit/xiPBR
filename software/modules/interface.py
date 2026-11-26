""" UI Interface module """

import math
import tkinter.font as tkfont
from datetime import datetime
from queue import Empty, Queue
from typing import Any

import customtkinter as ctk

# Redmi Note 8 landscape is 2340x1080 = 13:6; 1024x472 keeps that ratio.
WINDOW_W, WINDOW_H = 1024, 472
GAP = 10
CYCLE_SIZE = 132
RING_W = 12

# Palette (spirulina green on deep blue-green)
C_BG = "#0D1412"
C_SIDEBAR = "#0A100E"
C_CARD = "#15201C"
C_CARD_ALT = "#1B2A25"
C_BORDER = "#26372F"
C_ACCENT = "#2EE6B0"
C_ACCENT_DIM = "#1D9C78"
C_TEXT = "#E7F1ED"
C_MUTED = "#8AA198"
C_DAY = "#F2B84B"
C_NIGHT = "#5E6EDB"
C_MOON = "#C7CEF5"

R_HERO, R_CARD, R_TILE = 22, 16, 12

SANS_FONTS = ("Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", "Noto Sans", "DejaVu Sans", "Arial")
MONO_FONTS = ("JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New")


def _pick_family(candidates: tuple[str, ...]) -> str:
    """ First installed font from the list (needs an existing Tk root) """
    installed = set(tkfont.families())
    for name in candidates:
        if name in installed:
            return name
    return candidates[-1]


def _draw_sun(canvas: ctk.CTkCanvas, x: float, y: float, color: str) -> None:
    canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="")
    for i in range(8):
        a = math.radians(i * 45)
        canvas.create_line(
            x + 7 * math.cos(a), y + 7 * math.sin(a),
            x + 10 * math.cos(a), y + 10 * math.sin(a),
            fill=color, width=2, capstyle="round",
        )


def _draw_moon(canvas: ctk.CTkCanvas, x: float, y: float, color: str) -> None:
    canvas.create_oval(x - 7, y - 7, x + 7, y + 7, fill=color, outline="")
    canvas.create_oval(x - 3, y - 8, x + 9, y + 4, fill=C_CARD, outline="")  # carve the crescent


class App(ctk.CTk):
    """ UI App """

    # incoming data key -> label ref on homePage (values are raw, units are static labels)
    HOME_TEXT_FIELDS = {
        "well_being": "well_being_val",
        "days_until_harvest": "days_val",
        "culture_name": "culture_val",
        "target_temp": "target_temp_val",
        "target_ph": "target_ph_val",
        "temp": "temp_val",
        "ph": "ph_val",
        "water_level": "water_val",
        "b_d": "bd_val",
        "b_h": "bh_val",
        "lu": "lu_val",
        "ls": "ls_val",
        "ll": "ll_val",
    }

    def __init__(self, system_queue: Queue, ui_queue: Queue):
        """ Class init """
        ctk.set_appearance_mode("dark")
        super().__init__()

        self.system_queue = system_queue
        self.ui_queue = ui_queue
        self.gui_command_buffer: list[dict[str, Any]] = []

        self.title("xiPBR Mk I")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(WINDOW_W, WINDOW_H)
        self.configure(fg_color=C_BG)

        self._sans = _pick_family(SANS_FONTS)
        self._mono = _pick_family(MONO_FONTS)
        self._fonts: dict[tuple, ctk.CTkFont] = {}

        self._pages: dict[str, Any] = {
            "home": self.homePage,
            "telemetry": self.telemetryPage,
            "console": self.consolePage,
            "settings": self.settingsPage,
        }
        self._active_page: str = "home"
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._ui_refs: dict[str, Any] = {}
        self._home_cache: dict[str, Any] = {}   # last known home data, survives page switches

        self._build_layout()
        self.router("home")
        self._poll_commands()

    # === HELPERS === #
    def _font(self, size: int, weight: str = "normal", mono: bool = False,
              italic: bool = False) -> ctk.CTkFont:
        key = (size, weight, mono, italic)
        if key not in self._fonts:
            self._fonts[key] = ctk.CTkFont(
                family=self._mono if mono else self._sans, size=size, weight=weight,
                slant="italic" if italic else "roman",
            )
        return self._fonts[key]

    @staticmethod
    def _card(parent: Any, radius: int = R_CARD, fg: str = C_CARD) -> ctk.CTkFrame:
        return ctk.CTkFrame(parent, corner_radius=radius, fg_color=fg,
                            border_width=1, border_color=C_BORDER)

    def _metric_row(self, parent: Any, label: str, ref: str, default: str,
                    unit: str = "", size: int = 14, inline: bool = False) -> ctk.CTkFrame:
        """ 'label ........ value unit' (or 'label value unit' when inline) """
        row = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(row, text=label, font=self._font(size - 1), text_color=C_MUTED).pack(side="left")
        value = ctk.CTkLabel(row, text=default, font=self._font(size, "bold"), text_color=C_TEXT)
        unit_lbl = ctk.CTkLabel(row, text=unit, font=self._font(size - 1), text_color=C_MUTED)
        if inline:
            value.pack(side="left", padx=(6, 0))
            if unit:
                unit_lbl.pack(side="left", padx=(2, 0))
        else:
            if unit:
                unit_lbl.pack(side="right")
            value.pack(side="right", padx=(0, 3 if unit else 0))
        self._ui_refs[ref] = value
        return row

    def _tile(self, parent: Any, caption: str, ref: str, default: str, unit: str) -> ctk.CTkFrame:
        tile = self._card(parent, radius=R_TILE, fg=C_CARD_ALT)
        tile.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tile, text=caption, font=self._font(10), text_color=C_MUTED).grid(
            row=0, column=0, sticky="w", padx=12, pady=(8, 0))
        line = ctk.CTkFrame(tile, fg_color="transparent")
        line.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
        value = ctk.CTkLabel(line, text=default, font=self._font(22, "bold"), text_color=C_TEXT)
        value.pack(side="left")
        ctk.CTkLabel(line, text=unit, font=self._font(12), text_color=C_MUTED).pack(
            side="left", padx=(3, 0), pady=(6, 0))
        self._ui_refs[ref] = value
        return tile

    # === LAYOUT & APP === #
    def _build_layout(self) -> None:
        """ Build sidebar & main container """
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=64, corner_radius=0, fg_color=C_SIDEBAR)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(3, weight=1)   # spacer: settings sits at the bottom

        nav_items = [
            ("home", "◎", 0),
            ("telemetry", "≡", 1),
            ("console", ">_", 2),
            ("settings", "⚙", 4),
        ]
        for page_key, label, row in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=label, width=44, height=44, corner_radius=12,
                font=self._font(18, "bold"), fg_color="transparent", hover_color=C_CARD,
                text_color=C_MUTED, command=lambda p=page_key: self.router(p),
            )
            btn.grid(row=row, column=0, pady=(14, 4) if row == 0 else (4, 14 if row == 4 else 4))
            self._nav_buttons[page_key] = btn

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(GAP, 12), pady=12)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

    def router(self, page_name: str | None = None) -> None:
        """ Pages router """
        target = page_name or self._active_page
        if target not in self._pages:
            return

        self._active_page = target
        self._ui_refs.clear()

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        for key, btn in self._nav_buttons.items():
            active = key == target
            btn.configure(
                fg_color=C_CARD_ALT if active else "transparent",
                text_color=C_ACCENT if active else C_MUTED,
                border_width=1 if active else 0,
                border_color=C_ACCENT_DIM,
            )

        page_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_container.grid(row=0, column=0, sticky="nsew")
        self._pages[target](page_container)

    # === QUEUE COMMAND EXECUTION === #
    def _poll_commands(self) -> None:
        """ Command buffer listener """
        while self.gui_command_buffer:
            cmd = self.gui_command_buffer.pop(0)
            self._handle_command(cmd)

        while True:
            try:
                msg = self.ui_queue.get_nowait()
            except Empty:
                break
            if isinstance(msg, dict):
                self._handle_command(msg)

        self._refresh_clock()
        self.after(150, self._poll_commands)

    def _handle_command(self, cmd: dict[str, Any]) -> None:
        """ Dispatch incoming commands """
        action = cmd.get("action")
        if action == "navigate" and isinstance(cmd.get("page"), str):
            self.router(cmd["page"])
        elif action == "update_home" and isinstance(cmd.get("data"), dict):
            self._apply_home_data(cmd["data"])

    # === ADDITIONAL PAGE FUNCTIONS === #
    # Home #
    def _apply_home_data(self, data: dict[str, Any]) -> None:
        """ Store incoming home data and render it if homePage is mounted.

        Values are raw (no units): temp=24.5, b_d=63, days_until_harvest=12.
        Optional extras: user_name, target_temp, target_ph, wifi_level (0-3),
        day_fraction (0-1, light part of the cycle), cycle_pos (0-1, current moment).
        """
        self._home_cache.update(data)
        if self._active_page != "home" or not self._ui_refs:
            return

        for key, ref in self.HOME_TEXT_FIELDS.items():
            if key in self._home_cache and ref in self._ui_refs:
                self._ui_refs[ref].configure(text=str(self._home_cache[key]))

        if "user_name" in self._home_cache and "greeting_val" in self._ui_refs:
            self._ui_refs["greeting_val"].configure(text=f"Hello, {self._home_cache['user_name']}!")

        if not data or data.keys() & {"day_fraction", "cycle_pos"}:
            self._draw_cycle()
        if not data or "wifi_level" in data:
            self._draw_wifi()

    def _refresh_clock(self) -> None:
        """ Keep hh:mm dd.mm.yyyy fresh on homePage """
        clock_lbl = self._ui_refs.get("clock_lbl")
        if clock_lbl is None or not clock_lbl.winfo_exists():
            return
        text = datetime.now().strftime("%H:%M  %d.%m.%Y")
        if clock_lbl.cget("text") != text:
            clock_lbl.configure(text=text)

    def _draw_wifi(self) -> None:
        canvas = self._ui_refs.get("wifi_canvas")
        if canvas is None:
            return
        level = self._home_cache.get("wifi_level")
        level = level if isinstance(level, int) else 0
        canvas.delete("all")
        cx, cy = 13, 16
        for i, r in enumerate((5, 9, 13), start=1):
            canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r, start=45, extent=90, style="arc",
                outline=C_ACCENT if level >= i else C_BORDER, width=2,
            )
        canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2,
                           fill=C_ACCENT if level >= 1 else C_BORDER, outline="")

    def _draw_cycle(self) -> None:
        """ Day/night ring: amber = light, indigo = dark, white dot = now """
        canvas = self._ui_refs.get("cycle_canvas")
        if canvas is None:
            return
        try:
            day = float(self._home_cache.get("day_fraction", 0.6))
        except (TypeError, ValueError):
            day = 0.6
        day = min(max(day, 0.05), 0.95)

        center = CYCLE_SIZE / 2
        ring_r = center - 14
        box = (center - ring_r, center - ring_r, center + ring_r, center + ring_r)

        def polar(angle_deg: float, radius: float) -> tuple[float, float]:
            a = math.radians(angle_deg)   # clockwise from 12 o'clock
            return center + radius * math.sin(a), center - radius * math.cos(a)

        canvas.delete("all")
        canvas.create_arc(*box, start=90, extent=-360 * day, style="arc",
                          outline=C_DAY, width=RING_W)
        canvas.create_arc(*box, start=90 - 360 * day, extent=-360 * (1 - day), style="arc",
                          outline=C_NIGHT, width=RING_W)

        _draw_sun(canvas, *polar(360 * day / 2, ring_r * 0.5), C_DAY)
        _draw_moon(canvas, *polar(360 * day + 360 * (1 - day) / 2, ring_r * 0.5), C_MOON)

        pos = self._home_cache.get("cycle_pos")
        if isinstance(pos, (int, float)):
            mx, my = polar(360 * (pos % 1.0), ring_r)
            canvas.create_oval(mx - 6, my - 6, mx + 6, my + 6, fill=C_TEXT, outline=C_CARD, width=2)

    # === PAGES === #
    def homePage(self, parent: ctk.CTkFrame) -> None:
        """ Home dashboard page """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=9)
        parent.grid_rowconfigure(1, weight=10)

        self._home_hero(parent)
        self._home_bottom(parent)
        self._apply_home_data({})   # re-apply cached values after a page switch

    def _home_hero(self, parent: ctk.CTkFrame) -> None:
        hero = self._card(parent, radius=R_HERO)
        hero.grid(row=0, column=0, sticky="nsew", pady=(0, GAP))
        hero.grid_columnconfigure(0, weight=11, uniform="hero")
        hero.grid_columnconfigure(1, weight=9, uniform="hero")
        hero.grid_rowconfigure(0, weight=1)

        # --- left: greeting, well-being, harvest, culture ---
        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(24, 8), pady=16)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        stack = ctk.CTkFrame(left, fg_color="transparent")
        stack.grid(row=0, column=0, sticky="w")

        self._ui_refs["greeting_val"] = ctk.CTkLabel(
            stack, text="Hello, User!", font=self._font(16, "bold"), text_color=C_TEXT)
        self._ui_refs["greeting_val"].pack(anchor="w")

        ctk.CTkLabel(stack, text="Culture well-being", font=self._font(12), text_color=C_MUTED).pack(
            anchor="w", pady=(10, 0))
        self._ui_refs["well_being_val"] = ctk.CTkLabel(
            stack, text="-", font=self._font(40, "bold"), text_color=C_ACCENT)
        self._ui_refs["well_being_val"].pack(anchor="w")

        self._metric_row(stack, "Days until harvest", "days_val", "-", unit="d.", size=14,
                         inline=True).pack(anchor="w", pady=(2, 0))

        self._ui_refs["culture_val"] = ctk.CTkLabel(
            stack, text="Arthrospira platensis", font=self._font(12, italic=True),
            text_color=C_ACCENT, fg_color=C_CARD_ALT, corner_radius=12, padx=12, pady=3)
        self._ui_refs["culture_val"].pack(anchor="w", pady=(10, 0))

        # --- right: wifi + clock, tiles, light cycle ---
        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 20), pady=14)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(right, fg_color="transparent")
        top.grid(row=0, column=0, sticky="e")
        wifi = ctk.CTkCanvas(top, width=26, height=20, highlightthickness=0, bg=C_CARD)
        wifi.pack(side="left", padx=(0, 8))
        self._ui_refs["wifi_canvas"] = wifi
        self._ui_refs["clock_lbl"] = ctk.CTkLabel(
            top, text=datetime.now().strftime("%H:%M  %d.%m.%Y"),
            font=self._font(13, mono=True), text_color=C_TEXT)
        self._ui_refs["clock_lbl"].pack(side="left")

        body = ctk.CTkFrame(right, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        tiles = ctk.CTkFrame(body, fg_color="transparent")
        tiles.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        tiles.grid_columnconfigure(0, weight=1)
        tiles.grid_rowconfigure((0, 1), weight=1, uniform="tiles")
        self._tile(tiles, "TARGET TEMP", "target_temp_val", "--", "°C").grid(
            row=0, column=0, sticky="nsew", pady=(0, 6))
        self._tile(tiles, "TARGET pH", "target_ph_val", "-.-", "").grid(
            row=1, column=0, sticky="nsew")

        cycle = ctk.CTkCanvas(body, width=CYCLE_SIZE, height=CYCLE_SIZE,
                              highlightthickness=0, bg=C_CARD)
        cycle.grid(row=0, column=1, sticky="e")
        self._ui_refs["cycle_canvas"] = cycle

    def _home_bottom(self, parent: ctk.CTkFrame) -> None:
        bottom = ctk.CTkFrame(parent, fg_color="transparent")
        bottom.grid(row=1, column=0, sticky="nsew")
        bottom.grid_columnconfigure(0, weight=9, uniform="bottom")
        bottom.grid_columnconfigure(1, weight=11, uniform="bottom")
        bottom.grid_rowconfigure(0, weight=1)

        # --- left: live readings + console shortcut ---
        b_left = ctk.CTkFrame(bottom, fg_color="transparent")
        b_left.grid(row=0, column=0, sticky="nsew", padx=(0, GAP // 2))
        b_left.grid_columnconfigure(0, weight=1)
        b_left.grid_rowconfigure(0, weight=3)
        b_left.grid_rowconfigure(1, weight=2)

        readings = self._card(b_left)
        readings.grid(row=0, column=0, sticky="nsew", pady=(0, GAP))
        readings.grid_columnconfigure(0, weight=1)
        items = [
            ("Current temperature", "temp_val", "--", "°C"),
            ("Current pH", "ph_val", "-.-", ""),
            ("Water level", "water_val", "-", ""),
        ]
        for i, (label, ref, default, unit) in enumerate(items):
            readings.grid_rowconfigure(2 * i, weight=1)
            self._metric_row(readings, label, ref, default, unit, size=15).grid(
                row=2 * i, column=0, sticky="ew", padx=18)
            if i < len(items) - 1:
                ctk.CTkFrame(readings, height=1, fg_color=C_BORDER).grid(
                    row=2 * i + 1, column=0, sticky="ew", padx=18)

        ctk.CTkButton(
            b_left, text="  >_  console", anchor="w", corner_radius=R_CARD,
            font=self._font(18, "bold", mono=True), text_color=C_ACCENT,
            fg_color=C_CARD_ALT, hover_color=C_BORDER, border_width=1, border_color=C_BORDER,
            command=lambda: self.router("console"),
        ).grid(row=1, column=0, sticky="nsew")

        # --- right: change culture + status matrix ---
        b_right = ctk.CTkFrame(bottom, fg_color="transparent")
        b_right.grid(row=0, column=1, sticky="nsew", padx=(GAP // 2, 0))
        b_right.grid_columnconfigure(0, weight=1)
        b_right.grid_rowconfigure(1, weight=1)

        ctk.CTkButton(
            b_right, text="Change culture", width=170, height=34, corner_radius=17,
            font=self._font(13, "bold"), text_color=C_ACCENT, fg_color="transparent",
            hover_color=C_CARD_ALT, border_width=1, border_color=C_ACCENT,
            command=lambda: self.system_queue.put({"type": "ui_event", "event": "change_culture"}),
        ).grid(row=0, column=0, sticky="e", pady=(0, GAP))

        matrix = self._card(b_right)
        matrix.grid(row=1, column=0, sticky="nsew")
        matrix.grid_columnconfigure((0, 2), weight=1, uniform="matrix")
        matrix.grid_columnconfigure(1, weight=0)
        matrix.grid_rowconfigure(0, weight=1)

        self._stat_column(matrix, 0, [("B_d", "bd_val"), ("B_h", "bh_val")])
        ctk.CTkFrame(matrix, width=1, fg_color=C_BORDER).grid(row=0, column=1, sticky="ns", pady=14)
        self._stat_column(matrix, 2, [("LU", "lu_val"), ("LS", "ls_val"), ("LL", "ll_val")])

    def _stat_column(self, matrix: ctk.CTkFrame, column: int, stats: list[tuple[str, str]]) -> None:
        col = ctk.CTkFrame(matrix, fg_color="transparent")
        col.grid(row=0, column=column, sticky="nsew", padx=18, pady=14)
        col.grid_columnconfigure(0, weight=1)
        for i, (label, ref) in enumerate(stats):
            col.grid_rowconfigure(i, weight=1)
            self._metric_row(col, label, ref, "XX", unit="%", size=15).grid(
                row=i, column=0, sticky="ew")

    def _placeholder(self, parent: ctk.CTkFrame, title: str) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        card = self._card(parent, radius=R_HERO)
        card.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=self._font(20, "bold"), text_color=C_TEXT).pack(
            anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(card, text="Not implemented yet.", font=self._font(13), text_color=C_MUTED).pack(
            anchor="w", padx=24)

    def telemetryPage(self, parent: ctk.CTkFrame) -> None:
        """ Telemetry page """
        self._placeholder(parent, "Telemetry")

    def consolePage(self, parent: ctk.CTkFrame) -> None:
        """ Console page """
        self._placeholder(parent, "Console")

    def settingsPage(self, parent: ctk.CTkFrame) -> None:
        """ Settings page """
        self._placeholder(parent, "Settings")