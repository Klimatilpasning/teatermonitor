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

# Nicheformer: det sanselige, det intime, det eksperimenterende og det
# antroposofiske. Holdt i en egen liste frem for at blive rørt ind i
# OPLEVELSES_ORD, så det kan ses hvad udvidelsen henter — og rulles tilbage
# alene, hvis den viser sig at støje.
NICHE_ORD = [
    # sanselig scenekunst
    "sanseteater", "sanseforestilling", "sansekoncert", "sanselig",
    "musiksanseri", "sanseri", "babyteater", "vuggestueteater",
    "sanseunivers", "sanserejse",
    # små, intime og private visninger
    "stueteater", "dagligstueteater", "hjemmeteater", "salonforestilling",
    "intimteater", "kammerspil", "mikroteater", "arbejdsvisning",
    "åben prøve", "åbne prøver", "work in progress", "prøvevisning",
    "for et lille publikum", "intim forestilling",
    # eksperimenterende scenekunst
    "eksperimenterende", "eksperimental", "site-specific", "stedsspecifik",
    "immersiv", "installationsteater", "vandreteater", "totalteater",
    "materialeteater", "bevægelsesteater", "billedteater", "lydteater",
    # musikalske former
    "musikfortælling", "musikdramatik", "koncertteater", "tonefortælling",
    "musikalsk forestilling", "musikalsk fortælling", "musikalsk eventyr",
    # Steiner og antroposofi
    "eurytmi", "eurytmisk", "rudolf steiner", "steinerskole", "steiner",
    "waldorf", "antroposofisk", "årstidsfest", "årstidsspil",
    "adventsspil", "adventshave", "adventsspiral", "michaelsfest",
    "sankthansspil", "fortællekunst", "levende fortælling",
]

# Nicheformater der stort set ikke findes i voksenudgaver. De tæller derfor
# som et entydigt børnesignal på linje med en oplyst alder — ellers ville de
# falde på kravet nede i vurder(), fordi de sjældent skriver "for børn".
NICHE_BOERNE_ORD = [
    "babyteater", "vuggestueteater", "sanseteater", "sanseforestilling",
    "sansekoncert", "musiksanseri", "årstidsspil", "adventsspil",
    "adventshave", "adventsspiral", "musikalsk eventyr",
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
    "musikalsk legestue", "krybbespil",
    "babybio", "babycafé", "babycafe", "mødregruppe", "barselscafé",
    "krible krable", "brunch", "fællesspisning",
    "balletskole", "danseskole", "klovneløb",
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
    # nichesteder: det små, det frie og det antroposofiske
    "steinerskole", "rudolf steiner", "waldorf", "fri skole", "friskole",
    "hakkehuset", "teaterhus", "scenekunsthus", "prøvesal", "atelier",
]

# Spillesteder hvis program i sig selv ER scenekunst for børn. Vi henter
# enten hele deres program (rene børneteatre) eller kun deres børneafdeling.
# Derfor er KILDEN barnesignalet — teksten behøver ikke bevise det.
#
# Uden dette leverede Teater Refleksion 0 af 8 og Jysk Musikteater 10 af 65,
# fordi en titel som "Fyrtøjet" hverken nævner teater eller børn. Netop de
# poetiske smaaformater taber paa at blive maalt paa ordvalg.
#
# Bora Bora, Svalegangen og Aarhus Teater staar bevidst IKKE her: vi henter
# hele deres program, og det er overvejende for voksne.
BOERNESCENER = [
    "gruppe 38", "refleksion", "filuren", "jysk musikteater",
    "silkeborg teater", "randers teater",
]

# Overskriftsscanningen af HTML opsamler rubrikker og brudstykker som
# "Fra 16 år", "20." og "Læs mere". Naar kilden alene kan godkende en post,
# skal skraldet frasorteres foerst — ellers bliver sidemenuer til forestillinger.
JUNK_TITEL = re.compile(
    r"^(?:\d+\.?|fra \d+ ?år|\d+\+|læs mere|se mere|køb billet\w*|"
    r"billetter|program|forestillinger|nyheder|om os|kontakt|luk|"
    # rubrikker der inddeler et program efter målgruppe
    r"unge og voksne|børn og unge|for børn|for voksne|for de mindste|"
    r"aktuelt|kommende|tidligere|arkiv|turné|på turné|repertoire|"
    # domænenavne fra sidefod og logolinjer, fx "jmts.dk."
    r"[\w-]+\.(?:dk|com|net|org)\.?)$",
    re.IGNORECASE,
)


def er_junk_titel(titel: str) -> bool:
    t = titel.strip().strip(".:–-").strip()
    return len(t) < 4 or bool(JUNK_TITEL.match(t))


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

    if er_junk_titel(arr.titel):
        return False, 0, "ikke en forestilling (opsamlet rubrik)"

    # Kun KILDEN må udløse tilliden, aldrig spillestedet. Kultunaut-poster
    # bærer spillestedets navn, så en match på spillested ville betro enhver
    # voksenkoncert der tilfældigvis afholdes på Jysk Musikteater.
    fra_boernescene = any(h in _norm(arr.kilde or "") for h in BOERNESCENER)

    negative = _rammer(tekst, FRASORTER)
    niche = _rammer(tekst, NICHE_ORD)
    # Nicheordene tæller på lige fod med de brede oplevelsesord, så en
    # eurytmiopvisning eller et stueteater kan komme gennem kernekravet.
    oplevelse = _rammer(tekst, OPLEVELSES_ORD) + niche
    boerne = _rammer(tekst, BOERNE_ORD)
    boernegenre = genre in BOERNEGENRER

    # Frasortering vinder over genren: arrangører sætter selv genren, og
    # fodboldskoler og kunstværksteder havner rutinemæssigt under "For børn".
    if negative:
        return False, 0, f"frasorteret ({negative[0]})"

    # Kernekrav: der skal være en scene-, musik- eller fortælleoplevelse.
    # Uden det er det ikke den slags, digesten handler om.
    if not oplevelse and not fra_boernescene:
        return False, 0, "ingen scene-/musikoplevelse nævnt"

    point, grunde = 0, []
    if fra_boernescene:
        # Vægtes højere end en genre (40), fordi genren sættes af arrangøren
        # selv, mens et dedikeret børneteaters eget program er en redaktionel
        # beslutning. Svarer til genre + korrekt alder, som er den anden vej
        # at blive sikker på at noget er for børn.
        point += 55
        grunde.append("børnescene")
    if boernegenre:
        point += 40
        grunde.append(f"genre: {arr.genre}")
    if oplevelse:
        point += 25
        grunde.append(oplevelse[0])
    if boerne:
        point += 20
        grunde.append(f"børn: {boerne[0]}")
    if niche:
        point += 20
        grunde.append(f"niche: {niche[0]}")

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
    # Babyteater og adventsspiraler skriver sjældent "for børn" — formatet
    # siger det selv. Uden dette ville nicheudvidelsen falde her.
    strikte += _rammer(tekst, NICHE_BOERNE_ORD)
    if strikte:
        point += 15
    if not (boernegenre or overlap is True or strikte or fra_boernescene):
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


# --- Voksenafsnittet ------------------------------------------------------
# Filtret smider alt voksenindhold væk. Men Gruppe 38, Aarhus Teater og
# Svalegangen laver scenekunst der er en aften værd, og den bør ikke gå tabt
# alene fordi den ikke er for børn. Her samles de ganske få der rager op.
#
# Bevidst en STRAM liste: pointer for de store huse, turné og mange
# opførelser. Uden en høj tærskel bliver afsnittet til endnu en programoversigt,
# og så er det ikke længere "det absolut bedste".
VOKSEN_MAKS = 12
VOKSEN_TAERSKEL = 45
VOKSEN_PR_KOMMUNE = 3


def _prominens(arr: Arrangement, kerne: set[str] | None = None) -> int:
    tekst = _norm(f"{arr.titel} {arr.beskrivelse} {arr.genre}")
    sted = _norm(arr.spillested)
    point = 0
    if _rammer(tekst, STORE_TEGN):
        point += 30
    if any(h in sted for h in STORE_HUSE):
        point += 25
    # Vægtes højt: det er de kunstnerisk tunge scener. Uden dette faldt
    # Gruppe 38s voksenforestillinger ud, fordi deres titler er nøgne
    # ("Marias Testamente") og siderne ikke skriver ordet teater.
    if _rammer(sted, KVALITETSSTEDER):
        point += 30
    if _rammer(tekst, KVALITETSTEGN):
        point += 15
    # En tirsdag aften i Vejle er noget andet end en i Aarhus. Uden dette
    # blev afsnittet til syv musicals i rejsekommunerne.
    if kerne and arr.kommune in kerne:
        point += 25
    # Mange opførelser og turné er de eneste efterspørgselssignaler vi har.
    point += min(getattr(arr, "antal_visninger", 1), 8) * 2
    point += (getattr(arr, "antal_kommuner", 1) - 1) * 10
    return point


def voksen_top(arrangementer: list[Arrangement], conf: dict,
               undgaa: set[str], maks: int = VOKSEN_MAKS) -> list[Arrangement]:
    """De få voksenforestillinger der er en aften værd.

    ``undgaa`` er id'erne på det, der allerede er med som børneteater —
    ellers ville familieforestillinger optræde to gange i samme mail.
    """
    kandidater = []
    for arr in arrangementer:
        if arr.id in undgaa or not i_horisont(arr, conf["horisont_dage"]):
            continue
        if er_junk_titel(arr.titel):
            continue
        tekst = _norm(f"{arr.titel} {arr.beskrivelse} {arr.genre}")
        if _rammer(tekst, FRASORTER):
            continue
        if not _rammer(tekst, OPLEVELSES_ORD + NICHE_ORD):
            continue
        # Noget med tydeligt børnesignal hører ikke hjemme her. Er det godt
        # nok, står det ovenfor; er det ikke, var der en grund.
        if _norm(arr.genre) in BOERNEGENRER or _rammer(tekst, STRIKTE_BOERNE_ORD):
            continue
        kandidater.append(arr)

    kandidater = gruppér(kandidater)
    berig(kandidater)

    kerne = set(conf.get("kerne_kommuner", []))
    scoret = [(a, _prominens(a, kerne)) for a in kandidater]
    scoret = [(a, p) for a, p in scoret if p >= VOKSEN_TAERSKEL]
    scoret.sort(key=lambda t: -t[1])

    # Samme turné spiller i flere byer. gruppér() holder dem adskilt, fordi
    # spillestedet indgår i nøglen — men i en top-12 må TINA ikke bruge tre
    # pladser. Den højest scorende opsætning vinder, og med kernebonussen
    # er det den nærmeste.
    # Loft pr. kommune, ellers æder Vejle Musikteaters musicalprogram hele
    # afsnittet og de mindre, kunstnerisk tunge scener kommer aldrig med.
    valgt, sete_titler = [], set()
    pr_kommune: dict[str, int] = {}
    for arr, _ in scoret:
        n = _norm(arr.titel)
        if n in sete_titler or pr_kommune.get(arr.kommune, 0) >= VOKSEN_PR_KOMMUNE:
            continue
        sete_titler.add(n)
        pr_kommune[arr.kommune] = pr_kommune.get(arr.kommune, 0) + 1
        valgt.append(arr)
        if len(valgt) >= maks:
            break

    valgt.sort(key=lambda a: (a.dato is None, a.dato or date.max, a.titel))
    return valgt


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
