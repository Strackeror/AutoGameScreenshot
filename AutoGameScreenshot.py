import asyncio
import datetime
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import psutil
import win32gui
import win32process
from dataclasses_json import dataclass_json
from PIL import Image, ImageGrab
from pystray import Icon, Menu, MenuItem


@dataclass_json
@dataclass
class AgsConfig:
    # delay in seconds
    delay: int = 300
    quality: int = 80

    folder: str = "./Screenshots"

    additional_exes: List[str] = field(default_factory=lambda: [])
    ignored_exes: List[str] = field(default_factory=lambda: ["steam.exe"])


config = AgsConfig.from_json(open("./config.json", "r").read())


def should_screenshot(hwnd) -> bool:
    (tid, pid) = win32process.GetWindowThreadProcessId(hwnd)
    process = psutil.Process(pid)
    dlls = [os.path.basename(dll.path) for dll in process.memory_maps()]
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

    img_time = datetime.datetime.now().strftime("%H.%M.%S")
    window_name = win32gui.GetWindowText(hwnd)
    window_name = re.sub(r'[\\/*?:"<>|]', "", window_name)

    path = path / f"{img_time}-{window_name}.jpg"
    print(f"saving screenshot to {path}")
    img.save(path, quality=config.quality)


async def background_loop():
    while True:
        try:
            hwnd = win32gui.GetForegroundWindow()
            while not should_screenshot(hwnd):
                await asyncio.sleep(3)
                hwnd = win32gui.GetForegroundWindow()
            while should_screenshot(hwnd):
                screenshot(hwnd)
                await asyncio.sleep(config.delay)
                hwnd = win32gui.GetForegroundWindow()
        except Exception as e:
            print(f"Error {e}")


background_task = None


async def background():
    global background_task
    background_task = asyncio.create_task(background_loop())
    try:
        await background_task
    except asyncio.CancelledError:
        print("cancelled")
    print("Done")


event_loop = asyncio.new_event_loop()


async def stop():
    icon.stop()
    if background_task:
        background_task.cancel()


icon = Icon(
    "icon",
    icon=Image.open("icon.png"),
    menu=Menu(
        MenuItem("Exit", lambda: asyncio.run_coroutine_threadsafe(
            stop(), event_loop))
    ),
)
icon.run_detached()
event_loop.run_until_complete(background())
