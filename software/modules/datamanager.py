""" Data manager module """

from queue import Queue
import sqlite3
import time
from typing import Any

from .config import *

class DataManager:
    """ Data manager class """

    def __init__(self,
                 system_queue: Queue,
                 ui_queue: Queue) -> None:
        """ Initializes data manager """
        self.system_queue = system_queue
        self.ui_queue = ui_queue
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_FILE)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry (
                    timestamp INTEGER PRIMARY KEY,
                    temp REAL NOT NULL,
                    ph REAL NOT NULL,
                    turbidity_percent REAL NOT NULL,
                    water_level_ok INTEGER NOT NULL,
                    uptime_sec INTEGER NOT NULL,
                    state_code INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _get_field(self, telemetry: Any, name: str, default: Any = 0) -> Any:
        if isinstance(telemetry, dict):
            return telemetry.get(name, default)
        return getattr(telemetry, name, default)

    def write_log(self, log: str) -> None:
        """ Writes log into data/logs.log file """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{ts_str}] {log.rstrip()}\n"
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
        print(log)

    def save_telemetry(self, telemetry: Any) -> None:
        """ Saves incoming telemetry data into data/telemetry.db file """
        self._ensure_storage()
        ts = int(time.time())

        temp = round(int(self._get_field(telemetry, "temp_in_100", 0)) / 100.0, 2)
        ph = round(int(self._get_field(telemetry, "ph_10", 0)) / 10.0, 1)
        turbidity_percent = round(int(self._get_field(telemetry, "turbidity_ntu_100", 0)) / 100.0, 2)
        water_level_ok = 1 if bool(self._get_field(telemetry, "water_level_ok", False)) else 0
        uptime_sec = int(self._get_field(telemetry, "uptime_sec", 0))
        state_code = int(self._get_field(telemetry, "state_code", 0))

        conn = sqlite3.connect(DB_FILE)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO telemetry (
                        timestamp,
                        temp,
                        ph,
                        turbidity_percent,
                        water_level_ok,
                        uptime_sec,
                        state_code
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ts,
                        temp,
                        ph,
                        turbidity_percent,
                        water_level_ok,
                        uptime_sec,
                        state_code,
                    ),
                )
        finally:
            conn.close()

    def get_telemetry(self, metric_type: str, time_range: str = "now"):
        """ Returns telemetry by type and time:
        now (one), week_ago (one), month_ago (one), last_week (list), last_month (list)
        """
        if metric_type not in ALLOWED_TELEMETRY_COLUMNS:
            self.system_queue.put(
                f"[APP] (DATA MANAGER | ERROR) Unknown telemetry type: {metric_type}"
            )
            return None

        self._ensure_storage()
        now_ts = int(time.time())
        week_ago_ts = now_ts - 7 * SECONDS_DAY
        month_ago_ts = now_ts - 30 * SECONDS_DAY

        conn = sqlite3.connect(DB_FILE)
        try:
            cur = conn.cursor()

            match time_range:
                case "now":
                    target_ts = now_ts

                case "week_ago":
                    target_ts = week_ago_ts

                case "month_ago":
                    target_ts = month_ago_ts

                case "last_week":
                    rows = cur.execute(
                        f"SELECT {metric_type} FROM telemetry WHERE timestamp >= ? ORDER BY timestamp ASC",
                        (week_ago_ts,),
                    ).fetchall()
                    return [r[0] for r in rows]

                case "last_month":
                    rows = cur.execute(
                        f"SELECT {metric_type} FROM telemetry WHERE timestamp >= ? ORDER BY timestamp ASC",
                        (month_ago_ts,),
                    ).fetchall()
                    return [r[0] for r in rows]

                case _:
                    self.system_queue.put(
                        f"[APP] (DATA MANAGER | ERROR) Unknown telemetry time range: {time_range}"
                    )
                    return None

            row = cur.execute(
                f"SELECT {metric_type} FROM telemetry ORDER BY ABS(timestamp - ?) ASC LIMIT 1",
                (target_ts,),
            ).fetchone()
            return row[0] if row is not None else None
        finally:
            conn.close()
