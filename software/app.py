""" Main app """

import threading
from queue import Queue

from modules import bridge, datamanager, cultivator, interface

def system_thread(  system_queue: Queue,
                    gui_queue: Queue,
                    stm_bridge: bridge.Bridge,
                    dat_man: datamanager.DataManager,
                    core: cultivator.CultivatorCore,
                    app: interface.App  ):
    """ System thread """

if __name__ == "__main__":
    # App command queues
    sys_command_buffer = Queue()
    gui_command_buffer = Queue()

    # App objects
    stm_bridge = bridge.Bridge()
    dat_man = datamanager.DataManager()
    core = cultivator.CultivatorCore()
    app = interface.App()

    # Start system daemon
    sys_thread = threading.Thread(
        target=system_thread,
        args=(sys_command_buffer, gui_command_buffer,
              stm_bridge, dat_man, core, app),
        daemon=True)
    sys_thread.start()

    # Start app loop
    app.mainloop()
