# -*- coding: utf-8 -*-
"""Kultunaut-kilden — systemets rygrad.

Kultunaut er server-renderet HTML (ingen offentligt API), og svarene er
ISO-8859-1-kodede. Begge dele håndteres her.

Verificerede detaljer om deres søgeflade:
  * /perl/arrlist/type-nynaut?Area=<omraade>&Genre=<genre>&startnr=<n>
  * Area-værdier er fx "Silkeborg-storkommune" (aflæst fra deres dropdown)
  * Genre har en egen "Børneteater"-værdi
  * 12 arrangementer pr. side; startnr pager
  * Hvert kort er <div class="product" data-arrnr="..."> med titel, genre,
    beskrivelse, dato+spillested og pris
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

BASIS = "https://www.kultunaut.dk/perl/arrlist/type-nynaut"
STEDLISTE = "https://www.kultunaut.dk/perl/stedlist/type-nynaut"
PR_SIDE = 12
BRUGERAGENT = (
    "Teatermonitor/1.0 (privat kalenderovervaagning; kontakt via ejer)"
)

MAANEDER = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "maj": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}


@dataclass
class Arrangement:
    """Ét arrangement som vi har set det hos en kilde."""
    id: str
    titel: str
    genre: str
    beskrivelse: str
    dato: date | None
    dato_tekst: str
    tidspunkt: str
    spillested: str
    kommune: str
    link: str
    billede: str = ""
    kilde: str = "Kultunaut"
    alder_fra: int | None = None
    alder_til: int | None = None
    ekstra_datoer: list[date] = field(default_factory=list)

    @property
    def gruppenoegle(self) -> tuple[str, str]:
        """Samme forestilling samme sted = én post med flere spilledatoer."""
        return (self.titel.strip().lower(), self.spillested.strip().lower())


# ---------------------------------------------------------------------------
# Netværk
# ---------------------------------------------------------------------------
def _hent(url: str, sess: requests.Session, forsoeg: int = 3) -> BeautifulSoup | None:
    for n in range(forsoeg):
        try:
            svar = sess.get(url, timeout=25)
            if svar.status_code != 200:
                return None
            # Kultunaut leverer ISO-8859-1 uden altid at deklarere det korrekt.
            return BeautifulSoup(svar.content.decode("iso-8859-1", "replace"), "html.parser")
        except requests.RequestException:
            if n == forsoeg - 1:
                return None
            time.sleep(2 * (n + 1))
    return None


def _q(vaerdi: str) -> str:
    """URL-kod en værdi i latin-1, som Kultunaut forventer."""
    return quote(vaerdi, encoding="iso-8859-1", errors="replace")


# ---------------------------------------------------------------------------
# Parsning
# ---------------------------------------------------------------------------
def _parse_dato(tekst: str) -> tuple[date | None, str]:
    """'Fre. 14. aug. 2026 kl. 22, Avistorvet' -> (date(2026,8,14), '22').

    Kultunaut skriver også intervaller ('14. aug - 20. aug. 2026'); her
    bruges startdatoen.
    """
    t = tekst.replace("\xa0", " ")
    tid = ""
    m_tid = re.search(r"kl\.?\s*([0-9]{1,2}([.:][0-9]{2})?(\s*-\s*[0-9]{1,2}([.:][0-9]{2})?)?)", t)
    if m_tid:
        tid = m_tid.group(1).replace(".", ":").strip()

    aar_m = re.search(r"\b(20\d{2})\b", t)
    aar = int(aar_m.group(1)) if aar_m else None

    m = re.search(r"\b([0-9]{1,2})\.\s*([a-zæøå]{3})", t, re.IGNORECASE)
    if not m:
        return None, tid
    dag = int(m.group(1))
    maaned = MAANEDER.get(m.group(2).lower()[:3])
    if not maaned:
        return None, tid
    if aar is None:
        # Uden årstal: antag nærmeste fremtidige forekomst.
        i_dag = date.today()
        aar = i_dag.year if (maaned, dag) >= (i_dag.month, i_dag.day) else i_dag.year + 1
    try:
        return date(aar, maaned, dag), tid
    except ValueError:
        return None, tid


ALDER_MOENSTRE = [
    # "Aldersgruppe: 3-6 år", "Alder: 4 - 8 år"
    (re.compile(r"alder\w*\s*:?\s*(?:fra\s*)?(\d{1,2})\s*[-–til]{1,3}\s*(\d{1,2})\s*år", re.I), "interval"),
    # "Aldersgruppe: Fra 3 år", "for børn fra 5 år"
    (re.compile(r"(?:alder\w*\s*:?\s*)?fra\s*(\d{1,2})\s*år", re.I), "fra"),
    # "3-6 år", "6-10 år"
    (re.compile(r"\b(\d{1,2})\s*[-–]\s*(\d{1,2})\s*år\b", re.I), "interval"),
    # "4+ år", "fra 4+"
    (re.compile(r"\b(\d{1,2})\s*\+\s*år\b", re.I), "fra"),
    # "for børn på 3 år og opefter"
    (re.compile(r"\b(\d{1,2})\s*år\s*og\s*op", re.I), "fra"),
]


def udled_alder(tekst: str) -> tuple[int | None, int | None]:
    """Find aldersinterval i fritekst. Returnerer (fra, til)."""
    for moenster, slags in ALDER_MOENSTRE:
        m = moenster.search(tekst)
        if not m:
            continue
        if slags == "interval":
            a, b = int(m.group(1)), int(m.group(2))
            if 0 <= a <= b <= 18:
                return a, b
        else:
            a = int(m.group(1))
            if 0 <= a <= 18:
                return a, None
    return None, None


def _parse_kort(kort, kommune: str) -> Arrangement | None:
    arrnr = kort.get("data-arrnr", "").strip()
    if not arrnr:
        return None

    a = kort.find("a", href=re.compile("arrmore"))
    link = a["href"] if a and a.has_attr("href") else ""
    # NB: kortets data-price er en fast attrapværdi (125 på alle kort), ikke
    # den rigtige billetpris — den læses bevidst ikke.

    genre_el = kort.select_one(".genre_cat")
    genre = genre_el.get_text(" ", strip=True) if genre_el else ""

    titel_el = kort.select_one(".arr-genre h3")
    titel = titel_el.get_text(" ", strip=True) if titel_el else ""
    if not titel:
        return None

    besk_el = kort.select_one(".arr-description")
    beskrivelse = besk_el.get_text(" ", strip=True) if besk_el else ""

    tid_el = kort.select_one(".kult-month-day time")
    dato_tekst = tid_el.get_text(" ", strip=True) if tid_el else ""
    sted_el = tid_el.find("b") if tid_el else None
    spillested = sted_el.get_text(" ", strip=True) if sted_el else ""
    if spillested:
        dato_tekst = dato_tekst.replace(spillested, "").strip().rstrip(",").strip()

    dato, tidspunkt = _parse_dato(dato_tekst)
    alder_fra, alder_til = udled_alder(f"{titel} {beskrivelse}")

    billede_el = kort.select_one(".kult-image img")
    billede = billede_el.get("src", "") if billede_el else ""

    return Arrangement(
        id=f"kultunaut:{arrnr}",
        titel=titel,
        genre=genre,
        beskrivelse=beskrivelse,
        dato=dato,
        dato_tekst=dato_tekst,
        tidspunkt=tidspunkt,
        spillested=spillested,
        kommune=kommune,
        link=link,
        billede=billede,
        alder_fra=alder_fra,
        alder_til=alder_til,
    )


# ---------------------------------------------------------------------------
# Offentligt API
# ---------------------------------------------------------------------------
def hent_genre(kommune: str, omraade: str, genre: str, sess: requests.Session,
               maks_sider: int = 12, pause: float = 0.7) -> list[Arrangement]:
    """Hent alle arrangementer for én (kommune, genre) med paginering."""
    fundne: dict[str, Arrangement] = {}
    for side in range(maks_sider):
        url = f"{BASIS}?Area={_q(omraade)}&Genre={_q(genre)}"
        if side:
            url += f"&startnr={side * PR_SIDE}"
        suppe = _hent(url, sess)
        if suppe is None:
            break

        kort = suppe.select("div.product[data-arrnr]")
        if not kort:
            break

        nye = 0
        for k in kort:
            arr = _parse_kort(k, kommune)
            if arr and arr.id not in fundne:
                fundne[arr.id] = arr
                nye += 1
        if nye == 0:          # samme side igen = slut
            break
        time.sleep(pause)
    return list(fundne.values())


def hent_alt(kommuner: dict[str, str], genrer: list[str],
             log=print) -> list[Arrangement]:
    """Hent på tværs af kommuner og genrer. kommuner = {navn: omraade}."""
    sess = requests.Session()
    sess.headers.update({"User-Agent": BRUGERAGENT, "Accept-Language": "da-DK,da"})

    alle: dict[str, Arrangement] = {}
    for kommune, omraade in kommuner.items():
        for genre in genrer:
            fund = hent_genre(kommune, omraade, genre, sess)
            for arr in fund:
                # Første kommune der finder et arrangement "ejer" det.
                alle.setdefault(arr.id, arr)
            log(f"  Kultunaut {kommune:<12} {genre:<18} {len(fund):>3} fundet")
    return list(alle.values())


def hent_foreninger(omraade: str, stedtype: str = "Teaterforening") -> list[dict]:
    """Hent foreninger/klubber af en given type i et område."""
    sess = requests.Session()
    sess.headers.update({"User-Agent": BRUGERAGENT})
    url = f"{STEDLISTE}?StedType={_q(stedtype)}&Area={_q(omraade)}&Godkendt=Alle"
    suppe = _hent(url, sess)
    if suppe is None:
        return []

    ud, set_navne = [], set()
    for a in suppe.select('a[href*="/sted/"]'):
        navn = a.get_text(" ", strip=True)
        # Sprogvælgeren i sidehovedet matcher også — sortér den fra.
        if not navn or navn in {"Dansk", "Svensk", "Engelsk", "Tysk"}:
            continue
        if navn in set_navne:
            continue
        set_navne.add(navn)
        ud.append({"navn": navn, "link": a.get("href", "")})
    return ud
