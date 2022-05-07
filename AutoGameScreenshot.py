from dataclasses import dataclass, field
import win32gui
import win32process
import psutil
import os
import datetime
from PIL import Image, ImageGrab

from pystray import Icon, Menu, MenuItem
from typing import List
import asyncio
import re
from pathlib import Path

@dataclass
class AgsConfig:
    # delay in seconds
    delay: int = 300
    quality: int = 80

    folder: str = "./Screenshots"

    additional_exes: List[str] = field(default_factory=lambda: [])
    ignored_exes: List[str] = field(default_factory=lambda: ["steam.exe"])

config = AgsConfig()


def should_screenshot(hwnd) -> bool:
    (tid, pid) = win32process.GetWindowThreadProcessId(hwnd)
    process = psutil.Process(pid)
    dlls = [os.path.basename(dll.path)
            for dll in process.memory_maps()]
    dlls = sorted(dlls)

    if process.name() in config.additional_exes:
        return True
    if process.name() in config.ignored_exes:
        return False
    return any("xinput" in dll for dll in dlls)

def screenshot(hwnd):
    x, y, x1, y1 = win32gui.GetWindowRect(hwnd)
    img = ImageGrab.grab((x, y, x1, y1), all_screens=True)

    date = datetime.date.today().isoformat()
    path = Path(config.folder).joinpath(date)
    path.mkdir(parents=True, exist_ok=True)

    img_time = datetime.datetime.now().strftime('%H-%M-%S')
    window_name = win32gui.GetWindowText(hwnd)
    window_name = re.sub(r'[\\/*?:"<>|]', "", window_name)

    
    path = path / f"{img_time}-{window_name}.jpg"
    print(f"saving screenshot to {path}")
    img.save(path, quality=config.quality)
    
async def background_loop():
    while True:
        hwnd = win32gui.GetForegroundWindow()
        try:
            if should_screenshot(hwnd):
                screenshot(hwnd)
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(config.delay)

background_task = None
async def background():
    global background_task
    background_task = asyncio.create_task(background_loop())
    try:
        await background_task
    except asyncio.CancelledError:
        print("cancelled")
    print('Done')

event_loop = asyncio.new_event_loop()
async def stop():
    icon.stop()
    if background_task:
        background_task.cancel()


icon = Icon('icon', icon=Image.open("icon.png"),
            menu=Menu(
                MenuItem('Exit', lambda: asyncio.run_coroutine_threadsafe(stop(), event_loop))))
icon.run_detached()
event_loop.run_until_complete(background())
