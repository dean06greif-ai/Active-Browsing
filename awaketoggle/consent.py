"""Cookie-/Datenschutz-Hinweise: welcher Button ist „Alle akzeptieren“, welcher „Ablehnen“? (plattformunabhängig)"""

STRONG = ("alle akzeptieren", "alles akzeptieren", "alle cookies akzeptieren", "accept all", "accept all cookies",
          "allen zustimmen", "alle zulassen", "alle erlauben", "allow all", "alle annehmen", "alle cookies zulassen",
          "allow all cookies", "agree to all", "alle bestätigen", "alle cookies erlauben", "tout accepter",
          "alle accepteren", "accetta tutto", "aceptar todo")
ACCEPT = ("akzeptier", "accept", "zustimm", "stimme zu", "einverstanden", "zulassen", "erlauben", "annehmen",
          "agree", "allow", "consent", "bestätigen", "aceptar", "accett", "akceptuj", "zgadzam")
WEAK = ("ok", "okay", "verstanden", "ok, verstanden", "alles klar", "got it", "understood", "ok, alles klar")
NEGATIVE = ("ablehn", "reject", "decline", "deny", "verweiger", "nicht", "not ", "ohne", "without", "nur ", "only",
            "notwendig", "necessary", "essenziell", "essential", "einstellung", "setting", "anpass", "verwalt",
            "manage", "custom", "mehr", "more", "detail", "option", "präferenz", "preference", "speichern", "save",
            "abo", "subscribe", "benachrichtig", "notification", "standort", "location", "kamera", "camera",
            "mikrofon", "microphone", "widerruf", "datenschutzerklärung", "privacy policy")

DECLINE_STRONG = ("alle ablehnen", "ablehnen", "reject all", "reject", "decline", "decline all", "alle verweigern",
                  "nur notwendige", "nur notwendige cookies", "nur erforderliche", "nur erforderliche cookies",
                  "nur essenzielle", "nur essenzielle cookies", "nur technisch notwendige cookies", "only necessary",
                  "necessary only", "only essential", "essential only", "use necessary cookies only",
                  "nicht einverstanden", "nicht zustimmen", "weiter ohne zustimmung", "continue without accepting",
                  "ohne zustimmung fortfahren", "deny", "verweigern", "tout refuser", "rifiuta tutto")
DECLINE = ("ablehn", "reject", "decline", "deny", "verweiger", "nur notwendig", "nur erforderlich", "nur essenz",
           "nur technisch", "only necessary", "necessary only", "only essential", "essential only",
           "necessary cookies only", "without accept", "ohne zustimm", "ohne einwillig", "nicht einverstanden",
           "nicht zustimm", "nicht akzeptier", "refuser", "rifiut", "rechazar")
DECLINE_BAD = ("einstellung", "setting", "anpass", "verwalt", "manage", "custom", "mehr", "more", "detail", "option",
               "präferenz", "preference", "benachrichtig", "notification", "standort", "location", "abo", "subscribe",
               "partner", "anbieter", "vendor", "bezahl", "zahlen", "pay", "pur ", "datenschutzerklärung")
MAX_LEN = 50
SAME_BANNER_PX = 500  # Ablehnen-Button muss nah am Zustimmen-Button liegen (gleicher Hinweis)


def _norm(name: str) -> str:
    return " ".join((name or "").lower().split()).strip(" .!›>")


def accept_rank(name: str):
    """0 = „Alle akzeptieren“, 1 = „Akzeptieren“, 2 = „OK/Verstanden“, None = kein Zustimmungs-Button."""
    n = _norm(name)
    if not n or len(n) > MAX_LEN or any(w in n for w in NEGATIVE):
        return None
    if n in STRONG or (("alle" in n.split() or "all" in n.split()) and any(w in n for w in ACCEPT)):
        return 0
    if any(w in n for w in ACCEPT):
        return 1
    if n in WEAK:
        return 2
    return None


def decline_rank(name: str):
    """0 = „Alle ablehnen“/„Nur notwendige“, 1 = sonstige Ablehnung, None = kein Ablehnen-Button."""
    n = _norm(name)
    if not n or len(n) > MAX_LEN or any(w in n for w in DECLINE_BAD):
        return None
    if n in DECLINE_STRONG:
        return 0
    if any(w in n for w in DECLINE):
        return 1
    return None


def _best(buttons, rank):
    ranked = [(r, i, b) for i, b in enumerate(buttons) if (r := rank(b[0])) is not None]
    return min(ranked)[2] if ranked else None


def best_button(buttons):
    """buttons: [(Name, (l, t, r, b))] → bester Zustimmungs-Button (Name, Rechteck) oder None."""
    return _best(buttons, accept_rank)


def _middle_y(rect) -> float:
    return (rect[1] + rect[3]) / 2


def choose(buttons, decline: bool = False):
    """(Art, Name, Rechteck) mit Art „accept“ oder „decline“, oder None.

    Abgelehnt wird nur, wenn es im selben Hinweis auch einen echten Zustimmungs-Button gibt – sonst könnte
    „Ablehnen“ etwas ganz anderes sein. Ohne Ablehnen-Button wird zugestimmt.
    """
    accept = best_button(buttons)
    if not accept:
        return None
    if decline and accept_rank(accept[0]) <= 1:
        near = [b for b in buttons if abs(_middle_y(b[1]) - _middle_y(accept[1])) <= SAME_BANNER_PX]
        no = _best(near, decline_rank)
        if no:
            return ("decline", *no)
    return ("accept", *accept)
