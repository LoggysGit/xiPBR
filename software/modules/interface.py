""" UI Interface module """

import math
import tkinter.font as tkfont
from collections import deque
from datetime import datetime
from queue import Empty, Queue
from typing import Any

import customtkinter as ctk

# === WINDOW & THEME === #
# Redmi Note 8 landscape is 2340x1080 = 13:6; 1024x472 keeps that ratio.
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

# === DISPLAYED DATA === #
# Every value shown on the home page lives here. Replace the defaults with real data, or push
# updates at runtime:  ui_queue.put({"action": "update_home", "data": {"temp": 24.5, "cycle_pos": 0.42}})
# Values are shown as-is (units are static captions below), so send already formatted numbers.
DATA: dict[str, Any] = {
    "greeting": "Hello, User!",
    "well_being": "-",
    "days_until_harvest": "-",
    "culture_name": "Arthrospira platensis",
    "target_temp": "--",
    "target_ph": "-.-",
    "temp": "--",
    "ph": "-.-",
    "water_level": "-",
    "aeration_day": "XX",
    "aeration_night": "XX",
    "light_top": "XX",
    "light_side": "XX",
    "light_bottom": "XX",
    "clock": "--:--  --.--.----",   # refreshed automatically once a minute
    "wifi_level": 2,               # 0..3 bars
    "day_fraction": 0.6,           # share of the light period in the 24 h cycle, 0..1
    "cycle_pos": 0.3,              # marker on the ring, 0..1 (0 = lights on). Real time: (h * 60 + m) / 1440
}

# Console: history is kept in memory, the home page previews the last CONSOLE_LINES lines.
CONSOLE_BOOT = ("xiPBR Mk I console ready",)
CONSOLE_PROMPT = ">_"
CONSOLE_LINES, CONSOLE_CHARS, CONSOLE_HISTORY = 4, 52, 500

# Static captions: (caption, data key, unit)
NAV = (("home", "◎"), ("telemetry", "≡"), ("console", ">_"), ("settings", "⚙"))
TILES = (("TARGET TEMP", "target_temp", "°C"), ("TARGET pH", "target_ph", ""))
READINGS = (("Current temperature", "temp", "°C"), ("Current pH", "ph", ""), ("Water level", "water_level", ""))
STATS = (   # two columns of the status matrix; rows are shared, so the columns line up
    (("Aeration (day)", "aeration_day", "%"), ("Aeration (night)", "aeration_night", "%")),
    (("Top Light", "light_top", "%"), ("Side Light", "light_side", "%"), ("Bottom Light", "light_bottom", "%")),
)


def card(parent: Any, radius: int = R_CARD, fg: str = C_CARD) -> ctk.CTkFrame:
    """ Rounded panel with a thin border """
    return ctk.CTkFrame(parent, corner_radius=radius, fg_color=fg, border_width=1, border_color=C_BORDER)


class App(ctk.CTk):
    """ UI App """

    def __init__(self, system_queue: Queue, ui_queue: Queue):
        """ Class init """
        ctk.set_appearance_mode("dark")
        super().__init__()

        self.system_queue, self.ui_queue = system_queue, ui_queue
        self.gui_command_buffer: list[dict[str, Any]] = []

        self.title("xiPBR Mk I")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(WINDOW_W, WINDOW_H)
        self.configure(fg_color=C_BG)

        installed = set(tkfont.families())
        self._sans = next((f for f in SANS_FONTS if f in installed), SANS_FONTS[-1])
        self._mono = next((f for f in MONO_FONTS if f in installed), MONO_FONTS[-1])

        self.data: dict[str, Any] = dict(DATA)    # current values, single source of truth
        self.refs: dict[str, Any] = {}            # widgets of the page on screen, by data key
        self.log_lines: deque[str] = deque(CONSOLE_BOOT, maxlen=CONSOLE_HISTORY)
        self._page = "home"
        self._pages = {
            "home": self.homePage,
            "telemetry": lambda p: self._stub(p, "Telemetry"),
            "console": self.consolePage,
            "settings": lambda p: self._stub(p, "Settings"),
        }

        # Sidebar + content area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(self, width=64, corner_radius=0, fg_color=C_SIDEBAR)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(3, weight=1)    # spacer: settings sits at the bottom
        self._nav: dict[str, ctk.CTkButton] = {}
        for i, (page, icon) in enumerate(NAV):
            btn = ctk.CTkButton(
                sidebar, text=icon, width=44, height=44, corner_radius=12, font=self._font(18, "bold"),
                fg_color="transparent", hover_color=C_CARD, text_color=C_MUTED,
                command=lambda p=page: self.router(p),
            )
            btn.grid(row=4 if page == "settings" else i, column=0,
                     pady=(14 if i == 0 else 4, 14 if page == "settings" else 4))
            self._nav[page] = btn

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=(GAP, 12), pady=12)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.router("home")
        self._poll_commands()

    # === HELPERS === #
    def _font(self, size: int, style: str = "normal", mono: bool = False) -> tuple[str, int, str]:
        return (self._mono if mono else self._sans, size, style)

    def _lbl(self, parent: Any, text: str = "", key: str | None = None, size: int = 14,
             style: str = "normal", color: str = C_TEXT, mono: bool = False, **kw: Any) -> ctk.CTkLabel:
        """ Label factory. height=0 stops CTk from forcing its 28 px minimum height (that is what
        clipped the old tiles and the culture pill). `key` binds the label to a DATA value. """
        if key:
            text = str(self.data[key])
        label = ctk.CTkLabel(parent, text=text, height=0, font=self._font(size, style, mono),
                             text_color=color, **kw)
        if key:
            self.refs[key] = label
        return label

    def _metric(self, parent: Any, row: int, col: int, caption: str, key: str, unit: str,
                size: int = 15) -> None:
        """ One 'caption ........ value unit' line on a shared grid row; the unit column has a fixed
        width, so values line up on the right edge even when some rows have no unit """
        line = ctk.CTkFrame(parent, fg_color="transparent")
        line.grid(row=row, column=col, sticky="ew", padx=18)
        line.grid_columnconfigure(0, weight=1)
        self._lbl(line, caption, size=size, color=C_MUTED).grid(row=0, column=0, sticky="sw")
        self._lbl(line, key=key, size=size, style="bold").grid(row=0, column=1, sticky="se")
        self._lbl(line, unit, size=size - 2, color=C_MUTED, width=34, anchor="w").grid(
            row=0, column=2, sticky="sw", padx=(3, 0))

    def _tail(self) -> str:
        """ Last CONSOLE_LINES log lines, cut to the width of the home preview """
        lines = list(self.log_lines)[-CONSOLE_LINES:]
        return "\n".join(s if len(s) <= CONSOLE_CHARS else s[:CONSOLE_CHARS - 1] + "…" for s in lines)

    # === ROUTER, QUEUE, DATA === #
    def router(self, page_name: str | None = None) -> None:
        """ Pages router """
        page = page_name or self._page
        if page not in self._pages:
            return
        self._page = page
        self.refs.clear()
        for widget in self.content.winfo_children():
            widget.destroy()
        for key, btn in self._nav.items():
            on = key == page
            btn.configure(fg_color=C_CARD_ALT if on else "transparent",
                          text_color=C_ACCENT if on else C_MUTED,
                          border_width=int(on), border_color=C_ACCENT_DIM)
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        self._pages[page](frame)

    def _poll_commands(self) -> None:
        """ Drain the command buffer and ui_queue, then keep the clock fresh """
        cmds = self.gui_command_buffer[:]
        self.gui_command_buffer.clear()
        while True:
            try:
                cmds.append(self.ui_queue.get_nowait())
            except Empty:
                break
        for cmd in cmds:
            if not isinstance(cmd, dict):
                continue
            action = cmd.get("action")
            if action == "navigate" and isinstance(cmd.get("page"), str):
                self.router(cmd["page"])
            elif action == "update_home" and isinstance(cmd.get("data"), dict):
                self.update_data(cmd["data"])
            elif action == "log":
                self.log(str(cmd.get("text", "")))
        clock = datetime.now().strftime(CLOCK_FORMAT)
        if clock != self.data["clock"]:
            self.update_data({"clock": clock})
        self.after(150, self._poll_commands)

    def update_data(self, new: dict[str, Any]) -> None:
        """ Merge new values into self.data and refresh whatever is on screen """
        self.data.update(new)
        for key, value in new.items():
            if key in self.refs:
                self.refs[key].configure(text=str(value))
        if new.keys() & {"wifi_level", "day_fraction", "cycle_pos"}:
            self._draw_canvases()

    def log(self, text: str) -> None:
        """ Append a line to the console history; home preview and console page update live """
        line = f"[{datetime.now():%H:%M:%S}] {text}"
        self.log_lines.append(line)
        if (preview := self.refs.get("console_preview")) is not None:
            preview.configure(text=self._tail())
        if (box := self.refs.get("console_box")) is not None:
            box.configure(state="normal")
            box.insert("end", line + "\n")
            box.see("end")
            box.configure(state="disabled")

    def _draw_canvases(self) -> None:
        """ Redraw the Wi-Fi icon and the day/night ring from self.data """
        wifi, ring = self.refs.get("wifi_canvas"), self.refs.get("cycle_canvas")
        if wifi is not None:
            wifi.delete("all")
            level = int(self.data["wifi_level"])
            for i, r in enumerate((5, 9, 13), start=1):
                wifi.create_arc(13 - r, 16 - r, 13 + r, 16 + r, start=45, extent=90, style="arc",
                                outline=C_ACCENT if level >= i else C_BORDER, width=2)
            wifi.create_oval(11, 14, 15, 18, fill=C_ACCENT if level else C_BORDER, outline="")

        if ring is not None:
            c = CYCLE_SIZE / 2
            r = c - 14
            day = min(max(float(self.data["day_fraction"]), 0.05), 0.95)
            pos = float(self.data["cycle_pos"]) % 1.0

            def at(turn: float, radius: float) -> tuple[float, float]:
                """ Point on the ring; turn is 0..1 clockwise from 12 o'clock """
                a = math.tau * turn
                return c + radius * math.sin(a), c - radius * math.cos(a)

            ring.delete("all")
            box = (c - r, c - r, c + r, c + r)
            ring.create_arc(*box, start=90, extent=-360 * day, style="arc", outline=C_DAY, width=RING_W)
            ring.create_arc(*box, start=90 - 360 * day, extent=-360 * (1 - day), style="arc",
                            outline=C_NIGHT, width=RING_W)
            sx, sy = at(day / 2, r * 0.5)                      # sun
            ring.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill=C_DAY, outline="")
            for k in range(8):
                a = math.radians(45 * k)
                ring.create_line(sx + 7 * math.cos(a), sy + 7 * math.sin(a),
                                 sx + 10 * math.cos(a), sy + 10 * math.sin(a),
                                 fill=C_DAY, width=2, capstyle="round")
            mx, my = at(day + (1 - day) / 2, r * 0.5)          # moon (disc minus a card-colored disc)
            ring.create_oval(mx - 7, my - 7, mx + 7, my + 7, fill=C_MOON, outline="")
            ring.create_oval(mx - 3, my - 8, mx + 9, my + 4, fill=C_CARD, outline="")
            px, py = at(pos, r)                                # current time marker
            ring.create_oval(px - 7, py - 7, px + 7, py + 7, fill=C_TEXT, outline=C_CARD, width=2)

    # === PAGES === #
    def homePage(self, parent: ctk.CTkFrame) -> None:
        """ Home dashboard page """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=9, uniform="home")
        parent.grid_rowconfigure(1, weight=10, uniform="home")

        # --- hero card ---
        hero = card(parent, R_HERO)
        hero.grid(row=0, column=0, sticky="nsew", pady=(0, GAP))
        hero.grid_columnconfigure(0, weight=11, uniform="hero")
        hero.grid_columnconfigure(1, weight=9, uniform="hero")
        hero.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(24, 8))
        self._lbl(left, key="greeting", size=17, style="bold").pack(anchor="w")
        self._lbl(left, "Culture well-being", size=12, color=C_MUTED).pack(anchor="w", pady=(10, 0))
        self._lbl(left, key="well_being", size=38, style="bold", color=C_ACCENT).pack(anchor="w")
        days = ctk.CTkFrame(left, fg_color="transparent")
        days.pack(anchor="w")
        self._lbl(days, "Days until harvest", size=14, color=C_MUTED).pack(side="left")
        self._lbl(days, key="days_until_harvest", size=14, style="bold").pack(side="left", padx=(6, 2))
        self._lbl(days, "d.", size=14, color=C_MUTED).pack(side="left")
        self._lbl(left, key="culture_name", size=12, style="italic", color=C_ACCENT,
                  fg_color=C_CARD_ALT, corner_radius=12, pady=3).pack(anchor="w", pady=(12, 0))

        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 20), pady=14)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        status = ctk.CTkFrame(right, fg_color="transparent")
        status.grid(row=0, column=0, sticky="e")
        self.refs["wifi_canvas"] = ctk.CTkCanvas(status, width=26, height=20, highlightthickness=0, bg=C_CARD)
        self.refs["wifi_canvas"].pack(side="left", padx=(0, 8))
        self._lbl(status, key="clock", size=13, mono=True).pack(side="left")

        body = ctk.CTkFrame(right, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        tiles = ctk.CTkFrame(body, fg_color="transparent")
        tiles.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        tiles.grid_columnconfigure(0, weight=1)
        tiles.grid_rowconfigure((0, 1), weight=1, uniform="tiles")
        for i, (caption, key, unit) in enumerate(TILES):
            tile = card(tiles, R_TILE, C_CARD_ALT)
            tile.grid(row=i, column=0, sticky="nsew", pady=(0, 6) if i == 0 else 0)
            tile.grid_columnconfigure(0, weight=1)
            tile.grid_rowconfigure((0, 1), weight=1)
            self._lbl(tile, caption, size=10, color=C_MUTED).grid(row=0, column=0, sticky="sw", padx=14)
            value = ctk.CTkFrame(tile, fg_color="transparent")
            value.grid(row=1, column=0, sticky="nw", padx=14)
            self._lbl(value, key=key, size=22, style="bold").pack(side="left")
            if unit:
                self._lbl(value, unit, size=12, color=C_MUTED).pack(side="left", anchor="s", padx=(3, 0), pady=(0, 3))
        self.refs["cycle_canvas"] = ctk.CTkCanvas(body, width=CYCLE_SIZE, height=CYCLE_SIZE,
                                                  highlightthickness=0, bg=C_CARD)
        self.refs["cycle_canvas"].grid(row=0, column=1, sticky="e")

        # --- bottom: readings + console (left), culture button + status matrix (right) ---
        bottom = ctk.CTkFrame(parent, fg_color="transparent")
        bottom.grid(row=1, column=0, sticky="nsew")
        bottom.grid_columnconfigure(0, weight=9, uniform="bottom")
        bottom.grid_columnconfigure(1, weight=11, uniform="bottom")
        bottom.grid_rowconfigure(0, weight=1)

        b_left = ctk.CTkFrame(bottom, fg_color="transparent")
        b_left.grid(row=0, column=0, sticky="nsew", padx=(0, GAP // 2))
        b_left.grid_columnconfigure(0, weight=1)
        b_left.grid_rowconfigure((0, 1), weight=1, uniform="left")

        readings = card(b_left)
        readings.grid(row=0, column=0, sticky="nsew", pady=(0, GAP // 2))
        readings.grid_columnconfigure(0, weight=1)
        for i, (caption, key, unit) in enumerate(READINGS):
            readings.grid_rowconfigure(2 * i, weight=1)
            self._metric(readings, 2 * i, 0, caption, key, unit)
            if i < len(READINGS) - 1:
                ctk.CTkFrame(readings, height=1, fg_color=C_BORDER).grid(
                    row=2 * i + 1, column=0, sticky="ew", padx=18)

        console = card(b_left, fg=C_SIDEBAR)
        console.grid(row=1, column=0, sticky="nsew", pady=(GAP // 2, 0))
        console.grid_columnconfigure(0, weight=1)
        console.grid_rowconfigure(0, weight=1)
        preview = self._lbl(console, self._tail(), size=11, mono=True, color=C_MUTED, anchor="sw", justify="left")
        preview.grid(row=0, column=0, sticky="nsew", padx=14, pady=(8, 0))
        self.refs["console_preview"] = preview
        prompt = self._lbl(console, CONSOLE_PROMPT, size=13, style="bold", mono=True, color=C_ACCENT)
        prompt.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))
        for widget in (console, preview, prompt):
            widget.bind("<Button-1>", lambda _e: self.router("console"))

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

        matrix = card(b_right)
        matrix.grid(row=1, column=0, sticky="nsew")
        matrix.grid_columnconfigure((0, 2), weight=1, uniform="stats")
        matrix.grid_rowconfigure((0, 1, 2), weight=1, uniform="stats_rows")
        ctk.CTkFrame(matrix, width=1, fg_color=C_BORDER).grid(row=0, column=1, rowspan=3, sticky="ns", pady=14)
        for col, items in zip((0, 2), STATS):
            for row, (caption, key, unit) in enumerate(items):
                self._metric(matrix, row, col, caption, key, unit)

        self._draw_canvases()

    def consolePage(self, parent: ctk.CTkFrame) -> None:
        """ Console page: scrollback history + command input """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        box = ctk.CTkTextbox(parent, font=self._font(13, mono=True), fg_color=C_SIDEBAR, text_color=C_MUTED,
                             border_width=1, border_color=C_BORDER, corner_radius=R_CARD, wrap="word")
        box.grid(row=0, column=0, sticky="nsew")
        box.insert("1.0", "\n".join(self.log_lines) + "\n")
        box.see("end")
        box.configure(state="disabled")
        self.refs["console_box"] = box

        entry = ctk.CTkEntry(parent, height=38, corner_radius=R_CARD, font=self._font(13, mono=True),
                             fg_color=C_CARD_ALT, border_color=C_BORDER, text_color=C_ACCENT,
                             placeholder_text=f"{CONSOLE_PROMPT}  type a command")
        entry.grid(row=1, column=0, sticky="ew", pady=(GAP, 0))

        def send(_event: Any = None) -> None:
            cmd = entry.get().strip()
            if cmd:
                self.log(f"> {cmd}")
                self.system_queue.put({"type": "ui_event", "event": "console_command", "text": cmd})
                entry.delete(0, "end")

        entry.bind("<Return>", send)
        entry.focus()

    def _stub(self, parent: ctk.CTkFrame, title: str) -> None:
        """ Placeholder page """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        box = card(parent, R_HERO)
        box.grid(row=0, column=0, sticky="nsew")
        self._lbl(box, title, size=20, style="bold").pack(anchor="w", padx=24, pady=(20, 4))
        self._lbl(box, "Not implemented yet.", size=13, color=C_MUTED).pack(anchor="w", padx=24)
