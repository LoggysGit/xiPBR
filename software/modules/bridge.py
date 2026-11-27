""" STM32 <-> Host Bridge module """

from queue import Queue
import threading
import time
from typing import Any

import serial
from serial import SerialException

from .config import *

class Bridge:
    """ USB/UART Bridge class """

    def __init__(
        self,
        system_queue: Queue,
        ui_queue: Queue,
        os_mode: str = OS,
        port: str | None = STM_PORT,
        baudrate: int = BAUDRATE,
    ) -> None:
        """ Initializes USB/UART bridge """
        self.system_queue = system_queue
        self.ui_queue = ui_queue
        self.baudrate = baudrate

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._serial: serial.Serial | None = None

        self.os_mode = os_mode
        self.port = port
        self.set_os_mode(os_mode, port=port)

    def set_os_mode(self, mode: str, port: str | None = None) -> None:
        """ Switches platform mode ('windows' for tests, 'linux' for main target). """
        normalized = mode.strip().lower()
        if normalized not in ("windows", "linux"):
            self.system_queue.put(
                (f"[BRIDGE | WARN] Unknown OS mode '{mode}', keeping '{self.os_mode or 'linux'}'"),
                None
            )
            if not self.os_mode:
                normalized = "linux"
            else:
                return

        self.os_mode = normalized
        if port:
            self.port = port
        else:
            self.port = (
                getattr(globals(), "WIN_SERIAL_PORT", "COM3")
                if normalized == "windows"
                else getattr(globals(), "LINUX_SERIAL_PORT", "/dev/ttyACM0")
            )

        self._close_serial()
        self.system_queue.put(
            {
                "type": "log",
                "text": f"[BRIDGE] Mode set to '{self.os_mode}' (port: {self.port}, baud: {self.baudrate})",
            }
        )

    def _close_serial(self) -> None:
        if self._serial is not None:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except SerialException:
                pass
            finally:
                self._serial = None

    def _open_serial(self) -> bool:
        if self._serial is not None and self._serial.is_open:
            return True
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.2,
            )
            return True
        except SerialException as exc:
            self.system_queue.put(
                {
                    "type": "log",
                    "text": f"[BRIDGE | WARN] Cannot open {self.port} ({self.os_mode}): {exc}",
                }
            )
            self._serial = None
            return False

    def start(self) -> None:
        """ Starts listener thread """
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self.listen, name="BridgeListener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """ Stops listener loop and closes serial port """
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._close_serial()

    def listen(self) -> None:
        """ Listener loop """
        while not self._stop_event.is_set():
            if not self._open_serial():
                time.sleep(1.0)
                continue

            try:
                raw_line = self._serial.readline() if self._serial is not None else b""
                if raw_line:
                    # TODO
                    pass

            except SerialException as exc:
                self.system_queue.put(
                    (f"[BRIDGE | ERROR] Serial read error on {self.port}: {exc}"),
                    None
                )
                self._close_serial()
                time.sleep(0.5)

        self._close_serial()

    def send_settings(self, settings: Any) -> None:
        """ Sends settings to a COM-port """
        # TODO
