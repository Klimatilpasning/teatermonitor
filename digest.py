# -*- coding: utf-8 -*-
"""Bygger HTML- og tekstudgaven af digesten."""
from __future__ import annotations

import html
from datetime import date, timedelta

from kultunaut import Arrangement

UGEDAGE = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
MAANEDSNAVNE = ["", "januar", "februar", "marts", "april", "maj", "juni", "juli",
                "august", "september", "oktober", "november", "december"]

CSS = """
body{margin:0;padding:0;background:#f4f2ee;
     font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
     color:#23201c;line-height:1.5}
.ramme{max-width:680px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}
.dato{color:#6b6459;font-size:13px;margin:0 0 24px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;color:#6b6459;
   margin:32px 0 12px;padding-bottom:6px;border-bottom:1px solid #ddd8d0}
.kort{background:#fff;border:1px solid #e5e0d8;border-radius:10px;
      padding:14px 16px;margin-bottom:10px}
.kort.ny{border-left:4px solid #c2410c}
.titel{font-size:16px;font-weight:600;margin:0 0 3px}
.titel a{color:#23201c;text-decoration:none}
.meta{font-size:13px;color:#6b6459;margin:0 0 6px}
.besk{font-size:13px;color:#4a453d;margin:0}
.maerker{margin:8px 0 0}
.m{display:inline-block;font-size:11px;font-weight:600;border-radius:99px;
   padding:2px 9px;margin:0 5px 4px 0;text-transform:uppercase;letter-spacing:.04em}
.m-ny{background:#fde5d4;color:#9a3412}
.m-jul{background:#dcefe0;color:#1f6b38}
.m-pop{background:#e2e6f5;color:#33409c}
.m-alder{background:#eee9e1;color:#5a5348}
.klub{background:#fff;border:1px solid #e5e0d8;border-radius:10px;
      padding:14px 16px;margin-bottom:10px}
.klub .v{font-size:11px;font-weight:600;text-transform:uppercase;
         letter-spacing:.04em;padding:2px 8px;border-radius:99px}
.v-høj{background:#dcefe0;color:#1f6b38}
.v-middel{background:#fdf0d0;color:#8a5a08}
.v-lav{background:#eee9e1;color:#6b6459}
.klub ul{margin:8px 0 0;padding-left:18px;font-size:13px;color:#4a453d}
.forbehold{font-size:12px;color:#8a5a08;margin:8px 0 0}
.fod{font-size:12px;color:#8a8175;margin-top:32px;border-top:1px solid #ddd8d0;
     padding-top:14px}
.tom{background:#fff;border:1px dashed #d5cec4;border-radius:10px;
     padding:18px;text-align:center;color:#6b6459;font-size:14px}
"""


def dansk_dato(d: date) -> str:
    return f"{UGEDAGE[d.weekday()]} {d.day}. {MAANEDSNAVNE[d.month]}"


def _datolinje(arr: Arrangement) -> str:
    if arr.dato is None:
        return arr.dato_tekst or "dato ikke oplyst"
    tekst = dansk_dato(arr.dato)
    if arr.dato.year != date.today().year:
        tekst += f" {arr.dato.year}"
    if arr.tidspunkt:
        tekst += f" kl. {arr.tidspunkt}"
    if arr.ekstra_datoer:
        n = len(arr.ekstra_datoer)
        sidste = max(arr.ekstra_datoer)
        tekst += f" (+{n} flere frem til {sidste.day}. {MAANEDSNAVNE[sidste.month]})"
    return tekst


def _alderstekst(arr: Arrangement) -> str:
    if arr.alder_fra is None and arr.alder_til is None:
        return ""
    if arr.alder_til is None:
        return f"fra {arr.alder_fra} år"
    if arr.alder_fra is None:
        return f"op til {arr.alder_til} år"
    return f"{arr.alder_fra}-{arr.alder_til} år"


def _maerker(arr: Arrangement, er_ny: bool) -> str:
    ud = []
    if er_ny:
        ud.append('<span class="m m-ny">Nyt</span>')
    if getattr(arr, "jul", False):
        ud.append('<span class="m m-jul">Julesæson</span>')
    for sig in getattr(arr, "efterspoergsel", []):
        ud.append(f'<span class="m m-pop">{html.escape(sig)}</span>')
    alder = _alderstekst(arr)
    if alder:
        ud.append(f'<span class="m m-alder">{html.escape(alder)}</span>')
    return f'<div class="maerker">{"".join(ud)}</div>' if ud else ""


def _kort(arr: Arrangement, nye_id: set[str]) -> str:
    er_ny = arr.id in nye_id
    titel = html.escape(arr.titel)
    if arr.link:
        titel = f'<a href="{html.escape(arr.link)}">{titel}</a>'
    sted = html.escape(arr.spillested or arr.kilde)
    besk = html.escape(arr.beskrivelse[:230])
    if len(arr.beskrivelse) > 230:
        besk += "…"
    return f"""
    <div class="kort{' ny' if er_ny else ''}">
      <p class="titel">{titel}</p>
      <p class="meta">{html.escape(_datolinje(arr))} · {sted} · {html.escape(arr.kommune)}</p>
      <p class="besk">{besk}</p>
      {_maerker(arr, er_ny)}
    </div>"""


def _afsnit(titel: str, poster: list[Arrangement], nye_id: set[str],
            maks: int = 25) -> str:
    if not poster:
        return ""
    vist, resten = poster[:maks], len(poster) - maks
    kort = "".join(_kort(a, nye_id) for a in vist)
    hale = (f'<p class="besk" style="color:#8a8175">+ {resten} flere i dette '
            f'afsnit — se den fulde oversigt.</p>') if resten > 0 else ""
    return f"<h2>{html.escape(titel)}</h2>{kort}{hale}"


def _klubafsnit(anbefalinger: list[dict], dynamiske: dict[str, list[dict]]) -> str:
    if not anbefalinger and not dynamiske:
        return ""
    dele = ["<h2>Klubber og medlemsordninger</h2>"]
    for k in anbefalinger:
        fordele = "".join(f"<li>{html.escape(f)}</li>" for f in k["fordele"])
        forbehold = (f'<p class="forbehold">OBS: {html.escape(k["forbehold"])}</p>'
                     if k.get("forbehold") else "")
        dele.append(f"""
        <div class="klub">
          <p class="titel"><a href="{html.escape(k['link'])}">{html.escape(k['navn'])}</a>
             <span class="v v-{k['boernevaerdi']}">børneværdi: {k['boernevaerdi']}</span></p>
          <p class="meta">{html.escape(k['kommune'])} · {html.escape(k['pris'])}</p>
          <p class="besk">{html.escape(k['hvorfor'])}</p>
          <ul>{fordele}</ul>
          {forbehold}
          <p class="forbehold" style="color:#8a8175">Tal verificeret {k['verificeret']}</p>
        </div>""")

    for kommune, foreninger in dynamiske.items():
        navne = ", ".join(html.escape(f["navn"]) for f in foreninger[:14])
        dele.append(f'<div class="klub"><p class="meta">'
                    f'<strong>Øvrige foreninger i {html.escape(kommune)}:</strong> '
                    f'{navne}</p></div>')
    return "".join(dele)


def byg_html(godkendte: list[Arrangement], nye_id: set[str], conf: dict,
             klub_anbefalinger: list[dict], klub_dynamiske: dict[str, list[dict]],
             kildestatus: list[dict], voksne: list[Arrangement] | None = None) -> str:
    i_dag = date.today()
    kerne = set(conf["kerne_kommuner"])

    nye = [a for a in godkendte if a.id in nye_id]

    # "Nyt siden sidst" giver kun mening som eget afsnit i normal drift.
    # På første kørsel (eller efter nulstilling) er ALT nyt, og et eget
    # afsnit ville sluge hele digesten og tømme de øvrige afsnit.
    eget_nyt_afsnit = 0 < len(nye) <= 30

    ovrige = [a for a in godkendte if not (eget_nyt_afsnit and a.id in nye_id)]
    rejse = set(conf.get("rejse_kommuner", []))
    store = [a for a in ovrige if a.kommune in rejse]
    store_id = {a.id for a in store}
    jul = [a for a in ovrige if getattr(a, "jul", False) and a.id not in store_id]
    jul_id = {a.id for a in jul}
    snart_graense = i_dag + timedelta(days=21)
    snart = [a for a in ovrige
             if a.dato and a.dato <= snart_graense
             and a.id not in jul_id and a.id not in store_id]
    brugt = jul_id | store_id | {a.id for a in snart}
    resten = [a for a in ovrige if a.id not in brugt]
    kerne_resten = [a for a in resten if a.kommune in kerne]
    oevrig_resten = [a for a in resten if a.kommune not in kerne]

    maks = conf.get("maks_pr_afsnit", 25)
    if godkendte:
        afsnit = []
        if eget_nyt_afsnit:
            afsnit.append(_afsnit(f"Nyt siden sidst ({len(nye)})", nye, nye_id, maks))
        afsnit += [
            _afsnit("Inden for 3 uger", snart, nye_id, maks),
            _afsnit("Julesæson – book i god tid", jul, nye_id, maks),
            _afsnit("Store forestillinger – værd at køre efter", store, nye_id, maks),
            _afsnit("Senere i nærområdet", kerne_resten, nye_id, maks),
            _afsnit("Senere i det øvrige Østjylland", oevrig_resten, nye_id, maks),
        ]
        krop = "".join(afsnit)
    else:
        krop = ('<div class="tom">Ingen arrangementer matchede denne gang. '
                'Det kan være helt normalt uden for sæsonen.</div>')

    fejlende = [k for k in kildestatus if k["antal"] == 0]
    fodnote = (f"{len(godkendte)} arrangementer · horisont {conf['horisont_dage']} dage · "
               f"alder {conf['alder_fra']}-{conf['alder_til']} år · "
               f"kilder: Kultunaut + {len(kildestatus)} spillesteder")
    if fejlende:
        fodnote += f" ({len(fejlende)} spillesteder gav intet — se logfilen)"

    return f"""<!doctype html><html lang="da"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Teatermonitor {i_dag.isoformat()}</title><style>{CSS}</style></head><body>
<div class="ramme">
  <h1>Børneteater i Østjylland</h1>
  <p class="dato">{dansk_dato(i_dag)} {i_dag.year} · Silkeborg og Aarhus i fokus</p>
  {krop}
  {_afsnit("Til de voksne — det bedste på scenerne", voksne or [], nye_id, 12)}
  {_klubafsnit(klub_anbefalinger, klub_dynamiske)}
  <p class="fod">{html.escape(fodnote)}<br>
  "Populær" er et skøn ud fra antal opførelser og turné — ikke billetsalgstal.</p>
</div></body></html>"""


def byg_tekst(godkendte: list[Arrangement], nye_id: set[str],
              voksne: list[Arrangement] | None = None) -> str:
    linjer = [f"BØRNETEATER I ØSTJYLLAND — {date.today().isoformat()}", ""]
    if not godkendte:
        linjer.append("Ingen arrangementer matchede denne gang.")
    linjer += _tekstlinjer(godkendte, nye_id)
    if voksne:
        linjer += ["", "TIL DE VOKSNE — DET BEDSTE PÅ SCENERNE", ""]
        linjer += _tekstlinjer(voksne, nye_id)
    return "\n".join(linjer)


def _tekstlinjer(poster: list[Arrangement], nye_id: set[str]) -> list[str]:
    linjer: list[str] = []
    for arr in poster:
        maerker = []
        if arr.id in nye_id:
            maerker.append("NYT")
        if getattr(arr, "jul", False):
            maerker.append("JUL")
        maerker.extend(getattr(arr, "efterspoergsel", []))
        alder = _alderstekst(arr)
        if alder:
            maerker.append(alder)
        suffix = f"  [{', '.join(maerker)}]" if maerker else ""
        linjer.append(f"- {_datolinje(arr)} | {arr.titel} | "
                      f"{arr.spillested or arr.kilde}, {arr.kommune}{suffix}")
        if arr.link:
            linjer.append(f"  {arr.link}")
    return linjer
