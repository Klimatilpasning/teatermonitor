# -*- coding: utf-8 -*-
"""Teatermonitor — børneteater og familieoplevelser i Østjylland.

Brug:
  python monitor.py                 kør og send (eller skriv fil, jf. config)
  python monitor.py --toer          kør uden at sende, vis resultatet
  python monitor.py --tjek-kilder   diagnosticér alle kilder
  python monitor.py --nulstil       glem hvad der er set før
  python monitor.py --alt-som-nyt   marker alt som nyt i denne kørsel
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import traceback
import webbrowser
from datetime import date, datetime

import afsendelse
import digest
import filtrering
import klubber
import kultunaut
import spillesteder
from config import GENRER_BREDE, GENRER_SIKRE, OMRAADER, STATE_DIR, UDBAKKE_DIR, indlaes

# Windows-konsollen er ikke UTF-8 som standard.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SET_FIL = STATE_DIR / "set.json"
LOG_FIL = STATE_DIR / "koersler.log"


def log(besked: str = "") -> None:
    print(besked)
    with LOG_FIL.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {besked}\n")


def indlaes_set() -> dict:
    if SET_FIL.exists():
        try:
            return json.loads(SET_FIL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log("  Advarsel: set.json var ulæselig — starter forfra")
    return {}


def gem_set(kendte: dict) -> None:
    SET_FIL.write_text(json.dumps(kendte, ensure_ascii=False, indent=1), encoding="utf-8")


def eksporter_data(godkendte: list, nye_id: set[str], conf: dict,
                   anbefalinger: list[dict], voksne: list | None = None) -> None:
    """Skriv et maskinlæsbart udtræk, som den offentlige side bygges af."""

    def som_post(arr) -> dict:
        return {
            "id": arr.id,
            "titel": arr.titel,
            "beskrivelse": arr.beskrivelse,
            "dato": arr.dato.isoformat() if arr.dato else None,
            "ekstra_datoer": [d.isoformat() for d in arr.ekstra_datoer],
            "tidspunkt": arr.tidspunkt,
            "spillested": arr.spillested or arr.kilde,
            "kommune": arr.kommune,
            "genre": arr.genre,
            "link": arr.link,
            "alder_fra": arr.alder_fra,
            "alder_til": arr.alder_til,
            "jul": bool(getattr(arr, "jul", False)),
            "efterspoergsel": list(getattr(arr, "efterspoergsel", [])),
            "point": getattr(arr, "point", 0),
            "ny": arr.id in nye_id,
        }

    poster = [som_post(a) for a in godkendte]
    data = {
        "opdateret": datetime.now().isoformat(timespec="seconds"),
        "antal": len(poster),
        "kerne_kommuner": conf["kerne_kommuner"],
        "alder": [conf["alder_fra"], conf["alder_til"]],
        "arrangementer": poster,
        "voksne": [som_post(a) for a in (voksne or [])],
        "klubber": anbefalinger,
    }
    sti = UDBAKKE_DIR / "data.json"
    sti.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"  Skrev {sti} ({len(poster)} arrangementer)")


def hent_alt(conf: dict) -> tuple[list, list[dict]]:
    naere = conf["kerne_kommuner"] + conf["oevrige_kommuner"]
    kommuner = naere + conf.get("rejse_kommuner", [])
    omraadekort = {k: OMRAADER[k] for k in kommuner}

    log("Henter fra Kultunaut…")
    genrer = GENRER_SIKRE + GENRER_BREDE
    arrangementer = kultunaut.hent_alt(omraadekort, genrer, log=log)
    log(f"  I alt fra Kultunaut: {len(arrangementer)}")

    log("Tjekker spillesteders egne sider…")
    fra_steder, status = spillesteder.hent_alle(set(naere), log=log)
    log(f"  I alt fra spillesteder: {len(fra_steder)}")

    return arrangementer + fra_steder, status


def koer(conf: dict, toer: bool, alt_som_nyt: bool) -> int:
    raa, kildestatus = hent_alt(conf)
    godkendte, fravalgte = filtrering.filtrer(raa, conf, log=log)

    kendte = {} if alt_som_nyt else indlaes_set()
    nye_id = {a.id for a in godkendte if a.id not in kendte}
    log(f"  Heraf nye siden sidst: {len(nye_id)}")

    log("Henter klubber og foreninger…")
    alle_anbefalinger = klubber.anbefalinger(
        conf["kerne_kommuner"] + conf["oevrige_kommuner"])
    # I mailen vises klubafsnittet kun i månedens første uge (eller ved
    # allerførste kørsel) — den offentlige side har dem altid med.
    vis_klubber = conf["klubber_hver_gang"] or date.today().day <= 7 or not kendte
    dynamiske = klubber.hent_dynamiske(conf["kerne_kommuner"], log=log) if vis_klubber else {}
    anbefalinger = alle_anbefalinger if vis_klubber else []

    # Voksenafsnittet vælges fra de RÅ data, ikke fra de godkendte: alt
    # voksenindhold er allerede sorteret fra på det tidspunkt.
    voksne = filtrering.voksen_top(raa, conf, {a.id for a in godkendte})
    log(f"  Til voksenafsnittet: {len(voksne)}")

    html_krop = digest.byg_html(godkendte, nye_id, conf, anbefalinger, dynamiske,
                                kildestatus, voksne)
    tekst_krop = digest.byg_tekst(godkendte, nye_id, voksne)

    stempel = date.today().isoformat()
    fil = UDBAKKE_DIR / f"digest-{stempel}.html"
    fil.write_text(html_krop, encoding="utf-8")
    log(f"  Skrev {fil}")

    eksporter_data(godkendte, nye_id, conf, alle_anbefalinger, voksne)

    emne = f"Børneteater i Østjylland — {len(nye_id)} nye ({stempel})"
    if toer:
        log("\n" + tekst_krop)
        log(f"\nTørkørsel: intet sendt, intet gemt. Emne ville være: {emne}")
        webbrowser.open(fil.as_uri())
        return 0

    try:
        status = afsendelse.send(emne, html_krop, tekst_krop, conf)
        log(f"  {status}")
    except afsendelse.AfsendelsesFejl as fejl:
        log(f"  AFSENDELSE FEJLEDE: {fejl}")
        log(f"  Digesten ligger klar i {fil}")
        return 2

    for arr in godkendte:
        kendte[arr.id] = {"titel": arr.titel, "set": stempel}
    gem_set(kendte)
    log(f"  Gemte {len(kendte)} kendte arrangementer")
    return 0


def tjek_kilder(conf: dict) -> int:
    log("=== Kultunaut ===")
    kommuner = conf["kerne_kommuner"] + conf["oevrige_kommuner"]
    import requests
    sess = requests.Session()
    sess.headers.update({"User-Agent": kultunaut.BRUGERAGENT})
    i_alt = 0
    for k in kommuner:
        n = len(kultunaut.hent_genre(k, OMRAADER[k], "Børneteater", sess, maks_sider=3))
        i_alt += n
        log(f"  {k:<14} Børneteater: {n}")
    log(f"  Kultunaut samlet (stikprøve): {i_alt}")

    log("\n=== Spillesteder ===")
    _, status = spillesteder.hent_alle(set(kommuner), log=log)
    virker = [s for s in status if s["antal"] > 0]
    log(f"\n  {len(virker)} af {len(status)} spillesteder gav data.")
    for s in status:
        if s["antal"] == 0:
            log(f"    UDEN DATA: {s['navn']} — {s['status']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Teatermonitor for Østjylland")
    p.add_argument("--toer", action="store_true", help="kør uden at sende eller gemme")
    p.add_argument("--tjek-kilder", action="store_true", help="diagnosticér kilderne")
    p.add_argument("--nulstil", action="store_true", help="glem hvad der er set før")
    p.add_argument("--alt-som-nyt", action="store_true", help="marker alt som nyt")
    args = p.parse_args()

    conf = indlaes()
    log(f"=== Teatermonitor {datetime.now():%Y-%m-%d %H:%M} ===")

    if args.nulstil:
        SET_FIL.unlink(missing_ok=True)
        log("Hukommelsen er nulstillet.")
        return 0
    if args.tjek_kilder:
        return tjek_kilder(conf)

    try:
        return koer(conf, args.toer, args.alt_som_nyt)
    except Exception:
        log("UVENTET FEJL:\n" + traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
