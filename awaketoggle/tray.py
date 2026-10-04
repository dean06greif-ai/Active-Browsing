import logging
import subprocess
import threading
from dataclasses import asdict, replace

import pystray
from pystray import Menu
from pystray import MenuItem as Item

from . import APP_NAME, autostart
from . import config as config_mod
from .config import BROWSE_LENGTH_CHOICES, INTERVAL_CHOICES, JITTER_CHOICES, TIMER_CHOICES, VARIANTS
from .core import Status
from .icons import make_icon
from .tray_labels import browse_length_label, interval_label, jitter_label, timer_label, tooltip

log = logging.getLogger(__name__)

SIGNAL_LABELS = {"mouse": "Maus (1 Pixel hin und zurück)", "f15": "Taste F15", "random": "Zufällig (Varianten wählbar)",
                 "browse": "Browser-Test (Suchen, Tabs, Fenster, Scrollen, Klicks)"}
VARIANT_MENU_LABELS = {"mouse": "Mausbewegung (kleiner Pfad, zurück zum Start)",
                       "scroll": "Scrollen (kurz hin und zurück)",
                       "keys": "Tippen (nur F13–F24, kein Text)"}


class TrayApp:
    def __init__(self, engine, cfg_path, log_path):
        self.engine = engine
        self.cfg_path = cfg_path
        self.log_path = log_path
        self.icon = pystray.Icon(APP_NAME, make_icon("off"), tooltip(engine.status), self._menu())
        engine.on_status = self._on_status

    def run(self) -> None:
        self.icon.run()

    def stop(self) -> None:
        self.icon.stop()

    def _cfg(self):
        return self.engine.config

    def _on_status(self, status: Status) -> None:
        try:
            self.icon.icon = make_icon(status.state)
            self.icon.title = tooltip(status)
            self.icon.update_menu()
            if status.reason == "timer":
                self._notify("Timer abgelaufen, AwakeToggle ist jetzt aus.")
        except Exception:
            log.exception("Tray-Symbol konnte nicht aktualisiert werden")

    def _notify(self, text: str) -> None:
        try:
            if self.icon.HAS_NOTIFICATION:
                self.icon.notify(text, APP_NAME)
        except Exception:
            log.exception("Benachrichtigung fehlgeschlagen")

    def _change(self, **changes) -> None:
        new = replace(self._cfg(), **changes)
        config_mod.save(new, self.cfg_path)
        self.engine.update_config(new)
        log.info("Einstellung geändert: %s", changes)
        self.icon.update_menu()

    def _toggle(self) -> None:
        self.engine.toggle()
        self.icon.update_menu()

    def _run_now(self) -> None:
        log.info("Jetzt testen über Tray-Menü")
        self.engine.run_now()
        self.icon.update_menu()

    def _ask_interval(self) -> None:
        cur = self._cfg().interval_seconds
        script = ("Add-Type -AssemblyName Microsoft.VisualBasic;"
                  f"[Microsoft.VisualBasic.Interaction]::InputBox('Abstand in Sekunden "
                  f"({config_mod.INTERVAL_MIN}-{config_mod.INTERVAL_MAX}):','{APP_NAME}','{cur}')")
        try:
            out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True,
                                 text=True, timeout=600, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
        except Exception:
            log.exception("Eingabefenster für Abstand fehlgeschlagen")
            return
        if not out:
            return
        try:
            sec = int(float(out.replace(",", ".")))
        except ValueError:
            sec = 0
        if not config_mod.INTERVAL_MIN <= sec <= config_mod.INTERVAL_MAX:
            self._notify(f"Ungültiger Abstand: {out} (erlaubt {config_mod.INTERVAL_MIN}-{config_mod.INTERVAL_MAX} s)")
            return
        self._change(interval_seconds=sec)

    def _toggle_autostart(self) -> None:
        try:
            if autostart.is_enabled():
                autostart.disable()
                log.info("Autostart ausgeschaltet")
            else:
                autostart.enable()
                log.info("Autostart eingeschaltet: %s", autostart.shortcut_path())
        except Exception as e:
            log.exception("Autostart konnte nicht geändert werden")
            self._notify(f"Autostart konnte nicht geändert werden: {e}")
        self.icon.update_menu()

    def _make_shortcuts(self) -> None:
        try:
            paths = autostart.create_desktop_and_startmenu()
            log.info("Verknüpfungen angelegt: %s", ", ".join(map(str, paths)))
            self._notify("Verknüpfung auf dem Desktop und im Startmenü angelegt.")
        except Exception as e:
            log.exception("Verknüpfungen konnten nicht angelegt werden")
            self._notify(f"Verknüpfung konnte nicht angelegt werden: {e}")

    def _reload(self) -> None:
        cfg, warnings = config_mod.load(self.cfg_path)
        for w in warnings:
            log.warning(w)
        self.engine.update_config(cfg)
        log.info("Konfiguration neu geladen: %s", asdict(cfg))
        self._notify("Konfiguration neu geladen" + (f" ({len(warnings)} Warnung(en), siehe Protokoll)" if warnings else "."))
        self.icon.update_menu()

    @staticmethod
    def _open(path) -> None:
        subprocess.Popen(["notepad.exe", str(path)])

    def _quit(self) -> None:
        log.info("Beenden über Tray-Menü")
        self.icon.stop()

    def _radio(self, label, key, value) -> Item:
        return Item(label, lambda: self._change(**{key: value}),
                    checked=lambda i: getattr(self._cfg(), key) == value, radio=True)

    def _toggle_variant(self, variant) -> None:
        current = self._cfg().random_variants
        if variant in current and len(current) == 1:
            self._notify("Mindestens eine Variante muss aktiv bleiben.")
            return
        new = tuple(v for v in VARIANTS if (v in current) != (v == variant))
        self._change(random_variants=new)

    def _variant(self, variant) -> Item:
        return Item(VARIANT_MENU_LABELS[variant], lambda: self._toggle_variant(variant),
                    checked=lambda i: variant in self._cfg().random_variants,
                    enabled=lambda i: self._cfg().signal == "random")

    def _custom(self, key, choices, label_fn) -> Item:
        return Item(lambda i: f"Eigener Wert: {label_fn(getattr(self._cfg(), key))} (config.json)",
                    lambda: None, checked=lambda i: True, radio=True, enabled=False,
                    visible=lambda i: getattr(self._cfg(), key) not in choices)

    def _menu(self) -> Menu:
        return Menu(
            Item("Aktiv", self._toggle, checked=lambda i: self.engine.active, default=True),
            Item(lambda i: self.engine.status.text, lambda: None, enabled=False),
            Item("Jetzt testen (sofort ausführen)", self._run_now),
            Menu.SEPARATOR,
            Item("Signal", Menu(*[self._radio(lbl, "signal", k) for k, lbl in SIGNAL_LABELS.items()],
                                Menu.SEPARATOR, *[self._variant(v) for v in VARIANTS])),
            Item("Erweiterungs-Zähler vorher/nachher lesen",
                 lambda: self._change(badge_read=not self._cfg().badge_read),
                 checked=lambda i: self._cfg().badge_read, enabled=lambda i: self._cfg().signal == "browse"),
            Item("Browser-Test Länge", Menu(*[self._radio(browse_length_label(n), "browse_actions_max", n)
                                              for n in BROWSE_LENGTH_CHOICES],
                                            self._custom("browse_actions_max", BROWSE_LENGTH_CHOICES,
                                                         browse_length_label)),
                 enabled=lambda i: self._cfg().signal == "browse"),
            Item("Abstand", Menu(*[self._radio(interval_label(s), "interval_seconds", s) for s in INTERVAL_CHOICES],
                                 self._custom("interval_seconds", INTERVAL_CHOICES, interval_label),
                                 Menu.SEPARATOR,
                                 Item("Eigener Wert eingeben …", lambda: threading.Thread(
                                     target=self._ask_interval, daemon=True).start()))),
            Item("Abstand variieren", Menu(*[self._radio(jitter_label(j), "jitter_percent", j) for j in JITTER_CHOICES],
                                           self._custom("jitter_percent", JITTER_CHOICES, jitter_label))),
            Item(lambda i: f"Weg-Modus: Helligkeit {self._cfg().away_brightness} % + Stromsparen, "
                           f"zurück: {self._cfg().back_brightness} %",
                 lambda: self._change(away_power=not self._cfg().away_power),
                 checked=lambda i: self._cfg().away_power),
            Item("Automatisch abschalten", Menu(*[self._radio(timer_label(h), "timer_hours", h) for h in TIMER_CHOICES],
                                                self._custom("timer_hours", TIMER_CHOICES, timer_label))),
            Menu.SEPARATOR,
            Item("Beim Programmstart aktivieren", lambda: self._change(start_active=not self._cfg().start_active),
                 checked=lambda i: self._cfg().start_active),
            Item("Mit Windows starten", self._toggle_autostart, checked=lambda i: autostart.is_enabled()),
            Item("Verknüpfung auf Desktop + Startmenü anlegen",
                 lambda: threading.Thread(target=self._make_shortcuts, daemon=True).start()),
            Item("Konfiguration öffnen", lambda: self._open(self.cfg_path)),
            Item("Konfiguration neu laden", self._reload),
            Item("Protokoll öffnen", lambda: self._open(self.log_path)),
            Menu.SEPARATOR,
            Item("Beenden", self._quit),
        )
