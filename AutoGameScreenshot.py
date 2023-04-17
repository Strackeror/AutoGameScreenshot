import asyncio
import datetime
import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import dxcam
import psutil
import win32gui
import win32process
from PIL import Image
from pystray import Icon, Menu, MenuItem


@dataclass
class AgsConfig:
    # delay in seconds
    delay: int = 300
    quality: int = 80

    folder: str = "./Screenshots"

    dll_patterns: list[str] = field(
        default_factory=lambda: ["xinput", "game", "steam", "gaming", "dinput8"]
    )
    additional_exes: list[str] = field(default_factory=lambda: [])
    ignored_exes: list[str] = field(
        default_factory=lambda: ["steam.exe", "xboxpcapp.exe", "explorer.exe"]
    )


config = AgsConfig()
with open("./config.json", "r+") as configFile:
    config = AgsConfig(**json.loads(configFile.read() or "{}"))

with open("./config.json", "w") as configFile:
    configFile.write(json.dumps(asdict(config), indent=4))

cam = dxcam.create()

def get_dlls(hwnd) -> list[str]:
    child_windows = []
    win32gui.EnumChildWindows(hwnd, lambda h, _: child_windows.append(h), None)

    dlls = set()
    window_handles = [hwnd, *child_windows]
    for handle in window_handles:
        (_, pid) = win32process.GetWindowThreadProcessId(handle)
        process = psutil.Process(pid)
        for dll in process.memory_maps():
            dlls.add(os.path.basename(dll.path))
    return sorted([*dlls])


def get_process_names(hwnd) -> list[str]:
    child_windows = []
    win32gui.EnumChildWindows(hwnd, lambda h, _: child_windows.append(h), None)

    names = set()
    window_handles = [hwnd, *child_windows]
    for handle in window_handles:
        (_, pid) = win32process.GetWindowThreadProcessId(handle)
        process = psutil.Process(pid)
        names.add(process.name())
    return [*names]


def should_screenshot(hwnd) -> bool:
    names = get_process_names(hwnd)
    for name in names:
        for ignored in config.ignored_exes:
            if re.search(ignored, name, re.IGNORECASE):
                return False
        for additional in config.additional_exes:
            if re.search(additional, name, re.IGNORECASE):
                return True

    dlls = get_dlls(hwnd)
    for dll in dlls:
        for dll_pattern in config.dll_patterns:
            if re.search(dll_pattern, dll, re.IGNORECASE):
                print(f"matched {dll_pattern} in {dll}")
                return True
    return False


def screenshot(hwnd):
    x, y, x1, y1 = win32gui.GetWindowRect(hwnd)
    frame = cam.grab(region=(x,y,x1,y1))
    print(frame)
    img = Image.fromarray(frame)

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
            await asyncio.sleep(3)
            hwnd = win32gui.GetForegroundWindow()
            while not should_screenshot(hwnd):
                await asyncio.sleep(3)
                hwnd = win32gui.GetForegroundWindow()
            while should_screenshot(hwnd):
                screenshot(hwnd)
                await asyncio.sleep(config.delay)
                hwnd = win32gui.GetForegroundWindow()
        except Exception as e:
            print(f"Error {e}, {e.with_traceback(None)}")


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
        MenuItem("Exit", lambda: asyncio.run_coroutine_threadsafe(stop(), event_loop))
    ),
)
icon.run_detached()
event_loop.run_until_complete(background())
