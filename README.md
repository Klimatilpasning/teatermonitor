# Teatermonitor — børneteater i Østjylland

Overvåger scenekunst for børn i Østjylland og sender en ugentlig mail.
Silkeborg og Aarhus er kernen; de store forestillinger længere væk
(Kolding, Vejle, Fredericia, Herning, Billund) tages med.

## Kom i gang

1. **Indsæt Brevo-nøglen.** Omdøb `.env.eksempel` til `.env` og indsæt din
   nøgle i `BREVO_API_KEY=`. Uden den skrives digesten stadig til
   `udbakke/`, men den bliver ikke sendt.
2. Prøv en kørsel uden afsendelse:

```bash
python monitor.py --toer
```

## Kommandoer

| Kommando | Hvad den gør |
|---|---|
| `python monitor.py` | Kør og send. Husker hvad der er set før. |
| `python monitor.py --toer` | Kør uden at sende eller gemme. Åbner resultatet. |
| `python monitor.py --tjek-kilder` | Vis hvilke kilder der reelt svarer. |
| `python monitor.py --nulstil` | Glem hvad der er set før. |
| `python byg_side.py` | Byg den offentlige side i `udbakke/side.html`. |

## Ugentlig kørsel

Kører i GitHub Actions hver **mandag 05:30 UTC** (07:30 dansk sommertid) —
se `.github/workflows/ugentlig.yml`. Jobbet henter data, sender mailen,
bygger `docs/index.html` og committer både siden og hukommelsen tilbage.
Kør den manuelt med **Run workflow** under fanen Actions.

Fejler afsendelsen, bygges siden alligevel — trinnet er sat til
`continue-on-error`, så en manglende nøgle ikke også koster dig siden.

### Engangsopsætning på GitHub

Under Settings → Secrets and variables → Actions oprettes tre secrets:

| Secret | Værdi |
|---|---|
| `BREVO_API_KEY` | Din Brevo-nøgle (SMTP & API → API Keys) |
| `TEATERMONITOR_MODTAGERE` | Modtagerens mail. Flere adskilles med komma |
| `TEATERMONITOR_AFSENDER` | Din i Brevo **verificerede** afsenderadresse |

Mailadresser står bevidst ikke i `config.json` — repoet er offentligt, fordi
GitHub Pages kræver det på en gratis konto.

Slå til sidst Pages til: Settings → Pages → Source: *Deploy from a branch* →
branch `main`, mappe `/docs`.

### Lokal kørsel som alternativ

Den planlagte Windows-opgave **Teatermonitor** kan køre det samme lokalt
via `koer.ps1`. Den kræver at maskinen er tændt, og er derfor kun et
supplement:

```powershell
Get-ScheduledTaskInfo -TaskName "Teatermonitor"
```

## Sådan virker den

**Kultunaut er rygraden.** Der findes intet offentligt API, men søgesiderne
er server-renderede og kan hentes direkte:

```
/perl/arrlist/type-nynaut?Area=Silkeborg-storkommune&Genre=Børneteater&startnr=12
```

Tre ting er værd at vide, hvis kilden skal justeres:

- Svarene er **ISO-8859-1**-kodede, ikke UTF-8. Både URL-parametre og
  svar-body skal håndteres i latin-1.
- Kultunaut har sin egen genre `Børneteater`, som rammer præcist.
  `Area`-værdierne er deres egne (`Aarhus-storkommune` osv.) — se `OMRAADER`.
- Der er 12 resultater pr. side; `startnr` pager.
- Kortenes `data-price` er en **attrapværdi** (125 på alle kort) og læses
  bevidst ikke.

**Filtrering.** Arrangørerne sætter selv genren, så den er upålidelig — under
"Børneteater" ligger både fodboldskoler og kreaværksteder. Derfor kræver
`filtrering.py` at der er et scene-, musik- eller fortællesignal, og at det
er entydigt møntet på børn. Et løst "barn" i titlen tæller ikke, ellers
kommer voksendramaer med.

**Spillesteder.** `spillesteder.py` tjekker desuden teatrenes egne sider med
tre metoder i rækkefølge: WordPress-API, JSON-LD, og til sidst
overskrift+dato-scanning. Flere teatre (bl.a. Aarhus Teater og Filuren)
er JavaScript-sider, som ikke kan læses uden en headless browser — de
dækkes i praksis af Kultunaut. Kør `--tjek-kilder` for at se status.

**"Populær" er et skøn.** Der findes ingen offentlige billetsalgstal.
Mærkatet bygger på antal opførelser og om forestillingen turnerer i flere
kommuner. Det står også på den offentlige side.

## Indstillinger

Alt justeres i `config.json`:

| Nøgle | Betydning |
|---|---|
| `modtagere` | Hvem mailen sendes til |
| `afsendelse` | `brevo`, `smtp` eller `ingen` |
| `kerne_kommuner` | Vægtes højest i digesten |
| `rejse_kommuner` | Kun **store** forestillinger hentes herfra |
| `alder_fra` / `alder_til` | Aldersinteresse |
| `horisont_dage` | Hvor langt frem der kigges (365 = hele sæsonen) |
| `minimum_point` | Hæv for en skarpere digest |
| `maks_pr_afsnit` | Loft over antal poster pr. afsnit i mailen |

Hemmeligheder står **kun** i `.env` eller som miljøvariabler — aldrig i
`config.json`.

## Hensyn til kilderne

Kultunaut har ingen åben API-aftale. Scriptet henter derfor med en
identificerende User-Agent, pauser mellem kald og kører én gang om ugen.
Hvis det skal bruges mere intensivt, skriv til kultunaut@kultunaut.dk om en
dataaftale.
