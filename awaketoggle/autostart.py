"""Verknüpfungen: Autostart-Ordner (ohne Registry), Desktop und Startmenü."""
import os
import subprocess
import sys
from pathlib import Path

LNK_NAME = "AwakeToggle.lnk"
CREATE_NO_WINDOW = 0x08000000
_PS_SCRIPT = (
    "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:AT_LNK);"
    "$s.TargetPath=$env:AT_TARGET;$s.Arguments=$env:AT_ARGS;"
    "$s.WorkingDirectory=$env:AT_WORKDIR;$s.Description='AwakeToggle';"
    "if($env:AT_ICON){$s.IconLocation=$env:AT_ICON};$s.Save()"
)


def _programs() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def shortcut_path() -> Path:
    return _programs() / "Startup" / LNK_NAME


def startmenu_path() -> Path:
    return _programs() / LNK_NAME


def desktop_path() -> Path:
    """Echter Desktop-Ordner (auch wenn er per OneDrive umgeleitet ist)."""
    import ctypes
    buf = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0 and buf.value:
        return Path(buf.value) / LNK_NAME
    return Path(os.environ["USERPROFILE"]) / "Desktop" / LNK_NAME


def is_enabled() -> bool:
    return shortcut_path().exists()


def launch_command() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    script = Path(__file__).resolve().parent.parent / "main.py"
    return str(pyw if pyw.exists() else exe), f'"{script}"'


def _icon(target: str) -> str:
    if getattr(sys, "frozen", False):
        return f"{target},0"
    ico = Path(__file__).resolve().parent.parent / "build" / "awaketoggle.ico"
    return str(ico) if ico.exists() else ""


def create(lnk: Path) -> None:
    target, args = launch_command()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    workdir = str(Path(target).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent)
    env = {**os.environ, "AT_LNK": str(lnk), "AT_TARGET": target, "AT_ARGS": args,
           "AT_WORKDIR": workdir, "AT_ICON": _icon(target)}
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS_SCRIPT],
                   env=env, check=True, timeout=20, capture_output=True, creationflags=CREATE_NO_WINDOW)


def enable() -> None:
    create(shortcut_path())


def create_desktop_and_startmenu() -> list:
    paths = [desktop_path(), startmenu_path()]
    for p in paths:
        create(p)
    return paths


def disable() -> None:
    shortcut_path().unlink(missing_ok=True)
