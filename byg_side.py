# -*- coding: utf-8 -*-
"""Bygger den offentlige oversigtsside ud fra udbakke/data.json.

Siden er selvstændig: al data lægges ind i HTML'en, så den kan hostes
hvor som helst uden backend.

    python byg_side.py            -> udbakke/side.html
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

ROT = Path(__file__).resolve().parent
DATA = ROT / "udbakke" / "data.json"
UD = ROT / "udbakke" / "side.html"

MAANEDER = ["", "januar", "februar", "marts", "april", "maj", "juni", "juli",
            "august", "september", "oktober", "november", "december"]
UGEDAGE = ["man", "tir", "ons", "tor", "fre", "lør", "søn"]

SIDE = """<!doctype html>
<html lang="da">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Børneteater i Østjylland</title>
<meta name="description" content="Hele sæsonens scenekunst for børn i Østjylland — teater, dukketeater, koncerter og cirkus. Silkeborg og Aarhus i centrum.">
<style>
:root{
  --ground:#eceee8; --panel:#f7f8f5; --ink:#1b2019; --daemp:#5f6b5e;
  --linje:#d5d9d0; --curtain:#9d2b32; --amber:#a8741a; --sage:#4f6553;
  --skygge:0 1px 2px rgba(27,32,25,.06),0 4px 14px rgba(27,32,25,.05);
}
@media (prefers-color-scheme:dark){
  :root{ --ground:#12160f; --panel:#1a1f18; --ink:#e6e9e1; --daemp:#9aa596;
         --linje:#2c332a; --curtain:#e0656d; --amber:#e0a942; --sage:#8fae97;
         --skygge:0 1px 2px rgba(0,0,0,.4),0 4px 14px rgba(0,0,0,.3); }
}
:root[data-theme="dark"]{
  --ground:#12160f; --panel:#1a1f18; --ink:#e6e9e1; --daemp:#9aa596;
  --linje:#2c332a; --curtain:#e0656d; --amber:#e0a942; --sage:#8fae97;
  --skygge:0 1px 2px rgba(0,0,0,.4),0 4px 14px rgba(0,0,0,.3);
}
:root[data-theme="light"]{
  --ground:#eceee8; --panel:#f7f8f5; --ink:#1b2019; --daemp:#5f6b5e;
  --linje:#d5d9d0; --curtain:#9d2b32; --amber:#a8741a; --sage:#4f6553;
  --skygge:0 1px 2px rgba(27,32,25,.06),0 4px 14px rgba(27,32,25,.05);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.baand{max-width:1080px;margin:0 auto;padding:0 20px}

header{padding:44px 0 24px;border-bottom:2px solid var(--ink)}
h1{margin:0;font-size:clamp(30px,5vw,46px);line-height:1.02;font-weight:800;
   letter-spacing:-.03em;text-wrap:balance}
h1 em{font-style:normal;color:var(--curtain)}
.manchet{margin:12px 0 0;max-width:62ch;color:var(--daemp);font-size:15px}
.stamp{margin:16px 0 0;display:flex;flex-wrap:wrap;gap:8px 20px;
  font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;
  letter-spacing:.04em;text-transform:uppercase;color:var(--daemp);
  font-variant-numeric:tabular-nums}
.stamp b{color:var(--ink);font-weight:700}

.filter{position:sticky;top:0;z-index:20;background:var(--ground);
  border-bottom:1px solid var(--linje);padding:12px 0 10px;margin-bottom:8px;
  box-shadow:0 8px 12px -10px rgba(0,0,0,.3)}
.filterrk{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
/* Kommunerne holdes på én rulbar række, så filterbjælken ikke æder skærmen */
#kommuner{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;
  margin-top:8px;padding-bottom:2px}
#kommuner::-webkit-scrollbar{display:none}
#kommuner .chip{flex:0 0 auto}
.soeg{flex:1 1 210px;min-width:170px;padding:8px 12px;border:1px solid var(--linje);
  border-radius:7px;background:var(--panel);color:var(--ink);font-size:14px;
  font-family:inherit}
.soeg:focus-visible,.chip:focus-visible{outline:2px solid var(--curtain);outline-offset:2px}
.chip{border:1px solid var(--linje);background:var(--panel);color:var(--daemp);
  border-radius:99px;padding:6px 13px;font-size:13px;cursor:pointer;
  font-family:inherit;transition:background .12s,color .12s,border-color .12s}
.chip:hover{border-color:var(--sage);color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--ground);
  border-color:var(--ink);font-weight:600}
.chip.varm[aria-pressed="true"]{background:var(--curtain);border-color:var(--curtain);
  color:#fff}
.tael{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;
  color:var(--daemp);letter-spacing:.04em;font-variant-numeric:tabular-nums;
  padding:12px 0 4px}

h2.maaned{margin:34px 0 12px;padding-bottom:7px;scroll-margin-top:130px;
  border-bottom:1px solid var(--linje);
  font-size:13px;text-transform:uppercase;letter-spacing:.14em;font-weight:700;
  color:var(--sage);display:flex;justify-content:space-between;align-items:baseline}
h2.maaned span{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
  font-weight:400;color:var(--daemp);letter-spacing:.04em}

.liste{display:grid;gap:10px}
.post{display:grid;grid-template-columns:66px 1fr;gap:16px;background:var(--panel);
  border:1px solid var(--linje);border-radius:10px;padding:14px 16px;
  box-shadow:var(--skygge)}
.post.jul{border-left:3px solid var(--amber)}
.post.stor{border-left:3px solid var(--curtain)}
.dag{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;text-align:center;
  font-variant-numeric:tabular-nums;padding-top:2px}
.dag .n{display:block;font-size:23px;font-weight:700;line-height:1;
  letter-spacing:-.03em}
.dag .u{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.1em;
  color:var(--daemp);margin-top:4px}
.titel{margin:0 0 3px;font-size:18px;line-height:1.22;font-weight:600;
  font-family:Georgia,"Iowan Old Style","Palatino Linotype",serif;
  letter-spacing:-.005em;text-wrap:balance}
.titel a{color:inherit;text-decoration:none;
  text-decoration-color:var(--linje);text-underline-offset:3px}
.titel a:hover{text-decoration:underline}
.hvor{margin:0;font-size:13px;color:var(--daemp)}
.hvor b{color:var(--ink);font-weight:600}
.om{margin:7px 0 0;font-size:13px;color:var(--daemp);max-width:68ch}
.tags{margin-top:9px;display:flex;flex-wrap:wrap;gap:5px}
.t{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;
  border-radius:99px;padding:3px 9px;border:1px solid transparent}
.t-alder{background:transparent;border-color:var(--linje);color:var(--daemp)}
.t-jul{background:color-mix(in srgb,var(--amber) 15%,transparent);color:var(--amber)}
.t-stor{background:color-mix(in srgb,var(--curtain) 13%,transparent);color:var(--curtain)}
.t-pop{background:color-mix(in srgb,var(--sage) 16%,transparent);color:var(--sage)}

.tom{padding:44px 20px;text-align:center;color:var(--daemp);
  border:1px dashed var(--linje);border-radius:10px;margin-top:20px}

.klubber{margin:56px 0 0;padding-top:28px;border-top:2px solid var(--ink)}
.klubnet{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));
  margin-top:16px}
.klub{background:var(--panel);border:1px solid var(--linje);border-radius:10px;
  padding:16px 18px;box-shadow:var(--skygge)}
.klub h3{margin:0 0 4px;font-size:16px;font-family:Georgia,"Iowan Old Style",serif;
  font-weight:600}
.klub h3 a{color:inherit;text-decoration:none}
.klub h3 a:hover{text-decoration:underline}
.vaerdi{display:inline-block;font-size:10.5px;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;border-radius:99px;padding:3px 9px;margin-bottom:8px}
.v-høj{background:color-mix(in srgb,var(--sage) 18%,transparent);color:var(--sage)}
.v-middel{background:color-mix(in srgb,var(--amber) 16%,transparent);color:var(--amber)}
.v-lav{background:transparent;border:1px solid var(--linje);color:var(--daemp)}
.pris{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;
  color:var(--ink);margin:0 0 8px}
.klub ul{margin:8px 0 0;padding-left:17px;font-size:13px;color:var(--daemp)}
.klub li{margin-bottom:3px}
.obs{margin:10px 0 0;font-size:12px;color:var(--amber)}

footer{margin:56px 0 40px;padding-top:20px;border-top:1px solid var(--linje);
  font-size:12.5px;color:var(--daemp);max-width:68ch}
footer a{color:var(--sage)}
@media (max-width:560px){
  .post{grid-template-columns:52px 1fr;gap:12px;padding:12px 13px}
  .dag .n{font-size:19px}
  header{padding:30px 0 18px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>

<div class="baand">
<header>
  <h1>Børneteater i <em>Østjylland</em></h1>
  <p class="manchet">Hele sæsonens scenekunst for børn — teater, dukketeater,
     koncerter og cirkus — samlet fra Kultunaut og teatrenes egne programmer.
     Silkeborg og Aarhus i centrum, de store forestillinger længere væk taget med.</p>
  <p class="stamp">
    <span><b>__ANTAL__</b> forestillinger</span>
    <span><b>__JUL__</b> i julesæsonen</span>
    <span><b>__KOMMUNER__</b> kommuner</span>
    <span>Opdateret __OPDATERET__</span>
  </p>
</header>

<div class="filter">
  <div class="filterrk">
    <input id="soeg" class="soeg" type="search" placeholder="Søg i titel, sted eller beskrivelse…"
           aria-label="Søg i forestillinger">
    <button class="chip varm" id="f-jul" aria-pressed="false">Kun jul</button>
    <button class="chip varm" id="f-stor" aria-pressed="false">Store forestillinger</button>
    <button class="chip" id="f-kerne" aria-pressed="false">Silkeborg + Aarhus</button>
  </div>
  <div class="filterrk" id="kommuner" style="margin-top:8px"></div>
</div>

<p class="tael" id="tael"></p>
<div id="resultat"></div>

<section class="klubber">
  <h2 style="margin:0;font-size:22px;letter-spacing:-.02em">Klubber værd at melde sig ind i</h2>
  <p class="manchet" style="margin-top:8px">Vurderet på hvad de er værd
     <em style="font-style:normal;border-bottom:1px solid var(--linje)">for børneteater</em>
     — ikke generelt. Priser er tjekket ved kilden.</p>
  <div class="klubnet" id="klubber"></div>
</section>

<footer>
  <p><strong>Sådan er listen lavet.</strong> Data hentes fra Kultunauts
  arrangementskalender for de østjyske kommuner plus teatrenes egne sider, og
  filtreres på scenekunst for børn. Genrer sættes af arrangørerne selv, så der
  kan glide enkelte voksenforestillinger med — og noget kan mangle, hvis
  arrangøren ikke har registreret det.</p>
  <p><strong>Om "populær".</strong> Der findes ingen offentlige billetsalgstal.
  Mærkatet bygger på antal opførelser og om forestillingen turnerer i flere
  kommuner. Det er et skøn, ikke en måling.</p>
</footer>
</div>

<script>
const DATA = __DATA__;
const KLUBBER = __KLUBBER__;
const UGE = ["man","tir","ons","tor","fre","lør","søn"];
const MDR = ["","januar","februar","marts","april","maj","juni","juli",
             "august","september","oktober","november","december"];
const KERNE = __KERNE__;
const REJSE = __REJSE__;

const tilstand = {soeg:"", jul:false, stor:false, kerne:false, kommune:null};

function alderTekst(a){
  if(a.alder_fra==null && a.alder_til==null) return null;
  if(a.alder_til==null) return "fra "+a.alder_fra+" år";
  if(a.alder_fra==null) return "op til "+a.alder_til+" år";
  return a.alder_fra+"-"+a.alder_til+" år";
}
function esc(s){return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}

function kort(a){
  const d = a.dato ? new Date(a.dato+"T00:00:00") : null;
  const dag = d ? d.getDate() : "–";
  const uge = d ? UGE[(d.getDay()+6)%7] : "";
  const ekstra = a.ekstra_datoer.length ? " +"+a.ekstra_datoer.length+" datoer" : "";
  const tid = a.tidspunkt ? " kl. "+esc(a.tidspunkt) : "";
  const alder = alderTekst(a);
  const stor = REJSE.includes(a.kommune);
  let tags = "";
  if(alder) tags += '<span class="t t-alder">'+esc(alder)+'</span>';
  if(a.jul) tags += '<span class="t t-jul">Julesæson</span>';
  if(stor) tags += '<span class="t t-stor">Køretur værd</span>';
  (a.efterspoergsel||[]).forEach(s=>{tags += '<span class="t t-pop">'+esc(s)+'</span>';});
  const titel = a.link ? '<a href="'+esc(a.link)+'" rel="noopener">'+esc(a.titel)+'</a>'
                       : esc(a.titel);
  return '<article class="post'+(a.jul?" jul":"")+(stor?" stor":"")+'">'
    + '<div class="dag"><span class="n">'+dag+'</span><span class="u">'+uge+'</span></div>'
    + '<div><p class="titel">'+titel+'</p>'
    + '<p class="hvor"><b>'+esc(a.spillested)+'</b> · '+esc(a.kommune)+tid+esc(ekstra)+'</p>'
    + (a.beskrivelse?'<p class="om">'+esc(a.beskrivelse.slice(0,190))+(a.beskrivelse.length>190?"…":"")+'</p>':"")
    + (tags?'<div class="tags">'+tags+'</div>':"")
    + '</div></article>';
}

function filtrer(){
  const q = tilstand.soeg.toLowerCase().trim();
  return DATA.filter(a=>{
    if(tilstand.jul && !a.jul) return false;
    if(tilstand.stor && !REJSE.includes(a.kommune)) return false;
    if(tilstand.kerne && !KERNE.includes(a.kommune)) return false;
    if(tilstand.kommune && a.kommune!==tilstand.kommune) return false;
    if(q){
      const h = (a.titel+" "+a.spillested+" "+a.kommune+" "+a.beskrivelse).toLowerCase();
      if(!h.includes(q)) return false;
    }
    return true;
  });
}

function tegn(){
  const valgte = filtrer();
  document.getElementById("tael").textContent =
    valgte.length + " af " + DATA.length + " forestillinger";

  if(!valgte.length){
    document.getElementById("resultat").innerHTML =
      '<div class="tom">Ingen forestillinger matcher. Prøv at fjerne et filter.</div>';
    return;
  }
  const grupper = new Map();
  valgte.forEach(a=>{
    const n = a.dato ? a.dato.slice(0,7) : "9999-99";
    if(!grupper.has(n)) grupper.set(n,[]);
    grupper.get(n).push(a);
  });
  let html = "";
  [...grupper.keys()].sort().forEach(n=>{
    const poster = grupper.get(n);
    let navn = "Dato ikke oplyst";
    if(n!=="9999-99"){
      const [aar,m] = n.split("-");
      navn = MDR[parseInt(m,10)] + " " + aar;
    }
    html += '<h2 class="maaned">'+navn+'<span>'+poster.length+'</span></h2>'
          + '<div class="liste">' + poster.map(kort).join("") + '</div>';
  });
  document.getElementById("resultat").innerHTML = html;
}

// Kommune-chips
const antalPrKommune = {};
DATA.forEach(a=>{antalPrKommune[a.kommune]=(antalPrKommune[a.kommune]||0)+1;});
const raekke = Object.keys(antalPrKommune).sort((a,b)=>antalPrKommune[b]-antalPrKommune[a]);
document.getElementById("kommuner").innerHTML = raekke.map(k=>
  '<button class="chip" data-kommune="'+esc(k)+'" aria-pressed="false">'+esc(k)
  +' <span style="opacity:.6">'+antalPrKommune[k]+'</span></button>').join("");

document.querySelectorAll("[data-kommune]").forEach(b=>{
  b.addEventListener("click",()=>{
    const k = b.dataset.kommune;
    const aktiv = tilstand.kommune===k;
    tilstand.kommune = aktiv ? null : k;
    document.querySelectorAll("[data-kommune]").forEach(o=>
      o.setAttribute("aria-pressed", String(!aktiv && o===b)));
    tegn();
  });
});

function skifte(id,noegle){
  const b = document.getElementById(id);
  b.addEventListener("click",()=>{
    tilstand[noegle] = !tilstand[noegle];
    b.setAttribute("aria-pressed", String(tilstand[noegle]));
    tegn();
  });
}
skifte("f-jul","jul"); skifte("f-stor","stor"); skifte("f-kerne","kerne");
document.getElementById("soeg").addEventListener("input",e=>{
  tilstand.soeg = e.target.value; tegn();
});

document.getElementById("klubber").innerHTML = KLUBBER.map(k=>
  '<div class="klub">'
  + '<span class="vaerdi v-'+k.boernevaerdi+'">børneværdi: '+k.boernevaerdi+'</span>'
  + '<h3><a href="'+esc(k.link)+'" rel="noopener">'+esc(k.navn)+'</a></h3>'
  + '<p class="pris">'+esc(k.kommune)+' · '+esc(k.pris)+'</p>'
  + '<p class="om" style="margin:0">'+esc(k.hvorfor)+'</p>'
  + '<ul>'+k.fordele.map(f=>'<li>'+esc(f)+'</li>').join("")+'</ul>'
  + (k.forbehold?'<p class="obs">OBS: '+esc(k.forbehold)+'</p>':"")
  + '</div>').join("");

tegn();
</script>
</body>
</html>
"""


def byg() -> Path:
    if not DATA.exists():
        raise SystemExit("Kør 'python monitor.py --toer' først — udbakke/data.json mangler.")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    arr = data["arrangementer"]

    opdateret = datetime.fromisoformat(data["opdateret"])
    kommuner = sorted({a["kommune"] for a in arr})
    rejse = ["Kolding", "Vejle", "Fredericia", "Herning", "Billund",
             "Esbjerg", "Odense", "Aalborg"]

    html = (SIDE
            .replace("__DATA__", json.dumps(arr, ensure_ascii=False))
            .replace("__KLUBBER__", json.dumps(data.get("klubber", []), ensure_ascii=False))
            .replace("__KERNE__", json.dumps(data.get("kerne_kommuner", []), ensure_ascii=False))
            .replace("__REJSE__", json.dumps(rejse, ensure_ascii=False))
            .replace("__ANTAL__", str(len(arr)))
            .replace("__JUL__", str(sum(1 for a in arr if a.get("jul"))))
            .replace("__KOMMUNER__", str(len(kommuner)))
            .replace("__OPDATERET__",
                     f"{opdateret.day}. {MAANEDER[opdateret.month]} {opdateret.year}"))

    UD.write_text(html, encoding="utf-8")
    return UD


if __name__ == "__main__":
    sti = byg()
    print(f"Skrev {sti} ({sti.stat().st_size:,} bytes)")
