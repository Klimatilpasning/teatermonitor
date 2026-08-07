# -*- coding: utf-8 -*-
"""Relevansfiltrering + berigelse.

Formålet er BREDE børnekulturoplevelser: teater, dukketeater, koncerter,
cirkus, danseforestillinger, fortælling. Det behøver ikke være "rent teater".
Vi sorterer kun det fra, der tydeligt ikke er en oplevelse for børn
(generalforsamlinger, loppemarkeder, kurser o.l.).

Nødvendigt fordi Kultunauts genrer sættes af arrangørerne selv og er løse.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

from kultunaut import Arrangement

# Genrer der i sig selv er et stærkt børnesignal
BOERNEGENRER = {"børneteater", "for børn", "baby/barsel", "familiefilm"}

# Ord der indikerer en oplevelse man kan tage børn med til (bredt)
OPLEVELSES_ORD = [
    # scenekunst
    "teater", "forestilling", "scenekunst", "skuespil", "dukketeater",
    "figurteater", "marionet", "musical", "ballet", "opera", "operette",
    "danseforestilling", "danseteater", "dans", "cirkus", "nycirkus",
    "klovn", "gøgler", "artist", "akrobat", "revy", "kabaret",
    "improteater", "skyggeteater", "objektteater", "spiseteater",
    "gadeteater", "animationsteater", "performance",
    # musik og fortælling
    "koncert", "teaterkoncert", "musikteater", "musikforestilling",
    "fortælleforestilling", "fortælleteater", "fortælling", "eventyrteater",
    "syngespil", "børnekoncert", "familiekoncert", "sangfest",
    "højtlæsning", "eventyrstund", "trylleshow", "tryllekunst", "magi",
    "dukkespil", "bamseteater", "sanseoplevelse",
]

# Svage børnesignaler — tæller kun som ekstra point, aldrig alene.
# ("barn" alene fanger voksendramaer som "Hvorfor barnet koger i polentaen".)
BOERNE_ORD = [
    "børn", "barn", "børne", "familie", "familier", "baby",
    "tumling", "vuggestue", "børnehave", "indskoling", "skoleklasse",
    "junior", "eventyr", "nisse",
]

# Stærke signaler: teksten siger eksplicit at forestillingen er FOR børn.
STRIKTE_BOERNE_ORD = [
    "for børn", "for de mindste", "for de yngste", "for hele familien",
    "børneteater", "børneforestilling", "familieforestilling",
    "familieteater", "børnefamilie", "familiekoncert", "børnekoncert",
    "aldersgruppe", "anbefalet alder", "børn og voksne", "børn og unge",
    "for børnehaver", "for indskolingen", "for skoleklasser",
    "hele familien", "familievenlig", "børnevenlig",
]

# Ord der stærkt indikerer at det IKKE er en scene-/musikoplevelse.
# Udvidet efter første tørkørsel, hvor fodboldskoler, svømmecamps,
# skattejagter og kunstudstillinger slap igennem.
FRASORTER = [
    # møder og administration
    "generalforsamling", "bestyrelsesmøde", "banko", "bankospil",
    "loppemarked", "genbrugsmarked", "torvedag", "messe", "reception",
    "konference", "seminar", "fyraftensmøde", "netværksmøde",
    "informationsmøde", "borgermøde", "gudstjeneste", "konfirmation",
    # sport og lejre
    "fodboldskole", "fodboldcamp", "aquacamp", "svømmecamp", "sommercamp",
    "sportslejr", "idrætslejr", "håndboldskole", "svømmesal", "vandsjov",
    "sejlads", "gymnastikopvisning", "træningslejr", "fodboldstævne",
    # aktiviteter uden scene
    "skattejagt", "gaming event", "e-sport", "lan-party",
    "kunstudstilling", "børnekunstudstilling", "udstilling",
    "kunstskole", "kreaværksted", "krea-værksted", "åbent værksted",
    "rundvisning", "omvisning", "ferieaktivitet", "aktivitetsdag",
    "kursus", "aftenskole", "undervisningsforløb", "workshopforløb",
    # baby- og småbørnsformater — ikke scenekunst
    "babysalmesang", "salmesang", "babyrytmik", "rytmik", "legestue",
    "musikalsk legestue", "krybbespil", "sanserum", "sansetur",
    "babybio", "babycafé", "babycafe", "mødregruppe", "barselscafé",
    "krible krable", "brunch", "fællesspisning",
    "musiksanseri", "sanseri", "balletskole", "danseskole", "klovneløb",
    "workshop", "billedkunst",
    "læseklub", "læsekreds", "bogklub", "lektiecafé", "lektiehjælp",
    "strikkecafé", "spilklub", "sprogcafé",
]

# Kendetegn ved professionel scenekunst — giver ekstra point.
KVALITETSTEGN = [
    "teater", "teatret", "teatergruppe", "egnsteater", "turnéteater",
    "scenekunst", "forestilling", "dukketeater", "figurteater",
    "musikteater", "musikhus", "skuespil", "opera", "ballet",
]

# Spillesteder der som udgangspunkt viser professionel scenekunst.
KVALITETSSTEDER = [
    "teater", "scene", "musikhus", "kulturhus", "kulturhotel",
    "gruppe 38", "refleksion", "filuren", "bora bora", "svalegangen",
    "værket", "katapult", "carte blanche", "fængslet", "godsbanen",
]

# Julesæson-signaler
JULE_ORD = [
    "jul", "jule", "julen", "nisse", "nissen", "advent", "lucia",
    "julemand", "juleeventyr", "julekoncert", "juleforestilling",
    "julehygge", "julekalender", "nytår",
]


# --- Store forestillinger -------------------------------------------------
# Fra rejsekommunerne medtages KUN det store: musicals, de store teaterhuse
# og turnéopsætninger. Hverdagsbørneteater derovre er ikke en køretur værd.
STORE_HUSE = [
    "fredericia teater", "musikteatret vejle", "musikhuset", "musikkens hus",
    "nicolai", "godset", "kolding teater", "team teatret", "jyske bank boxen",
    "arena", "det ny teater", "odense teater", "magasinet", "aalborg teater",
    "vejle musikteater", "sønderborghus", "alsion", "messecenter",
    "forum horsens", "værket", "gigantium",
]

STORE_TEGN = [
    "musical", "familiemusical", "musicalforestilling", "storforestilling",
    "stor forestilling", "danmarksturné", "danmarkstour", "turné",
    "isshow", "arenashow", "cirkusforestilling", "symfoniorkester",
    "det kongelige teater", "gæstespil", "verdensturné",
]


def er_stor_forestilling(arr: Arrangement) -> bool:
    """Er det en 'kør gerne en time'-forestilling?

    Bevidst kun to kriterier: et af de store huse, eller et eksplicit
    stor-forestillings-ord. Antal opførelser blev prøvet som tredje
    kriterium, men det udnævnte ugentlige læseklubber til storforestillinger.
    """
    tekst = _norm(f"{arr.titel} {arr.beskrivelse} {arr.genre}")
    sted = _norm(arr.spillested)
    return (any(h in sted for h in STORE_HUSE)
            or any(t in tekst for t in STORE_TEGN))


def _norm(tekst: str) -> str:
    t = unicodedata.normalize("NFC", tekst.lower())
    return re.sub(r"\s+", " ", t)


def _rammer(tekst: str, ord_liste: list[str]) -> list[str]:
    return [o for o in ord_liste if o in tekst]


def alder_overlapper(arr: Arrangement, fra: int, til: int) -> bool | None:
    """Overlapper arrangementets alder med interessen? None = ikke oplyst."""
    if arr.alder_fra is None and arr.alder_til is None:
        return None
    a_fra = arr.alder_fra if arr.alder_fra is not None else 0
    a_til = arr.alder_til if arr.alder_til is not None else 18
    return a_fra <= til and a_til >= fra


def vurder(arr: Arrangement, conf: dict) -> tuple[bool, int, str]:
    """Vurdér ét arrangement. Returnerer (medtag, point, begrundelse)."""
    tekst = _norm(f"{arr.titel} {arr.beskrivelse} {arr.genre}")
    genre = _norm(arr.genre)

    negative = _rammer(tekst, FRASORTER)
    oplevelse = _rammer(tekst, OPLEVELSES_ORD)
    boerne = _rammer(tekst, BOERNE_ORD)
    boernegenre = genre in BOERNEGENRER

    # Frasortering vinder over genren: arrangører sætter selv genren, og
    # fodboldskoler og kunstværksteder havner rutinemæssigt under "For børn".
    if negative:
        return False, 0, f"frasorteret ({negative[0]})"

    # Kernekrav: der skal være en scene-, musik- eller fortælleoplevelse.
    # Uden det er det ikke den slags, digesten handler om.
    if not oplevelse:
        return False, 0, "ingen scene-/musikoplevelse nævnt"

    point, grunde = 0, []
    if boernegenre:
        point += 40
        grunde.append(f"genre: {arr.genre}")
    if oplevelse:
        point += 25
        grunde.append(oplevelse[0])
    if boerne:
        point += 20
        grunde.append(f"børn: {boerne[0]}")

    overlap = alder_overlapper(arr, conf["alder_fra"], conf["alder_til"])
    if overlap is True:
        point += 30
        grunde.append(f"alder {arr.alder_fra or 0}-{arr.alder_til or '?'} år")
    elif overlap is False:
        return False, 0, (f"alder uden for interesse "
                          f"({arr.alder_fra or 0}-{arr.alder_til or '?'} år)")
    else:
        if not conf["medtag_uden_alder"]:
            return False, 0, "ingen alder oplyst"

    # Oplevelsen er på plads; nu skal den også være møntet på børn.
    # Et løst "barn" i titlen er IKKE nok — der skal enten være
    # børnegenre, en oplyst alder der passer, eller en eksplicit
    # formulering om at det er for børn/familier.
    strikte = _rammer(tekst, STRIKTE_BOERNE_ORD)
    if strikte:
        point += 15
    if not (boernegenre or overlap is True or strikte):
        return False, point, "intet entydigt børnesignal"

    # Kvalitetsvægt: professionel scenekunst frem for lokale aktiviteter.
    sted = _norm(arr.spillested)
    if _rammer(tekst, KVALITETSTEGN):
        point += 20
    if _rammer(sted, KVALITETSSTEDER):
        point += 15
        grunde.append("scenekunststed")

    if point < conf.get("minimum_point", 0):
        return False, point, f"for lav relevans ({point} point)"

    return True, point, ", ".join(grunde) or "medtaget"


def i_horisont(arr: Arrangement, dage: int) -> bool:
    if arr.dato is None:
        return True
    i_dag = date.today()
    return i_dag <= arr.dato <= i_dag + timedelta(days=dage)


def er_julesaeson(arr: Arrangement) -> bool:
    """Julearrangement — enten på ord eller på dato i højsæsonen."""
    tekst = _norm(f"{arr.titel} {arr.beskrivelse}")
    if any(re.search(rf"\b{o}", tekst) for o in JULE_ORD):
        return True
    datoer = [d for d in [arr.dato, *arr.ekstra_datoer] if d]
    return any(d.month == 12 or (d.month == 11 and d.day >= 15) for d in datoer)


def gruppér(arrangementer: list[Arrangement]) -> list[Arrangement]:
    """Samme forestilling samme sted = én post med flere spilledatoer."""
    grupper: dict[tuple[str, str], Arrangement] = {}
    for arr in sorted(arrangementer, key=lambda a: (a.dato is None, a.dato or date.max)):
        noegle = arr.gruppenoegle
        if noegle in grupper:
            hoved = grupper[noegle]
            if arr.dato and arr.dato != hoved.dato and arr.dato not in hoved.ekstra_datoer:
                hoved.ekstra_datoer.append(arr.dato)
        else:
            grupper[noegle] = arr
    return list(grupper.values())


def berig(godkendte: list[Arrangement]) -> None:
    """Sæt afledte felter: julesæson og efterspørgsels-indikatorer.

    VIGTIGT: Vi har ingen billetsalgstal. "Populær" er derfor et *skøn*
    bygget på to observerbare ting:
      - hvor mange gange forestillingen spiller (stor opsætning / mange shows)
      - om den turnerer i flere kommuner (efterspurgt nok til at rejse rundt)
    Det angives som indikator, ikke som en måling.
    """
    pr_titel: dict[str, list[Arrangement]] = {}
    for arr in godkendte:
        pr_titel.setdefault(_norm(arr.titel), []).append(arr)

    for arr in godkendte:
        soeskende = pr_titel[_norm(arr.titel)]
        kommuner = {a.kommune for a in soeskende}
        antal_visninger = sum(1 + len(a.ekstra_datoer) for a in soeskende)

        arr.jul = er_julesaeson(arr)                       # type: ignore[attr-defined]
        arr.antal_visninger = antal_visninger              # type: ignore[attr-defined]
        arr.antal_kommuner = len(kommuner)                 # type: ignore[attr-defined]

        signaler = []
        if antal_visninger >= 4:
            signaler.append(f"{antal_visninger} opførelser")
        if len(kommuner) >= 2:
            signaler.append(f"turnerer i {len(kommuner)} kommuner")
        arr.efterspoergsel = signaler                      # type: ignore[attr-defined]
        arr.populaer = bool(signaler)                      # type: ignore[attr-defined]


def filtrer(arrangementer: list[Arrangement], conf: dict,
            log=None) -> tuple[list[Arrangement], list[tuple[Arrangement, str]]]:
    """Kør hele filtreringen. Returnerer (godkendte, fravalgte_med_begrundelse)."""
    godkendt, fravalgt = [], []
    for arr in arrangementer:
        if not i_horisont(arr, conf["horisont_dage"]):
            fravalgt.append((arr, "uden for tidshorisont"))
            continue
        medtag, point, grund = vurder(arr, conf)
        if medtag:
            arr.point = point                      # type: ignore[attr-defined]
            arr.begrundelse = grund                # type: ignore[attr-defined]
            godkendt.append(arr)
        else:
            fravalgt.append((arr, grund))

    godkendt = gruppér(godkendt)
    berig(godkendt)

    # Rejsekommunerne sorteres først NU — "stor forestilling" afhænger bl.a.
    # af antal opførelser, som først er kendt efter gruppering og berigelse.
    rejse = set(conf.get("rejse_kommuner", []))
    if rejse:
        beholdt = []
        for arr in godkendt:
            if arr.kommune in rejse and not er_stor_forestilling(arr):
                fravalgt.append((arr, f"{arr.kommune}: ikke stor nok til turen"))
            else:
                if arr.kommune in rejse:
                    arr.stor = True            # type: ignore[attr-defined]
                beholdt.append(arr)
        godkendt = beholdt

    godkendt.sort(key=lambda a: (a.dato is None, a.dato or date.max, a.titel))
    if log:
        log(f"  Filtrering: {len(godkendt)} godkendt, {len(fravalgt)} fravalgt")
    return godkendt, fravalgt
