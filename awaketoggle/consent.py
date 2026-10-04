"""Cookie-/Datenschutz-Hinweise: welcher Button ist „Alle akzeptieren“? (plattformunabhängig, testbar)"""

STRONG = ("alle akzeptieren", "alles akzeptieren", "alle cookies akzeptieren", "accept all", "accept all cookies",
          "allen zustimmen", "alle zulassen", "alle erlauben", "allow all", "alle annehmen", "alle cookies zulassen",
          "allow all cookies", "agree to all", "alle bestätigen")
ACCEPT = ("akzeptier", "accept", "zustimm", "stimme zu", "einverstanden", "zulassen", "erlauben", "annehmen",
          "agree", "allow", "consent", "bestätigen")
WEAK = ("ok", "okay", "verstanden", "ok, verstanden", "alles klar", "got it", "understood")
NEGATIVE = ("ablehn", "reject", "decline", "deny", "verweiger", "nicht", "not ", "ohne", "without", "nur ", "only",
            "notwendig", "necessary", "essenziell", "essential", "einstellung", "setting", "anpass", "verwalt",
            "manage", "custom", "mehr", "more", "detail", "option", "präferenz", "preference", "speichern", "save",
            "abo", "subscribe", "benachrichtig", "notification", "standort", "location", "kamera", "camera",
            "mikrofon", "microphone", "widerruf", "lesen", "read", "datenschutzerklärung", "privacy policy")
MAX_LEN = 50


def accept_rank(name: str):
    """0 = „Alle akzeptieren“, 1 = „Akzeptieren“, 2 = „OK/Verstanden“, None = kein Zustimmungs-Button."""
    n = " ".join((name or "").lower().split()).strip(" .!›>")
    if not n or len(n) > MAX_LEN or any(w in n for w in NEGATIVE):
        return None
    if n in STRONG or (("alle" in n.split() or "all" in n.split()) and any(w in n for w in ACCEPT)):
        return 0
    if any(w in n for w in ACCEPT):
        return 1
    if n in WEAK:
        return 2
    return None


def best_button(buttons):
    """buttons: [(Name, (l, t, r, b))] → bester (Name, Rechteck) oder None."""
    ranked = [(r, i, b) for i, b in enumerate(buttons) if (r := accept_rank(b[0])) is not None]
    return min(ranked)[2] if ranked else None
