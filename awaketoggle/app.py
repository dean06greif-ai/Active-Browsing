import atexit
import logging
import os
import signal
import sys
from dataclasses import asdict

from . import APP_NAME, __version__, config

MUTEX_NAME = "Local\\AwakeToggle.SingleInstance"
log = logging.getLogger("awaketoggle")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if sys.platform != "win32":
        print("AwakeToggle läuft nur unter Windows.", file=sys.stderr)
        return 2

    from . import win32
    if "--selftest" in argv:
        return win32.selftest()

    from .core import Engine
    from .logsetup import setup_logging
    from .session import SessionWatcher
    from .tray import TrayApp

    base = config.app_dir()
    base.mkdir(parents=True, exist_ok=True)
    cfg_path, log_path = base / "config.json", base / "awaketoggle.log"
    setup_logging(log_path)

    mutex = win32.acquire_single_instance(MUTEX_NAME)
    if mutex is None:
        log.info("Zweite Instanz gestartet, beende sie wieder")
        win32.message_box("AwakeToggle läuft bereits. Sie finden es im Infobereich der Taskleiste.", APP_NAME)
        return 0

    log.info("%s %s gestartet (PID %s)", APP_NAME, __version__, os.getpid())
    win32.set_dpi_aware()
    cfg, warnings = config.load(cfg_path)
    for w in warnings:
        log.warning(w)
    log.info("Konfiguration: %s", asdict(cfg))

    engine = Engine(win32.Win32Api(), cfg)
    tray = TrayApp(engine, cfg_path, log_path)

    def stop(reason: str) -> None:
        log.info("Beenden: %s", reason)
        engine.shutdown()
        tray.stop()

    session = SessionWatcher(on_lock_change=engine.set_session_locked,
                             on_end_session=lambda: stop("Abmelden/Herunterfahren (WM_ENDSESSION)"),
                             on_resume=engine.poke)
    atexit.register(engine.shutdown)
    for name in ("SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda s, f: stop(f"Signal {s}"))
    ctrl_handler = win32.set_console_ctrl_handler(lambda t: stop(f"Konsolenereignis {t}"))  # noqa: F841

    engine.start()
    session.start()
    if cfg.start_active:
        engine.set_active(True)
    try:
        tray.run()
    finally:
        engine.shutdown()
        session.stop()
        win32.close_handle(mutex)
        log.info("%s beendet", APP_NAME)
    return 0
