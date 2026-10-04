"""Helligkeit und Stromsparmodus unter Windows (ohne Administratorrechte).

Helligkeit: eingebaute Laptop-Anzeige über WMI (WmiMonitorBrightnessMethods), externe Monitore über DDC/CI (dxva2).
Stromsparen: Windows-Energiesparmodus (Schwelle ESBATTTHRESHOLD = 100 %) und Energiemodus „Beste Energieeffizienz“.
Der vorherige Zustand wird in away_state.json gesichert und beim nächsten Programmstart wiederhergestellt,
falls das Programm im Weg-Modus hart beendet wurde.
"""
import ctypes
import json
import logging
import os
import re
import subprocess
import uuid
from ctypes import wintypes
from pathlib import Path

log = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000
ES_ARGS = ("SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD")
OVERLAY_BEST_EFFICIENCY = "961cc777-2547-4f9d-8174-7d86181b8a7a"
_WMI_SCRIPT = ("Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods -ErrorAction Stop | "
               "Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{Timeout=1; Brightness=%d} "
               "-ErrorAction Stop | Out-Null")


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16), ("Data3", ctypes.c_uint16),
                ("Data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, text: str) -> "GUID":
        return cls.from_buffer_copy(uuid.UUID(text).bytes_le)

    def __str__(self) -> str:
        return str(uuid.UUID(bytes_le=bytes(self)))


class PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [("hPhysicalMonitor", wintypes.HANDLE), ("szPhysicalMonitorDescription", ctypes.c_wchar * 128)]


MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), MONITORENUMPROC, wintypes.LPARAM]
_user32.EnumDisplayMonitors.restype = wintypes.BOOL
try:
    _dxva2 = ctypes.WinDLL("dxva2")
    _dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, ctypes.POINTER(wintypes.DWORD)]
    _dxva2.GetPhysicalMonitorsFromHMONITOR.argtypes = [wintypes.HMONITOR, wintypes.DWORD,
                                                       ctypes.POINTER(PHYSICAL_MONITOR)]
    _dxva2.GetMonitorBrightness.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD),
                                            ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
    _dxva2.SetMonitorBrightness.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _dxva2.DestroyPhysicalMonitors.argtypes = [wintypes.DWORD, ctypes.POINTER(PHYSICAL_MONITOR)]
except OSError:
    _dxva2 = None
try:
    _powrprof = ctypes.WinDLL("powrprof")
    _powrprof.PowerGetEffectiveOverlayScheme.argtypes = [ctypes.POINTER(GUID)]
    _powrprof.PowerGetEffectiveOverlayScheme.restype = wintypes.DWORD
    _powrprof.PowerSetActiveOverlayScheme.argtypes = [GUID]
    _powrprof.PowerSetActiveOverlayScheme.restype = wintypes.DWORD
except (OSError, AttributeError):
    _powrprof = None


def _run(args, timeout=15) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, encoding="mbcs", errors="replace",
                          timeout=timeout, creationflags=CREATE_NO_WINDOW)


# ---------- Helligkeit ----------

def _ddc_brightness(percent: int) -> int:
    """Externe Monitore per DDC/CI; liefert die Anzahl erfolgreich gesetzter Monitore."""
    if not _dxva2:
        return 0
    monitors, ok = [], 0

    def cb(hmon, hdc, rect, lparam):
        monitors.append(hmon)
        return True
    _user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    for hmon in monitors:
        n = wintypes.DWORD()
        if not _dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmon, ctypes.byref(n)) or not n.value:
            continue
        arr = (PHYSICAL_MONITOR * n.value)()
        if not _dxva2.GetPhysicalMonitorsFromHMONITOR(hmon, n.value, arr):
            continue
        try:
            for pm in arr:
                lo, cur, hi = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
                if not _dxva2.GetMonitorBrightness(pm.hPhysicalMonitor, ctypes.byref(lo), ctypes.byref(cur),
                                                   ctypes.byref(hi)):
                    continue
                value = lo.value + (hi.value - lo.value) * percent // 100
                if _dxva2.SetMonitorBrightness(pm.hPhysicalMonitor, value):
                    ok += 1
        finally:
            _dxva2.DestroyPhysicalMonitors(n.value, arr)
    return ok


def _wmi_brightness(percent: int) -> bool:
    """Eingebaute Anzeige (Laptop/Tablet)."""
    try:
        r = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _WMI_SCRIPT % percent])
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def set_brightness(percent: int) -> str:
    percent = max(0, min(100, int(percent)))
    ddc = _ddc_brightness(percent)
    wmi = _wmi_brightness(percent)
    parts = ([f"{ddc} externe(r) Monitor(e)"] if ddc else []) + (["eingebaute Anzeige"] if wmi else [])
    if not parts:
        log.warning("Helligkeit %d %%: kein Monitor ließ sich einstellen (DDC/CI am Monitor aktivieren?)", percent)
        return "-"
    log.info("Helligkeit %d %%: %s", percent, ", ".join(parts))
    return ", ".join(parts)


# ---------- Stromsparen ----------

def read_energy_saver():
    """(AC, DC) der Energiesparmodus-Schwelle in Prozent oder None."""
    try:
        out = _run(["powercfg", "/query", *ES_ARGS]).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    values = re.findall(r":\s*0x([0-9a-fA-F]+)\s*$", out, re.MULTILINE)
    if len(values) < 2:
        return None
    return int(values[-2], 16), int(values[-1], 16)


def write_energy_saver(ac: int, dc: int) -> bool:
    ok = True
    for cmd, value in (("/setacvalueindex", ac), ("/setdcvalueindex", dc)):
        try:
            ok &= _run(["powercfg", cmd, *ES_ARGS, str(int(value))]).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
    try:
        ok &= _run(["powercfg", "/setactive", "SCHEME_CURRENT"]).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    return ok


def read_overlay():
    if not _powrprof:
        return None
    g = GUID()
    if _powrprof.PowerGetEffectiveOverlayScheme(ctypes.byref(g)) != 0:
        return None
    return str(g)


def write_overlay(text: str) -> bool:
    if not _powrprof or not text:
        return False
    return _powrprof.PowerSetActiveOverlayScheme(GUID.parse(text)) == 0


class Power:
    def __init__(self, state_path: Path):
        self.state_path = Path(state_path)

    def _save(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def _load(self):
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def dim(self, cfg) -> None:
        if cfg.away_energy_saver:
            if self._load() is None:
                es, overlay = read_energy_saver(), read_overlay()
                self._save({"es": list(es) if es else None, "overlay": overlay})
            ok_es = write_energy_saver(100, 100)
            ok_ov = write_overlay(OVERLAY_BEST_EFFICIENCY)
            log.info("Stromsparmodus an (Energiesparmodus: %s, Energiemodus beste Effizienz: %s)",
                     "ok" if ok_es else "fehlgeschlagen", "ok" if ok_ov else "nicht verfügbar")
        set_brightness(cfg.away_brightness)

    def restore(self, cfg) -> None:
        set_brightness(cfg.back_brightness)
        state = self._load()
        if state is None:
            return
        es = state.get("es")
        # Schwelle 100 % hieße „immer an“; war sie vorher schon so, auf den Windows-Standard 20 % setzen
        ac, dc = (es if es and max(es) < 100 else (0, 20))
        ok_es = write_energy_saver(ac, dc)
        ok_ov = write_overlay(state.get("overlay") or "00000000-0000-0000-0000-000000000000")
        log.info("Stromsparmodus aus (Energiesparmodus zurück auf %s/%s %%: %s, Energiemodus: %s)",
                 ac, dc, "ok" if ok_es else "fehlgeschlagen", "ok" if ok_ov else "nicht verfügbar")
        try:
            os.remove(self.state_path)
        except OSError:
            pass

    def recover(self, cfg) -> None:
        """Nach hartem Beenden im Weg-Modus beim Start alles zurücksetzen."""
        if self.state_path.exists():
            log.info("Weg-Modus war beim letzten Beenden noch an – setze Helligkeit/Stromsparen zurück")
            self.restore(cfg)
