# -*- coding: utf-8 -*-
"""Konfiguration for Teatermonitor.

Alle brugerindstillinger ligger i config.json ved siden af denne fil.
Hemmeligheder (API-nøgle / SMTP-kode) læses KUN fra miljøvariabler eller
.env — de skrives aldrig i config.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROT = Path(__file__).resolve().parent
STATE_DIR = ROT / "state"
UDBAKKE_DIR = ROT / "udbakke"

# ---------------------------------------------------------------------------
# Standardindstillinger. Overskrives af config.json.
# ---------------------------------------------------------------------------
STANDARD = {
    # Modtager(e) af digesten
    "modtagere": [],
    "afsender": "",
    "afsender_navn": "Teatermonitor",

    # "brevo" | "smtp" | "ingen" (skriv kun HTML-fil til udbakke/)
    "afsendelse": "ingen",
    "smtp_vaert": "",
    "smtp_port": 587,
    "smtp_bruger": "",

    # Geografi. Kultunauts egne områdenavne — se OMRAADER nedenfor.
    # Kernen vægtes højest i digesten.
    "kerne_kommuner": ["Silkeborg", "Aarhus"],
    "oevrige_kommuner": [
        "Skanderborg", "Favrskov", "Randers", "Horsens",
        "Odder", "Syddjurs", "Norddjurs", "Hedensted", "Viborg",
    ],

    # Længere væk — herfra medtages KUN store forestillinger
    # (musicals, store turnéopsætninger, de store teaterhuse).
    "rejse_kommuner": ["Kolding", "Vejle", "Fredericia", "Herning", "Billund"],

    # Aldersinteresse. Et arrangement tages med hvis dets aldersinterval
    # overlapper med dette.
    "alder_fra": 4,
    "alder_til": 12,

    # Hvor langt frem digesten kigger. En hel sæson: teatrene offentliggør
    # programmet længe før, og de populære juleforestillinger bliver udsolgt.
    "horisont_dage": 365,

    # Mindste relevanspoint for at komme med. Hæv for skarpere digest.
    "minimum_point": 60,

    # Maks antal poster pr. afsnit i mailen
    "maks_pr_afsnit": 25,

    # Tag arrangementer med uden oplyst alder, hvis de ellers ser
    # børnerelevante ud (genre/nøgleord).
    "medtag_uden_alder": True,

    # Vis klub-/foreningsafsnittet i hver digest (ellers kun 1. i måneden)
    "klubber_hver_gang": False,
}

HEMMELIGHEDER = {
    "brevo_api_noegle": ("BREVO_API_KEY", "TEATERMONITOR_BREVO_KEY"),
    "smtp_kode": ("TEATERMONITOR_SMTP_KODE", "SMTP_PASSWORD"),
}

# Mailadresser holdes UDE af config.json, så repoet kan være offentligt
# uden at udstille private adresser. Sættes som miljøvariabler/secrets.
# Flere modtagere adskilles med komma.
ADRESSE_MILJOE = {
    "modtagere": "TEATERMONITOR_MODTAGERE",
    "afsender": "TEATERMONITOR_AFSENDER",
}

# Kultunauts gyldige områdeværdier (aflæst direkte fra deres egen dropdown).
OMRAADER = {
    "Aarhus": "Aarhus-storkommune",
    "Silkeborg": "Silkeborg-storkommune",
    "Randers": "Randers-storkommune",
    "Horsens": "Horsens-storkommune",
    "Skanderborg": "Skanderborg-storkommune",
    "Favrskov": "Favrskov-storkommune",
    "Odder": "Odder-storkommune",
    "Syddjurs": "Syddjurs-storkommune",
    "Norddjurs": "Norddjurs-storkommune",
    "Hedensted": "Hedensted-storkommune",
    "Viborg": "Viborg-storkommune",
    "Samsoe": "Samsø-storkommune",
    "Herning": "Herning-storkommune",
    "Ikast-Brande": "Ikast-Brande-storkommune",
    # Rejsedistance — kun store forestillinger hentes herfra
    "Kolding": "Kolding-storkommune",
    "Vejle": "Vejle-storkommune",
    "Fredericia": "Fredericia-storkommune",
    "Billund": "Billund-storkommune",
    "Esbjerg": "Esbjerg-storkommune",
    "Odense": "Odense-storkommune",
    "Aalborg": "Aalborg-storkommune",
}

# Kultunaut-genrer der er relevante. "Børneteater" er deres egen kategori og
# rammer plet; de øvrige hentes også og filtreres bagefter på alder/nøgleord.
# "Baby/barsel" er bevidst udeladt — babysalmesang, rytmik og legestue er
# ikke det, digesten skal handle om.
GENRER_SIKRE = ["Børneteater", "For børn"]
GENRER_BREDE = ["Teater", "Dans", "Musical", "Anden forestilling", "Show/stand up"]


def _laes_dotenv() -> None:
    """Læs .env ind i miljøet, hvis filen findes. Simpelt KEY=VALUE-format."""
    env = ROT / ".env"
    if not env.exists():
        return
    for linje in env.read_text(encoding="utf-8").splitlines():
        linje = linje.strip()
        if not linje or linje.startswith("#") or "=" not in linje:
            continue
        noegle, _, vaerdi = linje.partition("=")
        os.environ.setdefault(noegle.strip(), vaerdi.strip().strip('"').strip("'"))


def hent_hemmelighed(navn: str) -> str:
    """Slå en hemmelighed op i miljøet. Returnerer tom streng hvis den mangler."""
    for miljoenavn in HEMMELIGHEDER.get(navn, ()):
        vaerdi = os.environ.get(miljoenavn)
        if vaerdi:
            return vaerdi
    return ""


def indlaes() -> dict:
    """Returnér den samlede konfiguration."""
    _laes_dotenv()
    conf = dict(STANDARD)
    sti = ROT / "config.json"
    if sti.exists():
        conf.update(json.loads(sti.read_text(encoding="utf-8")))

    # Mailadresser fra miljøet vinder over config.json
    if os.environ.get(ADRESSE_MILJOE["modtagere"]):
        conf["modtagere"] = [m.strip() for m
                             in os.environ[ADRESSE_MILJOE["modtagere"]].split(",")
                             if m.strip()]
    if os.environ.get(ADRESSE_MILJOE["afsender"]):
        conf["afsender"] = os.environ[ADRESSE_MILJOE["afsender"]].strip()

    ukendte = [k for k in (conf["kerne_kommuner"] + conf["oevrige_kommuner"]
                           + conf.get("rejse_kommuner", []))
               if k not in OMRAADER]
    if ukendte:
        raise SystemExit(
            f"Ukendt(e) kommune(r) i config.json: {', '.join(ukendte)}.\n"
            f"Gyldige: {', '.join(sorted(OMRAADER))}"
        )

    STATE_DIR.mkdir(exist_ok=True)
    UDBAKKE_DIR.mkdir(exist_ok=True)
    return conf
