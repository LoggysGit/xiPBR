""" Data manager module """

from queue import Queue

class DataManager():
    """ Data manager class """

    def __init__(self,
                 system_queue: Queue, ui_queue: Queue):
        """ """
