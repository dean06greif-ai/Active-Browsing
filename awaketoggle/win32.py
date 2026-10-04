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
    _runner = None

    def browse(self, plan, cfg, cancel):
        if self._runner is None:
            from .browse_runner import Runner
            self._runner = Runner(Desktop())
        badge = None
        if cfg.badge_read:
            from .badge_win import read_badge
            badge = lambda h: read_badge(h, cfg.badge_extension)  # noqa: E731
        return self._runner.run(plan, cfg.browse_processes, cancel, cfg.verbose_log, badge, cfg.browse_private_words)

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
    try:
        desk = Desktop()
        fg = desk.root(desk.foreground())
        lines.append(f"[INFO] Vordergrundprogramm: {desk.process_name(fg) if fg else '-'}")
        from .browse import BrowserNames, is_private
        from .config import app_dir, load
        names = BrowserNames()
        try:
            words = load(app_dir() / "config.json")[0].browse_private_words
        except Exception:
            words = ()
        for w in desk.app_windows():
            if desk.process_name(w) in names:
                kind = "Inkognito/InPrivate – wird NIE benutzt" if is_private(desk.title(w), words) else "normal"
                lines.append(f"[INFO] Browserfenster: {desk.process_name(w)} – {desk.title(w)[:60]!r} ({kind})")
        h = desk.find_browser(names, skip=lambda w: is_private(desk.title(w), words))
        lines.append(f"[INFO] Browser-Test würde nutzen: {desk.process_name(h) if h else '-'}"
                     f"{' – ' + desk.title(h)[:60] if h else ''}")
        if h:
            try:
                from .badge_win import read_badge, toolbar_buttons
                for name, help_text, cls, rect, _ in toolbar_buttons(h):
                    lines.append(f"[INFO]   Button: {name!r} Tooltip={help_text!r} Klasse={cls!r} {rect}")
                from .badge_win import _candidates, _child_texts
                for name, _, cls, _, el in _candidates(toolbar_buttons(h)):
                    lines.append(f"[INFO] Zähler-Kandidat: {name!r} ({cls}) Unterelemente={_child_texts(el)!r}")
                lines.append(f"[INFO] Zähler (automatisch): {read_badge(h)}")
            except Exception as e:
                check("UI Automation", False, repr(e), essential=False)
        check("EnumWindows", len(desk.top_windows()) >= 0, essential=False)
    except Exception as e:
        check("Fensterfunktionen", False, repr(e), essential=False)
    lines.append("Ergebnis: " + ("bestanden" if ok else "FEHLGESCHLAGEN"))

    report = "\n".join(lines)
    with open(os.path.join(tempfile.gettempdir(), "AwakeToggle-selftest.txt"), "w", encoding="utf-8") as f:
        f.write(report + "\n")
    if sys.stdout:
        print(report)
    return 0 if ok else 1


# ---------- Browser-Test: Fenster, Prozesse, Tastatur und Maus ----------

GA_ROOTOWNER = 3
GW_OWNER = 4
SW_RESTORE = 9
VK_MENU = 0x12
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP = 0x0008, 0x0010
MOUSEEVENTF_VIRTUALDESK, MOUSEEVENTF_ABSOLUTE = 0x4000, 0x8000
SM_SWAPBUTTON = 23
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
EXTENDED_VKS = frozenset({0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x6F})
MODIFIER_VKS = frozenset({0x10, 0x11, 0x12})
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
DWMWA_CLOAKED = 14
SHELL_PROCS = frozenset({
    "explorer.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe", "searchhost.exe", "searchapp.exe",
    "textinputhost.exe", "lockapp.exe", "applicationframehost.exe", "systemsettings.exe", "taskmgr.exe",
    "awaketoggle.exe", "python.exe", "pythonw.exe", "widgets.exe", "shellhost.exe",
})

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wintypes.LONG
try:
    dwmapi = ctypes.WinDLL("dwmapi")
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long
except OSError:
    dwmapi = None
try:
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    user32.GetDpiForWindow.restype = wintypes.UINT
except AttributeError:
    pass


def _vk_input(vk: int, up: bool) -> INPUT:
    flags = (KEYEVENTF_KEYUP if up else 0) | (KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_VKS else 0)
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(vk, user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC), flags, 0, 0)
    return inp


def _unicode_input(ch: str, up: bool) -> INPUT:
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0), 0, 0)
    return inp


def _mouse_flags(flags: int, dx: int = 0, dy: int = 0) -> INPUT:
    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(dx, dy, 0, flags, 0, 0)
    return inp


class Desktop:
    """Fenster- und Eingabefunktionen für den Browser-Test (Handles als int)."""

    send = staticmethod(Win32Api._send)

    def tick(self) -> int:
        return kernel32.GetTickCount()

    def last_input_tick(self) -> int:
        return Win32Api().last_input_tick()

    def foreground(self) -> int:
        return user32.GetForegroundWindow() or 0

    def root(self, h: int) -> int:
        return (user32.GetAncestor(h, GA_ROOTOWNER) or h) if h else 0

    def process_name(self, h: int) -> str:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        hp = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not hp:
            return ""
        try:
            buf, size = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
            if not kernel32.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(size)):
                return ""
            return os.path.basename(buf.value).lower()
        finally:
            kernel32.CloseHandle(hp)

    def is_window(self, h: int) -> bool:
        return bool(h) and bool(user32.IsWindow(h))

    def is_visible(self, h: int) -> bool:
        return bool(user32.IsWindowVisible(h))

    def title(self, h: int) -> str:
        n = user32.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(h, buf, n + 1)
        return buf.value

    def window_rect(self, h: int) -> tuple:
        r = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        return r.left, r.top, r.right, r.bottom

    def dpi(self, h: int) -> int:
        try:
            return user32.GetDpiForWindow(h) or 96
        except AttributeError:
            return 96

    def top_windows(self) -> set:
        """Alle Fenster der obersten Ebene (auch unsichtbare), damit nur wirklich neue als eigene gelten."""
        found = set()

        def cb(h, _):
            found.add(h)
            return True
        user32.EnumWindows(WNDENUMPROC(cb), 0)
        return found

    def app_windows(self) -> list:
        found = []

        def cb(h, _):
            if self.is_app_window(h):
                found.append(h)
            return True
        user32.EnumWindows(WNDENUMPROC(cb), 0)
        return found

    def is_app_window(self, h: int) -> bool:
        if not user32.IsWindowVisible(h) or user32.GetWindow(h, GW_OWNER) or user32.GetWindowTextLengthW(h) <= 0:
            return False
        if user32.GetWindowLongW(h, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return False
        cloaked = wintypes.DWORD()
        if dwmapi and not dwmapi.DwmGetWindowAttribute(h, DWMWA_CLOAKED, ctypes.byref(cloaked),
                                                       ctypes.sizeof(cloaked)) and cloaked.value:
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value == os.getpid():
            return False
        left, top, right, bottom = self.window_rect(h)
        return right - left > 200 and bottom - top > 200 or bool(user32.IsIconic(h))

    def find_consent(self, h: int):
        from .consent_win import find_accept_button
        return find_accept_button(h)

    def find_browser(self, names, skip=lambda h: False) -> int:
        """Oberstes Browserfenster (Z-Reihenfolge), übersprungene (Inkognito) nie; sonst oberstes Programmfenster.

        Wurde ein Browserfenster übersprungen, gibt es keinen Ersatz durch ein beliebiges Programmfenster.
        """
        front, skipped = 0, False
        for h in self.app_windows():
            proc = self.process_name(h)
            if skip(h):
                skipped = skipped or proc in names
                continue
            if proc in names:
                return h
            if not front and proc and proc not in SHELL_PROCS:
                front = h
        return 0 if skipped else front

    def activate(self, h: int) -> bool:
        if user32.IsIconic(h):
            user32.ShowWindow(h, SW_RESTORE)
            time.sleep(0.3)
        if user32.SetForegroundWindow(h) and self.root(self.foreground()) == h:
            return True
        self.send(_vk_input(VK_MENU, False))
        try:
            user32.SetForegroundWindow(h)
        finally:
            self.send(_vk_input(VK_MENU, True))
        time.sleep(0.05)
        if self.root(self.foreground()) == h:
            return True
        fg_thread = user32.GetWindowThreadProcessId(self.foreground(), None)
        me = kernel32.GetCurrentThreadId()
        attached = fg_thread and fg_thread != me and user32.AttachThreadInput(me, fg_thread, True)
        try:
            user32.BringWindowToTop(h)
            user32.SetForegroundWindow(h)
        finally:
            if attached:
                user32.AttachThreadInput(me, fg_thread, False)
        time.sleep(0.05)
        return self.root(self.foreground()) == h

    def cursor(self) -> tuple:
        p = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(p))
        return p.x, p.y

    def move_to(self, x: int, y: int) -> None:
        vx, vy = user32.GetSystemMetrics(SM_XVIRTUALSCREEN), user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        vw = max(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN) - 1, 1)
        vh = max(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN) - 1, 1)
        nx, ny = ((x - vx) * 65535) // vw, ((y - vy) * 65535) // vh
        self.send(_mouse_flags(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, nx, ny))

    def click(self, ctrl: bool = False) -> None:
        """Linksklick mit menschlicher Haltedauer; mit ctrl=True als Strg+Klick (Link im Hintergrund-Tab)."""
        swapped = user32.GetSystemMetrics(SM_SWAPBUTTON)
        down, up = (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP) if swapped else (MOUSEEVENTF_LEFTDOWN,
                                                                                 MOUSEEVENTF_LEFTUP)
        if ctrl:
            self.send(_vk_input(0x11, False))
            time.sleep(0.08)
        try:
            self.send(_mouse_flags(down))
            time.sleep(0.05 + 0.07 * (time.perf_counter_ns() % 1000) / 1000)
            self.send(_mouse_flags(up))
        finally:
            if ctrl:
                time.sleep(0.06)
                self.send(_vk_input(0x11, True))

    def wheel(self, delta: int) -> None:
        self.send(_wheel(delta))

    def send_combo(self, vks: tuple) -> None:
        mods, key = vks[:-1], vks[-1]
        try:
            for vk in mods:
                self.send(_vk_input(vk, False))
                time.sleep(0.02)
            self.send(_vk_input(key, False))
            time.sleep(0.05)
            self.send(_vk_input(key, True))
        finally:
            for vk in reversed(mods):
                time.sleep(0.02)
                self.send(_vk_input(vk, True))

    def type_char(self, ch: str) -> None:
        units = ch.encode("utf-16-le")
        for i in range(0, len(units), 2):
            unit = chr(int.from_bytes(units[i:i + 2], "little"))
            self.send(_unicode_input(unit, False))
            time.sleep(0.01)
            self.send(_unicode_input(unit, True))
