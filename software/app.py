""" Main app """

import threading
from queue import Queue

from modules import bridge, datamanager, interface

def system_thread(  system_queue: Queue,
                    gui_queue: Queue,
                    stm_bridge: bridge.Bridge,
                    dat_man: datamanager.DataManager,
                    app: interface.App  ):
    """ System thread """
    stm_bridge.listen()

    while True:
        item = system_queue.get()

        try:
            command, payload = item
            match command:
                case "WRITE_LOG":
                    dat_man.write_log(payload)
                    gui_queue.put(("UPDATE_CONSOLE", None))

                # Unknown command #
                case _:
                    print(f"Unknown command: {command}")

        except ValueError:
            print(f"Wrong command structure (CMD, PAYLOAD): {item}")

        except Exception as e:
            print(f"System thread error: {e}")

        finally:
            system_queue.task_done()

if __name__ == "__main__":
    # App command queues
    sys_command_buffer = Queue()
    gui_command_buffer = Queue()

    # App objects
    stm_bridge = bridge.Bridge(sys_command_buffer, gui_command_buffer)
    dat_man = datamanager.DataManager(sys_command_buffer, gui_command_buffer)
    app = interface.App(sys_command_buffer, gui_command_buffer)

    # Start system daemon
    sys_thread = threading.Thread(
        target=system_thread,
        args=(sys_command_buffer, gui_command_buffer,
              stm_bridge, dat_man, app),
        daemon=True)
    sys_thread.start()

    # Start app loop
    app.mainloop()
