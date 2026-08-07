# -*- coding: utf-8 -*-
"""Klubber, teaterforeninger og medlemsordninger.

To dele:
  * KURATERET — manuelt verificerede ordninger med priser og fordele.
    Hver post har 'verificeret'-dato, så det er synligt hvornår tallene
    sidst er tjekket ved kilden.
  * Dynamisk opslag i Kultunauts foreningsregister, så nye foreninger
    i området dukker op af sig selv.
"""
from __future__ import annotations

from config import OMRAADER
from kultunaut import hent_foreninger

VERIFICERET = "2026-08-07"

# ---------------------------------------------------------------------------
# Kuraterede ordninger. 'boernevaerdi' = hvor meget den gavner børneteater
# konkret (høj/middel/lav) — ikke hvor god ordningen er i al almindelighed.
# ---------------------------------------------------------------------------
KURATEREDE = [
    {
        "navn": "Børneteaterklubben – Silkeborg Teater",
        "kommune": "Silkeborg",
        "pris": "5 kr. (fornyes automatisk årligt, kan opsiges)",
        "fordele": [
            "Sæsonprogrammet på e-mail INDEN billetsalget åbner",
            "Nyhedsbrev ca. en gang om måneden",
        ],
        "forbehold": "Giver ikke længere rabat på billetter til børne- "
                     "og familieteater — værdien er den tidlige besked.",
        "boernevaerdi": "høj",
        "hvorfor": "Billigste og mest direkte adgang til børneprogrammet i "
                   "Silkeborg. De populære forestillinger (især jul) sælges "
                   "ofte hurtigt, så tidlig besked er hele pointen.",
        "link": "https://www.silkeborgteater.dk/page-13/index.html",
        "verificeret": VERIFICERET,
    },
    {
        "navn": "Medlemskab – Silkeborg Teater",
        "kommune": "Silkeborg",
        "pris": "100 kr. enlige / 200 kr. familie (sæson 2026-27)",
        "fordele": [
            "30 % rabat på billetter (2 personer ved familiemedlemskab)",
            "Billetbooking ca. 1. maj — før offentligheden",
            "Gratis garderobe i store sal",
            "Elektronisk sæsonprogram før offentlig lancering",
        ],
        "forbehold": "Rabatten gælder teatrets forestillinger bredt. Børn og "
                     "unge under 25 får i forvejen 100 kr. i rabat uanset "
                     "medlemskab, så gevinsten er mindst på de billige "
                     "børnebilletter (70-100 kr.).",
        "boernevaerdi": "middel",
        "hvorfor": "Bedst hvis I også ser voksenforestillinger. Den tidlige "
                   "booking er værd at have.",
        "link": "https://jmts.dk/program/medlem/",
        "verificeret": VERIFICERET,
    },
    {
        "navn": "Abonnement / sæsonkort – Teatret Gruppe 38",
        "kommune": "Aarhus",
        "pris": "Børn/unge op til 18 år 70 kr. · abonnement (min. 3 "
                "forestillinger) 95 kr. · sæsonkort 550 kr.",
        "fordele": [
            "Fast lav billetpris for børn",
            "Abonnementsprisen gælder resten af sæsonen efter køb af 3",
            "'Kaffe-kage-teater' 150 kr. — forestilling med kage og kaffe",
        ],
        "forbehold": "Sæsonkortet for 2026-27 stod som UDSOLGT ved tjek.",
        "boernevaerdi": "høj",
        "hvorfor": "Gruppe 38 er et af landets stærkeste børneteatre, og "
                   "børnebilletten er billig i forvejen.",
        "link": "https://www.gruppe38.dk/billetpriser/",
        "verificeret": VERIFICERET,
    },
    {
        "navn": "Sæsonkort – Aarhus Teater",
        "kommune": "Aarhus",
        "pris": "100 kr.",
        "fordele": ["10 % rabat på billetter"],
        "forbehold": "Rabatten gælder UDTRYKKELIGT ikke små børneforestillinger "
                     "og ekstra arrangementer.",
        "boernevaerdi": "lav",
        "hvorfor": "Ringe værdi hvis formålet er børneteater. Kun relevant "
                   "hvis I også går i teatret som voksne.",
        "link": "https://www.aarhusteater.dk/dit-besoeg/rabat",
        "verificeret": VERIFICERET,
    },
    {
        "navn": "Medlemskort – Teatret Svalegangen",
        "kommune": "Aarhus",
        "pris": "Ikke oplyst online — kontakt billetkontoret",
        "fordele": ["Oplyst rabat på alle forestillinger"],
        "forbehold": "Prisen kunne ikke verificeres på deres side ved tjek. "
                     "Svalegangen spiller primært voksenteater.",
        "boernevaerdi": "lav",
        "hvorfor": "Medtaget for fuldstændighedens skyld.",
        "link": "https://www.svalegangen.dk/priser/abonnement/",
        "verificeret": VERIFICERET,
    },
]

# Foreningstyper vi henter dynamisk fra Kultunaut
FORENINGSTYPER = ["Teaterforening", "Børne/ungdomsorganisation"]


def hent_dynamiske(kommuner: list[str], log=print) -> dict[str, list[dict]]:
    """Slå foreninger op i Kultunaut for de valgte kommuner."""
    ud: dict[str, list[dict]] = {}
    kendte = {k["navn"].lower() for k in KURATEREDE}
    for kommune in kommuner:
        omraade = OMRAADER.get(kommune)
        if not omraade:
            continue
        fundne = []
        for stedtype in FORENINGSTYPER:
            for f in hent_foreninger(omraade, stedtype):
                if f["navn"].lower() in kendte:
                    continue
                f["type"] = stedtype
                fundne.append(f)
        if fundne:
            ud[kommune] = fundne
            log(f"  Foreninger {kommune:<12} {len(fundne)} fundet")
    return ud


def anbefalinger(kommuner: list[str]) -> list[dict]:
    """Kuraterede ordninger for de valgte kommuner, bedst for børn først."""
    raekke = {"høj": 0, "middel": 1, "lav": 2}
    valgte = [k for k in KURATEREDE if k["kommune"] in kommuner]
    return sorted(valgte, key=lambda k: raekke.get(k["boernevaerdi"], 9))
