import os
from pprint import pprint
from time import sleep

import psutil
import win32gui
import win32process


sleep(3)


def get_dlls() -> list[str]:
    fg = win32gui.GetForegroundWindow()
    
    child_windows = []
    win32gui.EnumChildWindows(fg, lambda h, _: child_windows.append(h), None)

    dlls = set()
    window_handles = [fg, *child_windows]
    for handle in window_handles:
        (_, pid) = win32process.GetWindowThreadProcessId(handle)
        process = psutil.Process(pid)
        print(process)
        for dll in process.memory_maps():
            dlls.add(os.path.basename(dll.path))

    
    return sorted(list(dlls))

pprint(get_dlls())