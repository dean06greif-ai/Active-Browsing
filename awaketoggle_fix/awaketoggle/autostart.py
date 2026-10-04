"""Autostart über eine Verknüpfung im Autostart-Ordner des Benutzers (ohne Registry)."""
import os
import subprocess
import sys
from pathlib import Path

LNK_NAME = "AwakeToggle.lnk"
CREATE_NO_WINDOW = 0x08000000
_PS_SCRIPT = (
    "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:AT_LNK);"
    "$s.TargetPath=$env:AT_TARGET;$s.Arguments=$env:AT_ARGS;"
    "$s.WorkingDirectory=$env:AT_WORKDIR;$s.Description='AwakeToggle';$s.Save()"
)


def shortcut_path() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / LNK_NAME


def is_enabled() -> bool:
    return shortcut_path().exists()


def launch_command() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    script = Path(__file__).resolve().parent.parent / "main.py"
    return str(pyw if pyw.exists() else exe), f'"{script}"'


def enable() -> None:
    target, args = launch_command()
    lnk = shortcut_path()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "AT_LNK": str(lnk), "AT_TARGET": target, "AT_ARGS": args,
           "AT_WORKDIR": str(Path(target).parent)}
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PS_SCRIPT],
                   env=env, check=True, timeout=20, capture_output=True, creationflags=CREATE_NO_WINDOW)


def disable() -> None:
    shortcut_path().unlink(missing_ok=True)
