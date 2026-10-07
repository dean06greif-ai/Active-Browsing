import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

MAX_BYTES = 512 * 1024
BACKUPS = 1


def setup_logging(path) -> None:
    """Rotierendes Protokoll: aktuelle Datei + 1 Sicherung, zusammen höchstens 1 MB."""
    handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s [%(threadName)s] %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    crash = logging.getLogger("awaketoggle.crash")
    sys.excepthook = lambda t, v, tb: crash.critical("Unbehandelter Fehler", exc_info=(t, v, tb))
    threading.excepthook = lambda a: crash.critical(
        "Unbehandelter Fehler im Thread %s", a.thread.name if a.thread else "?",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
