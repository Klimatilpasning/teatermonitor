# -*- coding: utf-8 -*-
"""Test filtreringen mod cachede rådata.

Hentning tager ~10 minutter, filtrering tager et øjeblik. Uden en cache
koster hver lille justering af ordlisterne en ny fuld hentning, og så
bliver ordlisterne ikke justeret. Derfor:

  python test_filter.py --hent     hent rådata og læg dem i cachen
  python test_filter.py            filtrér cachen og vis resultatet
  python test_filter.py --niche    vis kun det, nicheudvidelsen henter ind
"""
from __future__ import annotations

import argparse
import io
import pickle
import sys
from dataclasses import asdict

import filtrering
import kultunaut
import spillesteder
from config import GENRER_BREDE, GENRER_SIKRE, OMRAADER, STATE_DIR, indlaes

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CACHE = STATE_DIR / "raadata.pickle"


def hent() -> list:
    conf = indlaes()
    naere = conf["kerne_kommuner"] + conf["oevrige_kommuner"]
    alle = naere + conf["rejse_kommuner"]
    omraadekort = {k: OMRAADER[k] for k in alle if k in OMRAADER}

    print("Henter fra Kultunaut…")
    arr = kultunaut.hent_alt(omraadekort, GENRER_SIKRE + GENRER_BREDE, log=print)
    print(f"  {len(arr)} fra Kultunaut")

    print("Henter fra spillesteder…")
    fra_steder, _ = spillesteder.hent_alle(set(naere), log=print)
    print(f"  {len(fra_steder)} fra spillesteder")

    raa = arr + fra_steder
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(raa))
    print(f"Cachet {len(raa)} arrangementer i {CACHE}")
    return raa


def indlaes_cache() -> list:
    if not CACHE.exists():
        sys.exit("Ingen cache. Kør først: python test_filter.py --hent")
    return pickle.loads(CACHE.read_bytes())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--hent", action="store_true", help="hent rådata til cachen")
    p.add_argument("--niche", action="store_true", help="vis kun nichefund")
    args = p.parse_args()

    raa = hent() if args.hent else indlaes_cache()
    conf = indlaes()
    godkendt, fravalgt = filtrering.filtrer(raa, conf)

    print(f"\n{len(raa)} rå  ->  {len(godkendt)} godkendt, {len(fravalgt)} fravalgt")

    if args.niche:
        traef = [a for a in godkendt
                 if filtrering._rammer(
                     filtrering._norm(f"{a.titel} {a.beskrivelse} {a.genre}"),
                     filtrering.NICHE_ORD)]
        print(f"\nNichefund: {len(traef)}\n")
        for a in sorted(traef, key=lambda x: (x.dato is None, x.dato or "")):
            ord_ = filtrering._rammer(
                filtrering._norm(f"{a.titel} {a.beskrivelse} {a.genre}"),
                filtrering.NICHE_ORD)
            print(f"  {a.dato}  {a.titel[:58]:<58}  {a.spillested[:26]:<26} [{', '.join(ord_[:3])}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
