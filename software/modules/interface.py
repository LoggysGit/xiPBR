""" UI Interface module """

from queue import Queue

import customtkinter as ctk

class App(ctk.CTk):
    """ UI App """

    def __init__(self,
                 system_queue: Queue, ui_queue: Queue):
        """ Class init """

    def router(self):
        """ Pages router """
