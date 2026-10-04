"""Zufällige Suchanfragen: Zahlen, Themen, Fragen, Rechnungen, Tippfehler."""
import random

TOPICS = (
    "wetter", "nachrichten", "fußball", "bundesliga", "rezept lasagne", "pizza teig", "bahn fahrplan",
    "flug berlin", "hotel münchen", "laptop", "smartphone", "kopfhörer", "fahrrad", "e-auto", "solaranlage",
    "wärmepumpe", "steuererklärung", "kindergeld", "urlaub ostsee", "mallorca", "kochen", "garten", "tomaten",
    "hund", "katze", "aquarium", "python programmieren", "excel formel", "windows update", "edge browser",
    "bitcoin kurs", "aktien", "dax", "gold preis", "benzinpreis", "strompreis", "mietvertrag", "kündigung",
    "bewerbung", "lebenslauf", "zahnarzt", "erkältung", "joggen", "yoga", "fitnessstudio", "kino", "serien",
    "netflix", "musik", "gitarre", "klavier", "schach", "sudoku", "kreuzworträtsel", "geschichte rom",
    "mond", "mars", "planeten", "vulkan", "erdbeben", "dinosaurier", "pyramiden", "eiffelturm", "zugspitze",
    "rhein", "bodensee", "hamburg hafen", "köln dom", "dresden", "wikipedia", "übersetzer", "duden",
)
TOPICS_EN = (
    "weather", "news", "recipe", "football", "laptop review", "best headphones", "python tutorial",
    "how to tie a tie", "space station", "world map", "translate", "time zones", "speed test",
)
QUESTIONS = (
    "was ist {t}", "wie funktioniert {t}", "warum {t}", "{t} in der nähe", "{t} test", "{t} vergleich",
    "beste {t} {y}", "{t} kaufen", "{t} erfahrungen", "{t} öffnungszeiten", "{t} bilder", "{t} preis",
    "wann {t}", "wo gibt es {t}", "{t} anleitung", "{t} heute", "{t} definition",
)
NUMBER_FORMS = (
    "{n}", "{n}", "{n}", "{n} {t}", "{t} {n}", "{a} + {b}", "{a} * {b}", "{a} - {b}", "{a} / {b}",
    "{n} km in meilen", "{n} euro in dollar", "{n} grad in fahrenheit", "{n} kg in pfund", "plz {p}",
    "wurzel aus {n}", "{n} quadrat", "ist {n} eine primzahl", "{n} in binär", "jahr {y2}", "{a}%",
)
COMMON_WORDS = ("der", "die", "und", "ist", "mit", "the", "and", "info", "news", "suche", "2026", "de")
SAFE_DOMAINS = ("wikipedia", "github", "microsoft", "bing", "duckduckgo", "youtube", "amazon",
                "stackoverflow", "mozilla", "apple", "google", "linkedin", "reddit")

QWERTZ_ROWS = ("1234567890ß", "qwertzuiopü", "asdfghjklöä", "yxcvbnm")


def neighbor(ch: str, rng: random.Random) -> str:
    low = ch.lower()
    for row in QWERTZ_ROWS:
        i = row.find(low)
        if i >= 0:
            options = [row[j] for j in (i - 1, i + 1) if 0 <= j < len(row)]
            return rng.choice(options)
    return ch


def typo(text: str, rng: random.Random) -> str:
    """Ein absichtlicher, nicht korrigierter Tippfehler (testet die Rechtschreibkorrektur der Suche)."""
    idx = [i for i, c in enumerate(text) if c.isalpha()]
    if len(idx) < 3:
        return text
    i = rng.choice(idx[1:])
    kind = rng.choice(("swap", "drop", "double", "neighbor"))
    if kind == "swap" and i + 1 < len(text):
        return text[:i] + text[i + 1] + text[i] + text[i + 2:]
    if kind == "drop":
        return text[:i] + text[i + 1:]
    if kind == "double":
        return text[:i] + text[i] + text[i:]
    return text[:i] + neighbor(text[i], rng) + text[i + 1:]


def _number(rng: random.Random) -> str:
    n = rng.choice((rng.randint(0, 99), rng.randint(100, 9999), rng.randint(10_000, 9_999_999)))
    return str(n)


def make_query(rng: random.Random) -> str:
    t = rng.choice(TOPICS)
    y = rng.randint(2019, 2027)
    roll = rng.random()
    if roll < 0.40:
        q = rng.choice(NUMBER_FORMS).format(
            n=_number(rng), t=t, a=rng.randint(2, 999), b=rng.randint(2, 99),
            p=f"{rng.randint(1000, 99999):05d}", y=y, y2=rng.randint(1000, 2100))
    elif roll < 0.75:
        q = rng.choice(QUESTIONS).format(t=t, y=y)
    elif roll < 0.85:
        q = rng.choice(TOPICS_EN) + rng.choice(("", f" {y}", f" {rng.randint(1, 99)}"))
    else:
        q = t
    if rng.random() < 0.15:
        q = typo(q, rng)
    if rng.random() < 0.1:
        q = q.capitalize()
    return q


def find_word(rng: random.Random, last_query: str = "") -> str:
    words = [w for w in last_query.split() if len(w) > 2]
    if words and rng.random() < 0.5:
        return rng.choice(words)
    return rng.choice(COMMON_WORDS)
