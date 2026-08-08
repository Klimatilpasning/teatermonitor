# -*- coding: utf-8 -*-
"""Direkte tjek af udvalgte spillesteders egne sider.

Supplement til Kultunaut: nogle teatre annoncerer på egen side før (eller uden
at) de registrerer i Kultunaut. Modulet er bevidst defensivt — hvert sted
prøves med tre metoder i rækkefølge, og fejl rapporteres i stedet for at
vælte kørslen:

  1. WordPress REST API  (mest pålideligt, hvis sitet har en event-posttype)
  2. JSON-LD (schema.org/Event) i sidens HTML
  3. Overskrift+dato-scanning af server-renderet HTML

Kør ``python monitor.py --tjek-kilder`` for at se hvad der reelt virker.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

from kultunaut import Arrangement, MAANEDER, udled_alder

BRUGERAGENT = "Teatermonitor/1.0 (privat kalenderovervaagning)"

# Hvert sted: navn, kommune, metode og de nødvendige parametre.
# "wp"    -> wp-json REST, felt 'api'
# "html"  -> hent 'url' og prøv JSON-LD, derefter overskriftsscanning
SPILLESTEDER = [
    # --- Silkeborg ---
    {"navn": "Jysk Musikteater", "kommune": "Silkeborg", "metode": "wp",
     "api": "https://jmts.dk/wp-json/wp/v2/bwps?categories=69&per_page=50",
     "hjem": "https://jmts.dk/kategori/boern/"},
    {"navn": "Silkeborg Teater (børneteater)", "kommune": "Silkeborg", "metode": "html",
     "url": "https://www.silkeborgteater.dk/page-13/index.html"},
    {"navn": "Silkeborg Ny Teater", "kommune": "Silkeborg", "metode": "html",
     "url": "https://silkeborgnyteater.dk/"},
    {"navn": "Hakkehuset", "kommune": "Silkeborg", "metode": "html",
     "url": "https://hakkehuset.dk/"},

    # --- Aarhus ---
    {"navn": "Teater Refleksion", "kommune": "Aarhus", "metode": "html",
     "url": "https://refleksion.dk/forestillinger/"},
    {"navn": "Teatret Gruppe 38", "kommune": "Aarhus", "metode": "html",
     "url": "https://www.gruppe38.dk/"},
    {"navn": "Teaterhuset Filuren", "kommune": "Aarhus", "metode": "html",
     "url": "https://filuren.dk/forestillinger"},
    {"navn": "Bora Bora", "kommune": "Aarhus", "metode": "html",
     "url": "https://bora-bora.dk/"},
    {"navn": "Aarhus Teater", "kommune": "Aarhus", "metode": "html",
     "url": "https://www.aarhusteater.dk/det-sker"},
    {"navn": "Svalegangen", "kommune": "Aarhus", "metode": "html",
     "url": "https://www.svalegangen.dk/"},

    # --- Øvrige Østjylland ---
    # Randers Egnsteater hedder nu Randers Teater og kører Billetten,
    # så familieforestillingerne kan hentes direkte via wp-api (kategori 15).
    {"navn": "Randers Teater", "kommune": "Randers", "metode": "wp",
     "api": "https://randersteater.dk/wp-json/wp/v2/bwps?categories=15&per_page=50",
     "hjem": "https://randersteater.dk/program/"},
    {"navn": "Horsens Ny Teater", "kommune": "Horsens", "metode": "html",
     "url": "https://horsensnyteater.dk/"},
]

DATO_RE = re.compile(
    r"\b(\d{1,2})\.?\s*(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)[a-z]*\.?\s*(20\d{2})?",
    re.IGNORECASE,
)


def _sess() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": BRUGERAGENT, "Accept-Language": "da-DK,da"})
    return s


def _tekstdato(tekst: str) -> date | None:
    m = DATO_RE.search(tekst)
    if not m:
        return None
    dag = int(m.group(1))
    maaned = MAANEDER.get(m.group(2).lower()[:3])
    aar = int(m.group(3)) if m.group(3) else None
    if not maaned:
        return None
    if aar is None:
        i_dag = date.today()
        aar = i_dag.year if (maaned, dag) >= (i_dag.month, i_dag.day) else i_dag.year + 1
    try:
        return date(aar, maaned, dag)
    except ValueError:
        return None


def _fra_wp(sted: dict, sess: requests.Session) -> list[Arrangement]:
    svar = sess.get(sted["api"], timeout=25)
    svar.raise_for_status()
    poster = svar.json()
    ud = []
    for p in poster:
        titel = BeautifulSoup(p.get("title", {}).get("rendered", ""), "html.parser").get_text(" ", strip=True)
        krop = BeautifulSoup(p.get("content", {}).get("rendered", ""), "html.parser").get_text(" ", strip=True)
        if not titel:
            continue
        a_fra, a_til = udled_alder(f"{titel} {krop}")
        ud.append(Arrangement(
            id=f"wp:{sted['navn']}:{p.get('id')}",
            titel=titel, genre="Børn",
            beskrivelse=krop[:400],
            dato=_tekstdato(krop) or _tekstdato(titel),
            dato_tekst="", tidspunkt="",
            spillested=sted["navn"], kommune=sted["kommune"],
            link=p.get("link", sted.get("hjem", "")),
            kilde=sted["navn"], alder_fra=a_fra, alder_til=a_til,
        ))
    return ud


def _fra_jsonld(suppe: BeautifulSoup, sted: dict) -> list[Arrangement]:
    ud = []
    for tag in suppe.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        koe = data if isinstance(data, list) else [data]
        while koe:
            node = koe.pop()
            if isinstance(node, dict) and "@graph" in node:
                koe.extend(node["@graph"] if isinstance(node["@graph"], list) else [node["@graph"]])
                continue
            if not isinstance(node, dict):
                continue
            if "event" not in str(node.get("@type", "")).lower():
                continue
            titel = str(node.get("name", "")).strip()
            if not titel:
                continue
            raa_dato = str(node.get("startDate", ""))[:10]
            try:
                d = date.fromisoformat(raa_dato) if raa_dato else None
            except ValueError:
                d = None
            besk = str(node.get("description", ""))[:400]
            a_fra, a_til = udled_alder(f"{titel} {besk}")
            ud.append(Arrangement(
                id=f"ld:{sted['navn']}:{titel}:{raa_dato}",
                titel=titel, genre="", beskrivelse=besk,
                dato=d, dato_tekst=raa_dato, tidspunkt="",
                spillested=sted["navn"], kommune=sted["kommune"],
                link=str(node.get("url", sted.get("url", ""))),
                kilde=sted["navn"], alder_fra=a_fra, alder_til=a_til,
            ))
    return ud


# "Fra 16 år", "3-6 år", "6+", "20." er aldersangivelser og rubrikker —
# metadata der står som naboer til titlen, ikke titler i sig selv.
METADATA_RE = re.compile(
    r"(fra |for |ca\.? )?\d{1,2}\s*([-–]\s*\d{1,2})?\s*(\+|år|årige?|kl\.?)?\.?$",
    re.IGNORECASE,
)


ORD_RE = re.compile(r"[a-zæøå]{3,}", re.IGNORECASE)
# Ord der kun beskriver målgruppe eller tid — en titel kan ikke bestå af dem.
IKKE_TITELORD = {"år", "årige", "kla", "klasse", "fra", "for", "ca", "kl", "og"}


def _brugbar_titel(t: str) -> bool:
    t = t.strip()
    if not (2 < len(t) < 95):
        return False
    if DATO_RE.fullmatch(t) or METADATA_RE.fullmatch(t):
        return False
    # "2 - 4 år 22" slipper gennem regexet ovenfor, men er stadig kun alder.
    # Kræv mindst ét rigtigt ord.
    return any(o.lower() not in IKKE_TITELORD for o in ORD_RE.findall(t))


def _titel_fra_blok(blok, blok_tekst: str, sted: dict | None = None) -> str:
    """Find den bedste titel til en dato-bærende blok.

    Rækkefølgen er afgørende og fundet ved at prøve begge sidetyper:

      1. Overskrift INDE i blokken.
      2. Teksten før datoen i blokken. RapidWeaver-sider (Silkeborg Teater)
         har titel og dato i samme klump uden overskrifter overhovedet.
      3. Først derefter baglæns i dokumentet. Elementor-sider (Teater
         Refleksion) lægger titel og dato i hver sin widget, så blokken kun
         indeholder "Fra 16 år" eller "20.".

    Trin 3 må ikke komme før trin 2: gør det, finder Silkeborg Teaters sider
    deres egen sidehoved-overskrift og alle forestillinger kommer til at
    hedde "Silkeborg Teater".
    """
    for vaelger in ("h1", "h2", "h3", "h4", "h5", ".title", "strong", "b", "a"):
        el = blok.select_one(vaelger)
        if el and _brugbar_titel(el.get_text(" ", strip=True)):
            return el.get_text(" ", strip=True)

    foer = DATO_RE.split(blok_tekst)[0].strip(" -–·|,")
    if _brugbar_titel(foer):
        return foer[:90].strip()

    # Sidehoveder og logolinjer gentager spillestedets eget navn — det er
    # aldrig en forestillingstitel.
    eget_navn = _norm_navn(sted["navn"]) if sted else ""
    for h in blok.find_all_previous(["h1", "h2", "h3", "h4"], limit=8):
        t = h.get_text(" ", strip=True)
        if _brugbar_titel(t) and _norm_navn(t) not in (eget_navn, ""):
            if not (eget_navn and _norm_navn(t) in eget_navn):
                return t

    return foer[:90].strip()


def _norm_navn(t: str) -> str:
    return re.sub(r"[^a-zæøå0-9]+", "", t.lower())


def _fra_blokke(suppe: BeautifulSoup, sted: dict) -> list[Arrangement]:
    """Generel scanner: find de INDERSTE blokke der indeholder en dato.

    Virker på tværs af meget forskellige sider — Elementor-sider (Teater
    Refleksion) har titel og dato i nabo-widgets, mens ældre RapidWeaver-
    sider (Silkeborg Teater) har dem i samme 'stacks'-blok og slet ingen
    overskrifter. At tage den inderste dato-bærende blok rammer begge.
    """
    kandidater = []
    for el in suppe.find_all(["div", "article", "li", "section", "td", "a"]):
        tekst = el.get_text(" ", strip=True)
        if not (15 <= len(tekst) <= 320) or not DATO_RE.search(tekst):
            continue
        # Kun den inderste: spring over hvis et barn også bærer datoen
        if any(15 <= b.get_text(" ", strip=True).__len__() <= 320
               and DATO_RE.search(b.get_text(" ", strip=True))
               for b in el.find_all(["div", "article", "li", "section", "td", "a"])):
            continue
        kandidater.append((el, tekst))

    ud, set_noegler = [], set()
    for el, tekst in kandidater:
        d = _tekstdato(tekst)
        if not d:
            continue
        titel = _titel_fra_blok(el, tekst, sted)
        if not titel or len(titel) < 3:
            continue
        noegle = (titel.lower(), d)
        if noegle in set_noegler:
            continue
        set_noegler.add(noegle)

        lnk = el.find("a") or (el if el.name == "a" else None)
        href = (lnk.get("href") if lnk and lnk.has_attr("href") else "") or sted.get("url", "")
        if href.startswith("/"):
            base = sted.get("url", "")
            href = base[:base.find("/", 8)] + href if len(base) > 8 else href

        a_fra, a_til = udled_alder(tekst)
        ud.append(Arrangement(
            id=f"blok:{sted['navn']}:{titel}:{d}",
            titel=titel, genre="", beskrivelse=tekst[:400],
            dato=d, dato_tekst="", tidspunkt="",
            spillested=sted["navn"], kommune=sted["kommune"],
            link=href, kilde=sted["navn"], alder_fra=a_fra, alder_til=a_til,
        ))
    return ud


def hent_sted(sted: dict, sess: requests.Session) -> tuple[list[Arrangement], str]:
    """Returnerer (arrangementer, statusbesked)."""
    try:
        if sted["metode"] == "wp":
            fund = _fra_wp(sted, sess)
            return fund, f"wp-api: {len(fund)}"

        svar = sess.get(sted["url"], timeout=25)
        if svar.status_code >= 400:
            return [], f"HTTP {svar.status_code}"
        suppe = BeautifulSoup(svar.text, "html.parser")

        fund = _fra_jsonld(suppe, sted)
        if fund:
            return fund, f"json-ld: {len(fund)}"

        fund = _fra_blokke(suppe, sted)
        if fund:
            return fund, f"blokke: {len(fund)}"
        return [], "ingen datoer fundet (sandsynligvis JavaScript-side)"
    except requests.RequestException as fejl:
        return [], f"netværksfejl: {type(fejl).__name__}"
    except Exception as fejl:                    # bevidst bredt: én kilde må ikke vælte kørslen
        return [], f"fejl: {type(fejl).__name__}: {fejl}"


def hent_alle(kommuner: set[str] | None = None, log=print) -> tuple[list[Arrangement], list[dict]]:
    """Hent fra alle konfigurerede spillesteder. Returnerer (arrangementer, status)."""
    sess = _sess()
    alle, status = [], []
    for sted in SPILLESTEDER:
        if kommuner and sted["kommune"] not in kommuner:
            continue
        fund, besked = hent_sted(sted, sess)
        alle.extend(fund)
        status.append({"navn": sted["navn"], "kommune": sted["kommune"], "status": besked,
                       "antal": len(fund)})
        log(f"  {sted['navn']:<32} {besked}")
        time.sleep(0.6)
    return alle, status
