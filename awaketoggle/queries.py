"""Menschliche Suchanfragen (rund 70 Themen): Interessen mit rotem Faden (Startanfrage, Verfeinerungen, verwandte Fragen).

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
    "backen": (("käsekuchen rezept", "brot backen ohne hefe", "zimtschnecken rezept", "apfelkuchen blech",
                "sauerteig ansetzen", "muffins grundrezept", "plätzchen rezepte"),
               ("{q} einfach", "{q} ohne zucker", "{q} vegan", "{q} wie lange backen", "{q} umluft", "{q} saftig"),
               ("springform größe umrechnen", "backpulver ersatz", "kuchen fällt zusammen warum", "teig geht nicht auf")),
    "kaffee": (("siebträger test", "kaffeevollautomat entkalken", "beste kaffeebohnen", "cold brew selber machen",
                "french press anleitung", "espresso mahlgrad"),
               ("{q} {y}", "{q} anleitung", "{q} unter 300 euro", "{q} vergleich", "{q} fehler"),
               ("koffein wirkung wie lange", "milchschaum ohne aufschäumer", "matcha latte rezept")),
    "smartphone": (("iphone akku tauschen kosten", "samsung galaxy vergleich", "handy speicher voll",
                    "beste handy kamera {y}", "smartphone unter 300 euro", "android update funktioniert nicht"),
                   ("{q} lösung", "{q} test", "{q} erfahrungen", "{q} reddit", "{q} vergleich", "{q} {y}"),
                   ("handyvertrag vergleich", "esim einrichten", "whatsapp backup wiederherstellen",
                    "displayschutzfolie anbringen")),
    "smarthome": (("smart home einsteiger", "thermostat smart test", "alexa routinen", "home assistant einrichten",
                   "smarte steckdose stromverbrauch", "saugroboter test {y}"),
                  ("{q} anleitung", "{q} vergleich", "{q} erfahrungen", "{q} ohne cloud", "{q} kosten"),
                  ("zigbee oder wlan", "matter standard erklärt", "überwachungskamera außen test")),
    "pc_bauen": (("gaming pc zusammenstellen", "grafikkarte einbauen", "netzteil berechnen", "ssd einbauen anleitung",
                  "cpu kühler montieren", "pc startet nicht"),
                 ("{q} {y}", "{q} anfänger", "{q} unter 1000 euro", "{q} reddit", "{q} fehler", "{q} video"),
                 ("bios update risiko", "wärmeleitpaste wie viel", "ram kompatibilität prüfen",
                  "windows neu installieren usb")),
    "ki": (("chatgpt kostenlos", "ki bilder erstellen", "künstliche intelligenz einfach erklärt", "ki tools {y}",
            "prompt schreiben tipps", "ki texte erkennen"),
           ("{q} deutsch", "{q} beispiele", "{q} vergleich", "{q} für anfänger", "{q} datenschutz"),
           ("ki im job", "neuronale netze erklärt", "ki gesetz eu")),
    "social_media": (("instagram story löschen", "tiktok algorithmus", "whatsapp status ausblenden",
                      "youtube kanal starten", "instagram account gehackt", "linkedin profil tipps"),
                     ("{q} anleitung", "{q} {y}", "{q} tipps", "{q} geht nicht", "{q} iphone"),
                     ("bildschirmzeit reduzieren", "social media pause", "reels schneiden app")),
    "versicherung": (("haftpflichtversicherung vergleich", "hausratversicherung was ist versichert",
                      "kfz versicherung wechseln", "berufsunfähigkeitsversicherung sinnvoll", "zahnzusatzversicherung test"),
                     ("{q} {y}", "{q} kosten", "{q} test", "{q} kündigen", "{q} erfahrungen"),
                     ("versicherungen die man braucht", "rechtsschutz lohnt sich", "schadensfreiheitsklasse tabelle")),
    "steuern": (("steuererklärung selber machen", "homeoffice pauschale {y}", "werbungskosten absetzen",
                 "steuerklasse wechseln", "steuer id vergessen", "pendlerpauschale berechnen"),
                ("{q} {y}", "{q} elster", "{q} beispiel", "{q} frist", "{q} tipps"),
                ("steuerrückzahlung wie lange", "lohnsteuerhilfeverein kosten", "steuer app test")),
    "wohnen": (("wohnung mieten {c}", "mietspiegel {c}", "nebenkostenabrechnung prüfen", "kaution zurück wie lange",
                "wg zimmer {c}", "schufa auskunft kostenlos"),
               ("{q} {y}", "{q} tipps", "{q} günstig", "{q} erfahrungen", "{q} frist"),
               ("mieterhöhung zulässig", "wohnungsbesichtigung fragen", "einbauküche übernehmen ablöse")),
    "immobilien": (("haus kaufen {c}", "baufinanzierung zinsen", "eigentumswohnung kaufen checkliste",
                    "grunderwerbsteuer {c}", "fertighaus kosten", "notarkosten hauskauf"),
                   ("{q} {y}", "{q} rechner", "{q} erfahrungen", "{q} tipps", "{q} aktuell"),
                   ("tilgung berechnen", "eigenkapital wie viel", "gutachter haus kosten")),
    "umzug": (("umzug checkliste", "umzugskarton wie viele", "umzugsfirma {c}", "ummelden {c}",
               "nachsendeauftrag post", "transporter mieten {c}"),
              ("{q} kosten", "{q} tipps", "{q} pdf", "{q} frist", "{q} günstig"),
              ("umzug steuerlich absetzen", "internet umziehen", "strom ummelden umzug")),
    "energie": (("solaranlage kosten", "balkonkraftwerk anmelden", "wärmepumpe altbau", "stromverbrauch senken",
                 "gaspreis aktuell", "heizkosten sparen"),
                ("{q} {y}", "{q} erfahrungen", "{q} förderung", "{q} lohnt sich", "{q} rechner"),
                ("stromanbieter wechseln", "dynamischer stromtarif", "dämmung kosten pro qm")),
    "fahrrad": (("e-bike test {y}", "fahrradkette ölen", "fahrrad schlauch wechseln", "rennrad für anfänger",
                 "fahrradtour {c}", "gravelbike oder trekkingrad"),
                ("{q} anleitung", "{q} kosten", "{q} vergleich", "{q} video", "{q} tipps"),
                ("fahrradschloss test", "ebike akku reichweite", "radweg karte {c}")),
    "camping": (("campingplatz ostsee", "dachzelt test", "wohnmobil mieten", "camping ausrüstung liste",
                 "wildcampen deutschland erlaubt", "camping kocher test"),
                ("{q} {y}", "{q} günstig", "{q} mit hund", "{q} erfahrungen", "{q} tipps"),
                ("schlafsack temperatur", "campingplatz italien", "stellplatz app")),
    "wandern": (("wandern {c} umgebung", "wanderschuhe test", "zugspitze wandern", "rheinsteig etappen",
                 "harz wanderung", "jakobsweg planen"),
                ("{q} karte", "{q} schwierigkeit", "{q} mit kindern", "{q} tipps", "{q} rundweg"),
                ("wanderapp kostenlos", "blasen vorbeugen wandern", "hüttenwanderung alpen")),
    "angeln": (("angelschein machen", "angeln für anfänger", "forellen angeln", "angelplätze {c}",
                "karpfen köder", "spinnfischen hecht"),
               ("{q} tipps", "{q} kosten", "{q} ausrüstung", "{q} jahreszeit", "{q} video"),
               ("schonzeiten fische", "angelknoten anleitung", "fisch ausnehmen")),
    "fotografie": (("spiegelreflex oder systemkamera", "fotografieren lernen", "handy fotos bearbeiten",
                    "blende verschlusszeit iso", "objektiv für portraits", "sternenhimmel fotografieren"),
                   ("{q} anfänger", "{q} tipps", "{q} einstellungen", "{q} {y}", "{q} beispiele"),
                   ("lightroom alternative kostenlos", "fotobuch erstellen", "goldener schnitt")),
    "buecher": (("bestseller {y}", "spiegel bestseller liste", "bücher wie harry potter", "krimi empfehlung",
                 "hörbuch kostenlos", "fantasy bücher erwachsene"),
                ("{q} empfehlung", "{q} rezension", "{q} reihenfolge", "{q} taschenbuch", "{q} hörbuch"),
                ("ebook reader test", "bibliothek {c} onleihe", "lesezirkel gründen")),
    "geschichte": (("zweiter weltkrieg zusammenfassung", "römisches reich untergang", "mauerfall 1989",
                    "französische revolution ursachen", "mittelalter alltag", "kalter krieg einfach erklärt"),
                   ("{q} einfach erklärt", "{q} doku", "{q} zeitstrahl", "{q} wikipedia", "{q} buch"),
                   ("museum {c}", "burgen deutschland", "geschichte podcast")),
    "sprachen": (("englisch lernen kostenlos", "spanisch für anfänger", "duolingo erfahrungen",
                  "französisch vokabeln", "italienisch lernen app", "englisch b2 test"),
                 ("{q} app", "{q} schnell", "{q} online", "{q} tipps", "{q} pdf"),
                 ("übersetzer deutsch englisch", "sprachreise erwachsene", "vhs sprachkurs {c}")),
    "schule": (("mathe nachhilfe online", "bruchrechnen erklärt", "ferien {y}", "schulranzen test",
                "abitur durchschnitt berechnen", "referat tipps"),
               ("{q} klasse 5", "{q} übungen", "{q} einfach", "{q} pdf", "{q} video"),
               ("lernplattform kostenlos", "schulbücher digital", "konzentration lernen tipps")),
    "studium": (("bafög rechner", "studiengang finden", "hausarbeit gliederung", "zitieren apa",
                 "nc {c} uni", "wg oder wohnheim"),
                ("{q} {y}", "{q} beispiel", "{q} tipps", "{q} vorlage", "{q} erfahrungen"),
                ("semesterbeitrag {c}", "studentenjob {c}", "masterarbeit zeitplan")),
    "hochzeit": (("hochzeit planen checkliste", "hochzeitslocation {c}", "hochzeitskleid trends {y}",
                  "standesamt {c} termin", "hochzeitsrede beispiele", "hochzeit kosten durchschnitt"),
                 ("{q} {y}", "{q} günstig", "{q} ideen", "{q} tipps", "{q} pdf"),
                 ("trauzeuge aufgaben", "eheringe gold oder platin", "flitterwochen ziele")),
    "geschenke": (("geschenk freundin", "geschenkideen mann", "geschenk 18 geburtstag", "wichtelgeschenk unter 10 euro",
                   "geschenk für eltern", "last minute geschenk"),
                  ("{q} ideen", "{q} selber machen", "{q} {y}", "{q} günstig", "{q} besonders"),
                  ("gutschein selbst gestalten", "geschenk verpacken ohne papier", "erlebnisgeschenke {c}")),
    "einkaufen": (("angebote diese woche", "lidl prospekt", "black friday {y}", "amazon prime day", "dm angebote",
                   "media markt angebote"),
                  ("{q} heute", "{q} online", "{q} gutschein", "{q} {c}"),
                  ("preisvergleich", "rückgaberecht online", "öffnungszeiten sonntag {c}")),
    "restaurant": (("restaurant {c}", "italiener {c}", "sushi {c}", "frühstück {c}", "brunch {c} sonntag",
                    "lieferdienst {c}"),
                   ("{q} bewertungen", "{q} speisekarte", "{q} reservieren", "{q} günstig", "{q} offen"),
                   ("trinkgeld wie viel", "vegane restaurants {c}", "rooftop bar {c}")),
    "ernaehrung": (("intervallfasten 16 8", "eiweiß lebensmittel", "gesund abnehmen", "vitamin d mangel",
                    "low carb rezepte", "zucker reduzieren tipps"),
                   ("{q} plan", "{q} erfahrungen", "{q} tabelle", "{q} studie", "{q} wie viel"),
                   ("kalorientabelle", "meal prep ideen", "smoothie rezepte")),
    "psychologie": (("stress abbauen", "einschlafen tipps", "burnout anzeichen", "meditation anfänger",
                     "prokrastination überwinden", "selbstbewusstsein stärken"),
                    ("{q} übungen", "{q} schnell", "{q} tipps", "{q} buch", "{q} app"),
                    ("achtsamkeit übungen", "therapeut finden {c}", "work life balance")),
    "beauty": (("hautpflege routine", "haare färben zuhause", "sonnencreme test", "pickel loswerden",
                "nagellack trends {y}", "frisuren mittellang"),
               ("{q} tipps", "{q} test", "{q} drogerie", "{q} männer", "{q} {y}"),
               ("retinol wirkung", "friseur {c}", "naturkosmetik marken")),
    "zimmerpflanzen": (("monstera pflege", "zimmerpflanzen pflegeleicht", "orchidee gießen", "pflanzen umtopfen",
                        "trauermücken bekämpfen", "pflanzen für dunkle räume"),
                       ("{q} tipps", "{q} gelbe blätter", "{q} wie oft", "{q} erde", "{q} fehler"),
                       ("pflanzenlampe test", "ableger ziehen", "giftige pflanzen katzen")),
    "basteln": (("basteln mit kindern", "makramee anleitung", "kerzen selber machen", "stricken lernen",
                 "nähmaschine für anfänger", "diy deko ideen"),
                ("{q} anleitung", "{q} video", "{q} einfach", "{q} material", "{q} ideen"),
                ("bastelladen {c}", "häkeln muster kostenlos", "upcycling ideen")),
    "motorrad": (("motorradführerschein kosten", "a2 motorrad", "motorrad touren {c}", "motorradhelm test",
                  "motorrad winterfest machen", "125er für anfänger"),
                 ("{q} {y}", "{q} tipps", "{q} vergleich", "{q} erfahrungen", "{q} gebraucht"),
                 ("motorrad versicherung", "kurventechnik", "motorradtreffen {y}")),
    "recht": (("widerruf online kauf", "kündigung handyvertrag", "mietminderung schimmel", "abmahnung arbeitgeber",
               "erbrecht pflichtteil", "garantie oder gewährleistung"),
              ("{q} muster", "{q} frist", "{q} {y}", "{q} anwalt", "{q} vorlage"),
              ("verbraucherzentrale {c}", "rechtsberatung kostenlos", "fahrverbot einspruch")),
    "rente": (("rente berechnen", "rentenbescheid verstehen", "private altersvorsorge", "riester kündigen",
               "rente mit 63", "betriebsrente steuer"),
              ("{q} {y}", "{q} rechner", "{q} tabelle", "{q} lohnt sich", "{q} erfahrungen"),
              ("rentenerhöhung {y}", "rentenpunkte kaufen", "witwenrente höhe")),
    "brettspiele": (("brettspiele für 2", "spiel des jahres {y}", "catan regeln", "kartenspiele für erwachsene",
                     "kooperative brettspiele", "schach lernen"),
                    ("{q} regeln", "{q} test", "{q} empfehlung", "{q} erweiterung", "{q} video"),
                    ("spielwarenladen {c}", "puzzle 1000 teile", "kniffel regeln")),
    "nachhaltigkeit": (("plastik vermeiden tipps", "secondhand online", "mülltrennung richtig", "co2 fußabdruck rechner",
                        "nachhaltig leben", "regionale lebensmittel {c}"),
                       ("{q} tipps", "{q} alltag", "{q} beispiele", "{q} {y}", "{q} einfach"),
                       ("unverpackt laden {c}", "reparieren statt wegwerfen", "fairtrade siegel")),
    "krypto": (("ethereum kurs", "bitcoin kaufen", "krypto steuer", "krypto wallet sicher", "bitcoin halving",
                "solana prognose"),
               ("{q} aktuell", "{q} {y}", "{q} anfänger", "{q} erfahrungen", "{q} prognose"),
               ("krypto börse vergleich", "blockchain einfach erklärt", "stablecoin erklärt")),
}
THEME_WEIGHTS = {"wetter": 3, "rezept": 2, "fussball": 2, "bahn": 1.5, "urlaub": 1.5, "technik": 2.5, "finanzen": 1.2,
                 "gesundheit": 1.2, "haushalt": 1.2, "garten": 0.8, "wissen": 1.5, "freizeit": 1.2, "job": 0.8,
                 "behoerde": 1, "auto": 1, "tiere": 0.8, "programmieren": 1, "english": 0.8, "rechnen": 2, "zahl": 1,
                 "gaming": 1.3, "sport": 1.3, "musik": 1, "filme": 1.3, "fitness": 1, "mode": 0.9, "heimwerken": 1,
                 "familie": 0.9, "nachrichten": 1.5, "wissenschaft": 0.9, "fernreisen": 1,
                 "backen": 1, "kaffee": 0.7, "smartphone": 1.4, "smarthome": 0.8, "pc_bauen": 0.8, "ki": 1.2,
                 "social_media": 1, "versicherung": 0.8, "steuern": 1, "wohnen": 1, "immobilien": 0.8, "umzug": 0.6,
                 "energie": 1, "fahrrad": 0.9, "camping": 0.7, "wandern": 0.8, "angeln": 0.5, "fotografie": 0.7,
                 "buecher": 0.9, "geschichte": 0.8, "sprachen": 0.8, "schule": 0.8, "studium": 0.7, "hochzeit": 0.4,
                 "geschenke": 0.9, "einkaufen": 1.3, "restaurant": 1.1, "ernaehrung": 1, "psychologie": 0.8,
                 "beauty": 0.8, "zimmerpflanzen": 0.6, "basteln": 0.6, "motorrad": 0.5, "recht": 0.8, "rente": 0.6,
                 "brettspiele": 0.6, "nachhaltigkeit": 0.6, "krypto": 0.8}

# Verwandte Themen: dahin springt man, wenn ein Anliegen erledigt ist (roter Faden über mehrere Themen)
RELATED = {
    "wetter": ("urlaub", "garten", "freizeit", "wandern", "camping"), "rezept": ("backen", "ernaehrung", "einkaufen", "kaffee"),
    "fussball": ("sport", "nachrichten", "gaming"), "bahn": ("urlaub", "umzug", "wetter", "job"),
    "urlaub": ("fernreisen", "bahn", "wetter", "camping", "restaurant"), "technik": ("smartphone", "pc_bauen", "smarthome", "ki"),
    "finanzen": ("krypto", "rente", "steuern", "immobilien", "versicherung"), "gesundheit": ("ernaehrung", "fitness", "psychologie"),
    "haushalt": ("nachhaltigkeit", "heimwerken", "zimmerpflanzen", "energie"), "garten": ("zimmerpflanzen", "heimwerken", "wetter"),
    "wissen": ("geschichte", "wissenschaft", "sprachen"), "freizeit": ("restaurant", "filme", "musik", "brettspiele"),
    "job": ("steuern", "recht", "studium", "rente"), "behoerde": ("steuern", "umzug", "recht", "auto"),
    "auto": ("versicherung", "motorrad", "energie"), "tiere": ("familie", "wandern", "zimmerpflanzen"),
    "programmieren": ("ki", "pc_bauen", "technik"), "english": ("sprachen", "programmieren", "technik"),
    "rechnen": ("finanzen", "schule", "wissen"), "zahl": ("wissen", "rechnen"),
    "gaming": ("pc_bauen", "filme", "technik"), "sport": ("fussball", "fitness", "fahrrad"),
    "musik": ("freizeit", "filme", "buecher"), "filme": ("buecher", "musik", "freizeit"),
    "fitness": ("ernaehrung", "sport", "fahrrad", "wandern"), "mode": ("beauty", "einkaufen", "nachhaltigkeit"),
    "heimwerken": ("energie", "basteln", "garten", "smarthome"), "familie": ("schule", "geschenke", "tiere", "brettspiele"),
    "nachrichten": ("finanzen", "wetter", "geschichte"), "wissenschaft": ("ki", "wissen", "geschichte"),
    "fernreisen": ("urlaub", "sprachen", "fotografie"), "backen": ("rezept", "kaffee", "ernaehrung"),
    "kaffee": ("backen", "rezept", "restaurant"), "smartphone": ("technik", "social_media", "fotografie"),
    "smarthome": ("energie", "technik", "heimwerken"), "pc_bauen": ("gaming", "technik", "programmieren"),
    "ki": ("programmieren", "wissenschaft", "technik"), "social_media": ("smartphone", "fotografie", "beauty"),
    "versicherung": ("finanzen", "auto", "recht"), "steuern": ("finanzen", "job", "rente"),
    "wohnen": ("umzug", "immobilien", "recht", "energie"), "immobilien": ("finanzen", "wohnen", "energie"),
    "umzug": ("wohnen", "behoerde", "heimwerken"), "energie": ("smarthome", "immobilien", "nachhaltigkeit"),
    "fahrrad": ("wandern", "fitness", "sport"), "camping": ("wandern", "urlaub", "wetter", "angeln"),
    "wandern": ("camping", "wetter", "fotografie", "fahrrad"), "angeln": ("camping", "wetter", "wandern"),
    "fotografie": ("fernreisen", "smartphone", "wandern"), "buecher": ("filme", "geschichte", "sprachen"),
    "geschichte": ("buecher", "wissen", "fernreisen"), "sprachen": ("fernreisen", "studium", "english"),
    "schule": ("familie", "studium", "rechnen"), "studium": ("job", "wohnen", "sprachen"),
    "hochzeit": ("geschenke", "restaurant", "beauty", "fernreisen"), "geschenke": ("einkaufen", "basteln", "familie"),
    "einkaufen": ("geschenke", "mode", "rezept"), "restaurant": ("freizeit", "rezept", "kaffee"),
    "ernaehrung": ("fitness", "rezept", "gesundheit"), "psychologie": ("gesundheit", "buecher", "fitness"),
    "beauty": ("mode", "gesundheit", "einkaufen"), "zimmerpflanzen": ("garten", "haushalt", "tiere"),
    "basteln": ("geschenke", "familie", "heimwerken"), "motorrad": ("auto", "versicherung", "wandern"),
    "recht": ("wohnen", "job", "versicherung"), "rente": ("finanzen", "steuern", "versicherung"),
    "brettspiele": ("familie", "freizeit", "gaming"), "nachhaltigkeit": ("energie", "haushalt", "mode"),
    "krypto": ("finanzen", "steuern", "technik"),
}
NO_GENERIC = frozenset({"rechnen", "zahl", "english"})
GENERIC_REFINES = ("{q} erfahrungen", "{q} worauf achten", "{q} forum", "{q} vor und nachteile", "{q} tipps",
                   "{q} {y}", "{q} video", "{q} test", "was ist besser {q}", "{q} vergleich")

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


def related_theme(theme: str, rng: random.Random) -> str:
    """Verwandtes Thema für den nächsten Schritt (z. B. wandern → camping); sonst irgendein Thema."""
    options = [t for t in RELATED.get(theme, ()) if t in THEMES]
    return rng.choice(options) if options else rng.choice(tuple(THEMES))


class Interest:
    """Ein Anliegen mit rotem Faden: erste Anfrage, dann aufeinander aufbauende Verfeinerungen und verwandte Fragen.

    budget = so viele Suchen bleibt man ungefähr bei diesem Anliegen (danach exhausted)."""

    def __init__(self, rng: random.Random, theme: str = "", weights: dict = None, city: str = "", budget: int = 4):
        self.rng = rng
        weights = weights or THEME_WEIGHTS
        self.theme = theme or rng.choices(tuple(weights), tuple(weights.values()))[0]
        self.city = city or rng.choice(CITIES)
        self.query = ""
        self.anchor = ""  # Bezug für Verfeinerungen; baut sich mit jeder Verfeinerung weiter auf
        self.searches = 0
        self.budget = budget
        self.used = set()
        self.root = ""  # erste Anfrage: der Kern des Anliegens

    def _fresh(self, make, tries=6):
        """Neue, in diesem Anliegen noch nicht gesuchte Anfrage; None wenn keine gefunden."""
        for _ in range(tries):
            q = " ".join(dict.fromkeys(make().split()))
            if q not in self.used:
                return q
        return None

    def _take(self, q):
        self.used.add(q)
        self.query = q
        self.searches += 1
        return q

    def _related(self):
        return self._fresh(lambda: _fill(self.rng.choice(THEMES[self.theme][2]), self.rng, city=self.city))

    def _refined(self, base):
        pool = GENERIC_REFINES if self.theme not in NO_GENERIC and self.rng.random() < 0.2 else THEMES[self.theme][1]
        return self._fresh(lambda: _fill(self.rng.choice(pool), self.rng, q=base, city=self.city), tries=10)

    def first(self) -> str:
        starts = THEMES[self.theme][0]
        q = self._fresh(lambda: _fill(self.rng.choice(starts), self.rng, city=self.city), tries=10)
        q = q or self._refined(self.root or _fill(self.rng.choice(starts), self.rng, city=self.city))
        self.anchor = self._take(q or _fill(self.rng.choice(starts), self.rng, city=self.city))
        self.root = self.root or self.anchor
        return _humanize(self.query, self.rng)

    def again(self) -> str:
        """Neue Suche im selben Anliegen (z. B. in einem neuen Tab): anderer Einstieg ins gleiche Thema."""
        q = self._related() if self.rng.random() < 0.5 else None
        if q is None:
            return self.first()
        self.anchor = self._take(q)
        return _humanize(self.query, self.rng)

    def next(self) -> str:
        """Verfeinern (meist, baut auf der letzten Anfrage auf) oder zu einer verwandten Frage springen.
        Ist die Anfrage schon lang, fängt man wieder beim Kern an und verfeinert anders."""
        base = self.anchor.split(" = ")[0]
        if len(base) >= 45:
            base = self.root.split(" = ")[0]
        refine = self.rng.random() < 0.65
        q = self._refined(base) if refine else self._related()
        if q is None:
            refine = not refine
            q = self._refined(base) if refine else self._related()
        if q is None:
            refine, q = True, self._refined(self.root.split(" = ")[0])
        if q is None:
            return self.first()
        self._take(q)
        if refine or self.rng.random() < 0.4:
            self.anchor = q  # verwandte Frage wird manchmal zum neuen Faden, auf dem weiter aufgebaut wird
        return _humanize(self.query, self.rng)

    @property
    def exhausted(self) -> bool:
        return self.searches >= self.budget


def make_query(rng: random.Random, weights: dict = None) -> str:
    return Interest(rng, weights=weights).first()


def find_word(rng: random.Random, last_query: str = "") -> str:
    words = [w for w in last_query.split() if len(w) > 2 and not w.isdigit()]
    if words and rng.random() < 0.8:
        return rng.choice(words)
    return rng.choice(COMMON_WORDS)
