""" Data manager module """

from queue import Queue

class DataManager():
    """ Data manager class """

    def __init__(self,
                 system_queue: Queue, ui_queue: Queue):
        """ """

    def write_log(log: str) -> None:
        """ Writes log into data/logs.log file """

    def save_telemetry(telemetry) -> None:
        """ Saves incoming telemetry data into data/telemetry.db file """