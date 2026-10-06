"""Menschliche Suchanfragen (rund 30 Themen): Interessen mit rotem Faden (Startanfrage, Verfeinerungen, verwandte Fragen).

Ein Mensch sucht selten völlig zusammenhanglos. Er hat ein Anliegen („Wetter fürs Wochenende“), sucht,
verfeinert („… morgen“, „… regenradar“), springt zu Verwandtem und wechselt irgendwann das Thema.
Zahlen kommen so vor, wie Menschen sie tippen: Umrechnungen, Rechnungen, Postleitzahlen, Jahre.
"""
import random

CITIES = ("berlin", "hamburg", "münchen", "köln", "frankfurt", "stuttgart", "leipzig", "dresden", "hannover",
          "nürnberg", "bremen", "dortmund", "essen", "düsseldorf", "bonn", "münster", "freiburg", "kiel",
          "rostock", "erfurt", "mainz", "augsburg", "regensburg", "potsdam")
TEAMS = ("bayern", "dortmund", "leverkusen", "leipzig", "stuttgart", "frankfurt", "freiburg", "gladbach",
         "wolfsburg", "bremen", "union berlin", "hsv", "schalke", "köln", "mainz", "hoffenheim")

# Thema: (Startanfragen, Verfeinerungen mit {q} = bisherige Anfrage, verwandte neue Anfragen)
THEMES = {
    "wetter": (("wetter {c}", "wetter morgen", "wetter {c} wochenende"),
               ("{q} morgen", "{q} 14 tage", "{q} stündlich", "regenradar {c}", "{q} regen"),
               ("unwetterwarnung {c}", "pollenflug {c}", "sonnenaufgang {c}")),
    "rezept": (("lasagne rezept", "pizzateig rezept", "kürbissuppe", "bananenbrot rezept", "gulasch rezept",
                "pfannkuchen rezept", "spaghetti carbonara original", "linsensuppe"),
               ("{q} einfach", "{q} vegetarisch", "{q} ohne ei", "{q} chefkoch", "{q} schnell", "{q} kalorien"),
               ("wie lange hält gekochter reis", "backofen umluft oder ober unterhitze", "hefe ersatz")),
    "fussball": (("bundesliga tabelle", "{t} ergebnis", "{t} gegen {t2}", "bundesliga spieltag {n2}"),
                 ("{q} live", "{q} aufstellung", "{q} highlights", "{q} heute"),
                 ("champions league auslosung", "transfermarkt {t}", "dfb pokal ergebnisse")),
    "bahn": (("zug {c} {c2}", "db fahrplan", "deutschlandticket"),
             ("{q} heute", "{q} verspätung", "{q} preis", "{q} sparpreis"),
             ("bahn streik aktuell", "fahrgastrechte entschädigung", "bahncard 25 lohnt sich")),
    "urlaub": (("ferienwohnung ostsee", "hotel {c}", "{c} sehenswürdigkeiten", "flug mallorca", "urlaub mit hund"),
               ("{q} günstig", "{q} {y}", "{q} bewertungen", "{q} last minute"),
               ("reisepass beantragen dauer", "auslandskrankenversicherung", "koffer handgepäck maße")),
    "technik": (("laptop test {y}", "beste kopfhörer {y}", "handy akku schnell leer", "wlan langsam was tun",
                 "windows 11 update probleme", "drucker offline"),
                ("{q} lösung", "{q} reddit", "{q} unter 500 euro", "{q} vergleich"),
                ("router neu starten", "speedtest", "bluetooth verbindet nicht")),
    "finanzen": (("dax aktuell", "bitcoin kurs", "etf sparplan", "goldpreis", "strompreis vergleich"),
                 ("{q} heute", "{q} prognose", "{q} erfahrungen", "{q} {y}"),
                 ("zinsen tagesgeld", "inflation aktuell", "brutto netto rechner")),
    "gesundheit": (("erkältung hausmittel", "kopfschmerzen ursachen", "zahnarzt {c}", "rückenschmerzen übungen",
                    "schlafen besser"),
                   ("{q} schnell", "{q} was hilft", "{q} wann zum arzt"),
                   ("hausarzt {c} notdienst", "apotheke notdienst {c}")),
    "haushalt": (("schimmel entfernen", "waschmaschine riecht", "kalk entfernen wasserkocher", "fenster putzen",
                  "heizung entlüften"),
                 ("{q} hausmittel", "{q} anleitung", "{q} essig"),
                 ("backpulver putzen", "abfluss verstopft")),
    "garten": (("tomaten pflanzen", "rasen vertikutieren", "hortensien schneiden", "hochbeet anlegen"),
               ("{q} wann", "{q} anleitung", "{q} fehler"),
               ("mondkalender garten {y}", "schnecken bekämpfen")),
    "wissen": (("wie hoch ist die zugspitze", "wann wurde der kölner dom gebaut", "wie weit ist der mond",
                "wer hat das telefon erfunden", "hauptstadt australien", "wie alt wurden dinosaurier",
                "warum ist der himmel blau"),
               ("{q} wikipedia", "{q} einfach erklärt"),
               ("größter planet", "tiefster punkt der erde", "längster fluss europa")),
    "freizeit": (("kino {c}", "neue serien netflix", "tatort heute", "{c} veranstaltungen wochenende",
                  "konzerte {c} {y}"),
                 ("{q} programm", "{q} tickets", "{q} heute abend"),
                 ("spieleabend ideen", "escape room {c}")),
    "job": (("bewerbung anschreiben", "lebenslauf vorlage", "kündigungsfrist arbeitsvertrag", "urlaubsanspruch"),
            ("{q} muster", "{q} {y}", "{q} tipps"),
            ("brutto netto rechner", "minijob grenze {y}")),
    "behoerde": (("personalausweis beantragen", "steuererklärung frist {y}", "kindergeld {y}",
                  "kfz zulassung {c}", "wohngeld antrag"),
                 ("{q} {c}", "{q} online", "{q} termin", "{q} kosten"),
                 ("elster login", "bürgeramt {c} termin")),
    "auto": (("e-auto reichweite", "reifenwechsel wann", "benzinpreis {c}", "tüv kosten", "auto verkaufen"),
             ("{q} {y}", "{q} tipps", "{q} vergleich"),
             ("tankstelle in der nähe", "ladesäule {c}")),
    "tiere": (("hund zieht an der leine", "katze frisst nicht", "aquarium einrichten", "welpen erziehung"),
              ("{q} was tun", "{q} tipps", "{q} tierarzt"),
              ("tierarzt notdienst {c}", "hundefutter test")),
    "programmieren": (("python liste sortieren", "excel sverweis", "excel prozent formel", "git branch löschen",
                       "css flexbox zentrieren"),
                      ("{q} beispiel", "{q} stackoverflow", "{q} fehler"),
                      ("python dictionary", "excel datum formatieren")),
    "english": (("weather {c}", "python tutorial", "how to tie a tie", "best headphones {y}", "world map"),
                ("{q} reddit", "{q} for beginners", "{q} {y}"),
                ("time zones", "speed test")),
    "rechnen": (("{a} * {b}", "{a} + {b}", "{n} km in meilen", "{n} euro in dollar", "{n} grad fahrenheit in celsius",
                 "{p} prozent von {n}", "plz {c}", "{n} tage in wochen", "wurzel aus {n}"),
                ("{q} rechner", "{q} = ?"),
                ("prozentrechner", "taschenrechner", "{n} in binär")),
    "zahl": (("{n}", "{plz}", "{y2}", "{n} {t}"),
             ("{q} bedeutung", "{q} wikipedia"),
             ("{n}",)),
    "gaming": (("ps5 angebote", "gta 6 release", "minecraft seeds {y}", "beste pc spiele {y}", "elden ring boss guide",
                "nintendo switch 2 spiele", "steam sale {y}", "ea fc {y} tipps"),
               ("{q} reddit", "{q} test", "{q} preis", "{q} gameplay", "{q} tipps"),
               ("gaming headset test", "grafikkarte vergleich {y}", "twitch streamer deutschland", "ping zu hoch was tun")),
    "sport": (("formel 1 ergebnis", "nba ergebnisse", "tennis wimbledon {y}", "handball em {y}",
               "tour de france etappe {n2}", "olympia medaillenspiegel", "darts wm {y}"),
              ("{q} live", "{q} heute", "{q} highlights", "{q} tabelle"),
              ("sportschau live stream", "marathon {c} {y}", "formel 1 kalender {y}")),
    "musik": (("konzerte {c}", "charts deutschland", "gitarre lernen", "songtext bohemian rhapsody",
               "spotify playlist workout", "festival {y} line up"),
              ("{q} tickets", "{q} {y}", "{q} akkorde", "{q} für anfänger"),
              ("spotify wrapped", "plattenspieler test", "musikschule {c}")),
    "filme": (("neue filme kino", "beste serien {y}", "netflix neu diesen monat", "oscar gewinner {y}",
               "film tipps wochenende", "disney plus neuheiten"),
              ("{q} trailer", "{q} kritik", "{q} besetzung", "{q} staffel 2"),
              ("imdb top 250", "kino {c} programm", "streaming dienste vergleich")),
    "fitness": (("trainingsplan anfänger", "joggen abnehmen", "proteinpulver test", "fitnessstudio {c}",
                 "yoga für anfänger", "liegestütze richtig"),
                ("{q} zuhause", "{q} plan", "{q} tipps", "{q} wie oft"),
                ("kalorienbedarf berechnen", "muskelkater was hilft", "schritte pro tag gesund")),
    "mode": (("sneaker trends {y}", "winterjacke damen", "jeans herren slim fit", "kleidergröße umrechnen",
              "zalando gutschein"),
             ("{q} günstig", "{q} sale", "{q} test", "{q} kombinieren"),
             ("flecken aus jeans entfernen", "wolle waschen temperatur", "secondhand kleidung online")),
    "heimwerken": (("bohrmaschine test", "laminat verlegen", "wand streichen anleitung", "silikonfuge erneuern",
                    "dübel richtig setzen", "regal selber bauen"),
                   ("{q} anleitung", "{q} video", "{q} kosten", "{q} fehler"),
                   ("baumarkt {c} öffnungszeiten", "akkuschrauber vergleich", "tapete entfernen")),
    "familie": (("kita {c}", "elterngeld rechner", "kindergeburtstag ideen", "spielplatz {c}", "babybrei rezept",
                 "ausflugsziele mit kindern {c}"),
                ("{q} tipps", "{q} {y}", "{q} ab 3 jahren", "{q} antrag"),
                ("kinderarzt {c} notdienst", "schulferien {y}", "brettspiele für kinder")),
    "nachrichten": (("nachrichten heute", "tagesschau", "nachrichten {c}", "bundestag aktuell", "umfrage bundestagswahl",
                     "börse nachrichten"),
                    ("{q} live", "{q} aktuell", "{q} zusammenfassung"),
                    ("wetterwarnung deutschland", "verkehr {c} aktuell", "lokalnachrichten {c}")),
    "wissenschaft": (("james webb teleskop bilder", "mars mission {y}", "wie entsteht ein schwarzes loch",
                      "klimawandel fakten", "ki einfach erklärt", "sonnenfinsternis {y}", "quantencomputer erklärt"),
                     ("{q} einfach erklärt", "{q} neueste erkenntnisse", "{q} doku"),
                     ("iss live sehen", "planetarium {c}", "sternschnuppen {y}")),
    "fernreisen": (("thailand rundreise", "new york tipps", "japan reisezeit", "flug bali günstig", "kanada roadtrip",
                    "island ringstraße"),
                   ("{q} {y}", "{q} kosten", "{q} erfahrungen", "{q} 2 wochen"),
                   ("visum usa esta", "impfungen thailand", "reiseadapter japan")),
}
THEME_WEIGHTS = {"wetter": 3, "rezept": 2, "fussball": 2, "bahn": 1.5, "urlaub": 1.5, "technik": 2.5, "finanzen": 1.2,
                 "gesundheit": 1.2, "haushalt": 1.2, "garten": 0.8, "wissen": 1.5, "freizeit": 1.2, "job": 0.8,
                 "behoerde": 1, "auto": 1, "tiere": 0.8, "programmieren": 1, "english": 0.8, "rechnen": 2, "zahl": 1,
                 "gaming": 1.3, "sport": 1.3, "musik": 1, "filme": 1.3, "fitness": 1, "mode": 0.9, "heimwerken": 1,
                 "familie": 0.9, "nachrichten": 1.5, "wissenschaft": 0.9, "fernreisen": 1}

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


def _fill(template: str, rng: random.Random, q: str = "", city: str = "") -> str:
    c = city or rng.choice(CITIES)
    t, t2 = rng.sample(TEAMS, 2)
    n = rng.choice((rng.randint(2, 99), rng.randint(100, 999), rng.randint(1000, 99999)))
    return template.format(
        q=q, c=c, c2=rng.choice([x for x in CITIES if x != c]), t=t, t2=t2, y=rng.randint(2024, 2027),
        n=n, n2=rng.randint(1, 34), a=rng.randint(2, 999), b=rng.randint(2, 99), p=rng.choice((5, 10, 15, 19, 20, 25)),
        plz=f"{rng.randint(1067, 99998):05d}", y2=rng.randint(1800, 2030))


def _humanize(q: str, rng: random.Random) -> str:
    if rng.random() < 0.12:
        q = typo(q, rng)
    if rng.random() < 0.06:
        q = q.capitalize()
    return q


class Interest:
    """Ein Anliegen mit rotem Faden: erste Anfrage, dann Verfeinerungen und verwandte Fragen."""

    def __init__(self, rng: random.Random, theme: str = "", weights: dict = None):
        self.rng = rng
        weights = weights or THEME_WEIGHTS
        self.theme = theme or rng.choices(tuple(weights), tuple(weights.values()))[0]
        self.city = rng.choice(CITIES)
        self.query = ""
        self.anchor = ""  # Bezug für Verfeinerungen; verwandte Sprünge ändern ihn nicht
        self.searches = 0

    def first(self) -> str:
        starts = THEMES[self.theme][0]
        self.query = self.anchor = _fill(self.rng.choice(starts), self.rng, city=self.city)
        self.searches = 1
        return _humanize(self.query, self.rng)

    def next(self) -> str:
        """Verfeinern (meist) oder zu einer verwandten Frage springen."""
        _, refines, related = THEMES[self.theme]
        base = self.anchor.split(" = ")[0]
        for _ in range(5):
            refine = self.rng.random() < 0.65 and len(base) < 45
            if refine:
                q = _fill(self.rng.choice(refines), self.rng, q=base, city=self.city)
            else:
                q = _fill(self.rng.choice(related), self.rng, city=self.city)
            q = " ".join(dict.fromkeys(q.split()))
            if q != self.query:
                break
        self.query = q
        if refine:
            self.anchor = q
        self.searches += 1
        return _humanize(self.query, self.rng)

    @property
    def exhausted(self) -> bool:
        return self.searches >= 4


def make_query(rng: random.Random, weights: dict = None) -> str:
    return Interest(rng, weights=weights).first()


def find_word(rng: random.Random, last_query: str = "") -> str:
    words = [w for w in last_query.split() if len(w) > 2 and not w.isdigit()]
    if words and rng.random() < 0.8:
        return rng.choice(words)
    return rng.choice(COMMON_WORDS)
