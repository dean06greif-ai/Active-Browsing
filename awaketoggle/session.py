"""Verstecktes Fenster für WM_ENDSESSION, Sperr-/Entsperr- und Energie-Ereignisse (nur Windows)."""
import ctypes
import logging
import threading
from ctypes import wintypes

from .win32 import kernel32, user32

log = logging.getLogger(__name__)

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_POWERBROADCAST = 0x0218
WM_WTSSESSION_CHANGE = 0x02B1
WTS_LOCKED_EVENTS = {2: "Konsole getrennt", 4: "RDP getrennt", 7: "gesperrt"}
WTS_UNLOCKED_EVENTS = {1: "Konsole verbunden", 3: "RDP verbunden", 8: "entsperrt"}
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
NOTIFY_FOR_THIS_SESSION = 0
CLASS_NAME = "AwakeToggleSessionWindow"

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)
wtsapi32.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
wtsapi32.WTSRegisterSessionNotification.restype = wintypes.BOOL
wtsapi32.WTSUnRegisterSessionNotification.argtypes = [wintypes.HWND]
wtsapi32.WTSUnRegisterSessionNotification.restype = wintypes.BOOL
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                   wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


class SessionWatcher:
    def __init__(self, on_lock_change, on_end_session, on_resume):
        self._on_lock_change = on_lock_change
        self._on_end_session = on_end_session
        self._on_resume = on_resume
        self._proc = WNDPROC(self._wndproc)
        self._hwnd = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="SessionWatcher", daemon=True)

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(5)

    def stop(self) -> None:
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
            self._thread.join(2)

    def _run(self) -> None:
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=hinst, lpszClassName=CLASS_NAME)
        try:
            if not user32.RegisterClassW(ctypes.byref(wc)):
                log.error("RegisterClassW fehlgeschlagen (%s)", ctypes.get_last_error())
                return
            self._hwnd = user32.CreateWindowExW(0, CLASS_NAME, "AwakeToggle", 0, 0, 0, 0, 0,
                                                None, None, hinst, None)
            if not self._hwnd:
                log.error("Verstecktes Fenster konnte nicht erstellt werden (%s)", ctypes.get_last_error())
                return
            if not wtsapi32.WTSRegisterSessionNotification(self._hwnd, NOTIFY_FOR_THIS_SESSION):
                log.warning("Sperr-Benachrichtigung nicht verfügbar, nutze nur Abfrage des Eingabedesktops")
        finally:
            self._ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        self._hwnd = None
        user32.UnregisterClassW(CLASS_NAME, hinst)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_WTSSESSION_CHANGE:
                if wparam in WTS_LOCKED_EVENTS:
                    log.info("Sitzungsereignis: %s", WTS_LOCKED_EVENTS[wparam])
                    self._on_lock_change(True)
                elif wparam in WTS_UNLOCKED_EVENTS:
                    log.info("Sitzungsereignis: %s", WTS_UNLOCKED_EVENTS[wparam])
                    self._on_lock_change(False)
                return 0
            if msg == WM_QUERYENDSESSION:
                return 1
            if msg == WM_ENDSESSION:
                if wparam:
                    self._on_end_session()
                return 0
            if msg == WM_POWERBROADCAST:
                if wparam == PBT_APMSUSPEND:
                    log.info("System geht in den Energiesparmodus")
                elif wparam in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC):
                    log.info("System aus dem Energiesparmodus aufgewacht")
                    self._on_resume()
                return 1
            if msg == WM_CLOSE:
                wtsapi32.WTSUnRegisterSessionNotification(hwnd)
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            log.exception("Fehler bei Fensternachricht 0x%04X", msg)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
