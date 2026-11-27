""" STM32 <-> Host Bridge module """

from queue import Queue

class Bridge:
    """ USB/UART Bridge class """

    def __init__(self,
                 system_queue: Queue, ui_queue: Queue):
        """ """

    def listen(self) -> None:
        """ Listener loop """
