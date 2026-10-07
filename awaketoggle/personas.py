"""Browsing-Persönlichkeiten: Wer surft gerade? Jede hat Lieblingsthemen, Tempo, Lesedauer und Eigenheiten.

Die Persönlichkeiten wechseln sich ab – dieselbe kommt nicht gleich wieder dran (nicht unter den letzten drei).
Lieblingsthemen machen etwa zwei Drittel der Anliegen aus, der Rest ist bunt gemischt wie bei echten Menschen.
"""
import random
from collections import deque
from dataclasses import dataclass

from .queries import THEME_WEIGHTS

FAVORITE_BOOST = 6.0
OTHER_FACTOR = 0.35
ROTATION_MEMORY = 3


@dataclass(frozen=True)
class Persona:
    name: str
    themes: tuple = ()  # Lieblingsthemen (leer = alles gleich gern)
    styles: tuple = (2, 5, 1.5)  # Gewichte für ruhig, normal, hektisch
    curiosity: tuple = (0.1, 0.6)  # Neigung, Treffer in neuen Tabs zu öffnen
    reader: float = 1.0  # Lesedauer-Faktor
    decline: float = 0.12  # Anteil der Cookie-Hinweise, die abgelehnt werden („Nur notwendige“)
    sites: tuple = ()  # Lieblingsseiten für Strg+Enter (www.….com)

    @property
    def weights(self) -> dict:
        if not self.themes:
            return dict(THEME_WEIGHTS)
        return {t: w * (FAVORITE_BOOST if t in self.themes else OTHER_FACTOR) for t, w in THEME_WEIGHTS.items()}


ALLROUNDER = Persona("Allrounder")
PERSONAS = (
    ALLROUNDER,
    Persona("Technik-Nerd", ("technik", "programmieren", "gaming", "wissenschaft", "ki", "pc_bauen", "smartphone", "smarthome"), (1, 4, 3), (0.3, 0.7), 0.8,
            0.35, ("github", "stackoverflow", "microsoft")),
    Persona("Sportfan", ("fussball", "sport", "fitness", "fahrrad", "ernaehrung"), (1, 5, 2.5), (0.2, 0.6), 0.9, 0.1,
            ("espn", "transfermarkt")),
    Persona("Hobbykoch", ("rezept", "garten", "haushalt", "backen", "kaffee", "restaurant", "einkaufen"), (3, 5, 1), (0.1, 0.4), 1.3, 0.1, ("allrecipes",)),
    Persona("Reiselustige", ("urlaub", "fernreisen", "bahn", "wetter", "camping", "sprachen", "fotografie"), (2, 5, 1), (0.3, 0.7), 1.1, 0.12,
            ("booking", "tripadvisor", "airbnb")),
    Persona("Finanz-Fuchs", ("finanzen", "nachrichten", "job", "steuern", "versicherung", "krypto", "rente", "immobilien"), (1, 5, 2), (0.2, 0.5), 1.0, 0.25,
            ("investing", "bloomberg")),
    Persona("Gamer", ("gaming", "technik", "filme", "pc_bauen", "brettspiele"), (0.5, 4, 3), (0.3, 0.7), 0.7, 0.2,
            ("twitch", "steampowered", "ign")),
    Persona("Familienmensch", ("familie", "gesundheit", "haushalt", "tiere", "schule", "geschenke", "basteln"), (2, 5, 1.5), (0.1, 0.5), 1.0, 0.08,
            ("ikea", "amazon")),
    Persona("Studentin", ("wissen", "wissenschaft", "programmieren", "english", "rechnen", "studium", "wohnen", "sprachen"), (1.5, 5, 2), (0.3, 0.7),
            1.2, 0.25, ("wikipedia", "duolingo", "coursera")),
    Persona("Heimwerker", ("heimwerken", "garten", "auto", "energie", "smarthome", "motorrad"), (2.5, 5, 1), (0.1, 0.4), 1.2, 0.1, ("ikea", "youtube")),
    Persona("Nachrichtenleser", ("nachrichten", "wetter", "gesundheit", "behoerde", "recht", "rente", "geschichte"), (5, 3, 0.5), (0.05, 0.3), 1.5,
            0.05, ("bbc", "cnn")),
    Persona("Kulturfan", ("musik", "filme", "freizeit", "buecher", "fotografie"), (2, 5, 1.5), (0.2, 0.6), 1.1, 0.12,
            ("spotify", "imdb", "netflix")),
    Persona("Modebewusste", ("mode", "fitness", "freizeit", "beauty", "social_media", "einkaufen"), (1.5, 5, 2), (0.3, 0.7), 0.9, 0.15, ("zalando", "asos")),
)


class Rotation:
    """Wechselt die Persönlichkeit je Durchlauf, ohne kurz hintereinander dieselbe zu nehmen."""

    def __init__(self, personas=PERSONAS, memory: int = ROTATION_MEMORY):
        self.personas = personas
        self.recent = deque(maxlen=min(memory, len(personas) - 1))

    def next(self, rng: random.Random) -> Persona:
        options = [p for p in self.personas if p.name not in self.recent]
        p = rng.choice(options)
        self.recent.append(p.name)
        return p


_rotation = Rotation()


def next_persona(rng: random.Random) -> Persona:
    return _rotation.next(rng)
