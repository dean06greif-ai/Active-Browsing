"""Win32-Aufrufe über ctypes (nur Windows)."""
import ctypes
import os
import sys
import tempfile
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
MAPVK_VK_TO_VSC = 0
DESKTOP_READOBJECTS = 0x0001
UOI_NAME = 2
ERROR_ALREADY_EXISTS = 183
MB_ICONINFORMATION = 0x40

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
kernel32.SetThreadExecutionState.restype = wintypes.DWORD
kernel32.GetTickCount.argtypes = []
kernel32.GetTickCount.restype = wintypes.DWORD
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
user32.GetLastInputInfo.restype = wintypes.BOOL
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID,
                                             wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
user32.GetUserObjectInformationW.restype = wintypes.BOOL
user32.CloseDesktop.argtypes = [wintypes.HANDLE]
user32.CloseDesktop.restype = wintypes.BOOL
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
user32.MessageBoxW.restype = ctypes.c_int

HandlerRoutine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
kernel32.SetConsoleCtrlHandler.argtypes = [HandlerRoutine, wintypes.BOOL]
kernel32.SetConsoleCtrlHandler.restype = wintypes.BOOL


def _mouse_move(dx: int, dy: int) -> INPUT:
    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, 0)
    return inp


def _wheel(delta: int) -> INPUT:
    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(0, 0, delta & 0xFFFFFFFF, MOUSEEVENTF_WHEEL, 0, 0)
    return inp


def _key(vk: int, scan: int, up: bool) -> INPUT:
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(vk, scan, KEYEVENTF_KEYUP if up else 0, 0, 0)
    return inp


class Win32Api:
    def tick(self) -> int:
        return kernel32.GetTickCount()

    def last_input_tick(self) -> int:
        info = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        return info.dwTime

    def set_awake(self, on: bool) -> bool:
        flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if on else 0)
        return kernel32.SetThreadExecutionState(flags) != 0

    def is_locked(self) -> bool:
        """Gesperrt, wenn der Eingabedesktop nicht 'Default' ist (Sperrbildschirm, sicherer Desktop)."""
        h = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)
        if not h:
            return True
        try:
            buf = ctypes.create_unicode_buffer(256)
            needed = wintypes.DWORD()
            if not user32.GetUserObjectInformationW(h, UOI_NAME, buf, ctypes.sizeof(buf), ctypes.byref(needed)):
                return False
            return buf.value.lower() != "default"
        finally:
            user32.CloseDesktop(h)

    def execute(self, plan) -> bool:
        if plan.kind == "keys":
            return self._keys(plan.steps)
        if plan.kind == "scroll":
            return self._scroll(plan.steps)
        return self._mouse(plan.steps)

    @staticmethod
    def _send(*inputs) -> bool:
        arr = (INPUT * len(inputs))(*inputs)
        return user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT)) == len(inputs)

    def _mouse(self, steps) -> bool:
        origin = wintypes.POINT()
        have_pos = user32.GetCursorPos(ctypes.byref(origin))
        ok = True
        for dx, dy, pause in steps:
            ok &= self._send(_mouse_move(dx, dy))
            if pause:
                time.sleep(pause)
        if have_pos:
            time.sleep(0.015)
            now = wintypes.POINT()
            if user32.GetCursorPos(ctypes.byref(now)) and (now.x, now.y) != (origin.x, origin.y):
                user32.SetCursorPos(origin.x, origin.y)
        return ok

    def _scroll(self, steps) -> bool:
        ok = True
        for delta, pause in steps:
            if delta:
                ok &= self._send(_wheel(delta))
            if pause:
                time.sleep(pause)
        return ok

    def _keys(self, steps) -> bool:
        ok = True
        for vk, hold, pause in steps:
            scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
            ok &= self._send(_key(vk, scan, False))
            if hold:
                time.sleep(hold)
            ok &= self._send(_key(vk, scan, True))
            if pause:
                time.sleep(pause)
        return ok


def acquire_single_instance(name: str):
    h = kernel32.CreateMutexW(None, False, name)
    if not h:
        return None
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(h)
        return None
    return h


def close_handle(h) -> None:
    if h:
        kernel32.CloseHandle(h)


def set_dpi_aware() -> None:
    try:
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except AttributeError:
        pass
    try:
        ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        user32.SetProcessDPIAware()


def message_box(text: str, title: str) -> None:
    user32.MessageBoxW(None, text, title, MB_ICONINFORMATION)


def set_console_ctrl_handler(callback):
    """Strg+C, Konsole schließen, Abmelden, Herunterfahren; Rückgabe muss referenziert bleiben."""
    def _handler(ctrl_type):
        callback(ctrl_type)
        return True
    handler = HandlerRoutine(_handler)
    kernel32.SetConsoleCtrlHandler(handler, True)
    return handler


def selftest() -> int:
    lines, ok = [], True

    def check(name, cond, info="", essential=True):
        nonlocal ok
        tag = "OK" if cond else ("FEHLER" if essential else "WARNUNG")
        lines.append(f"[{tag}] {name} {info}".rstrip())
        if essential and not cond:
            ok = False

    expected = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
    check("sizeof(INPUT)", ctypes.sizeof(INPUT) == expected, f"= {ctypes.sizeof(INPUT)}, erwartet {expected}")
    api = Win32Api()
    check("GetTickCount", api.tick() > 0)
    try:
        check("GetLastInputInfo", True, f"Leerlauf {(api.tick() - api.last_input_tick()) & 0xFFFFFFFF} ms")
    except OSError as e:
        check("GetLastInputInfo", False, str(e), essential=False)
    check("SetThreadExecutionState an", api.set_awake(True))
    check("SetThreadExecutionState aus", api.set_awake(False))
    lines.append(f"[INFO] Eingabedesktop gesperrt: {api.is_locked()}")
    name = f"Local\\AwakeToggle.SelfTest.{os.getpid()}"
    h1 = acquire_single_instance(name)
    h2 = acquire_single_instance(name)
    check("Mutex anlegen", h1 is not None)
    check("Mutex erkennt Zweitinstanz", h2 is None)
    close_handle(h1)
    close_handle(h2)
    try:
        import pystray
        check("pystray-Backend", pystray.Icon.__module__.endswith("_win32"), pystray.Icon.__module__)
    except Exception as e:
        check("pystray-Backend", False, repr(e))
    lines.append("Ergebnis: " + ("bestanden" if ok else "FEHLGESCHLAGEN"))

    report = "\n".join(lines)
    with open(os.path.join(tempfile.gettempdir(), "AwakeToggle-selftest.txt"), "w", encoding="utf-8") as f:
        f.write(report + "\n")
    if sys.stdout:
        print(report)
    return 0 if ok else 1
