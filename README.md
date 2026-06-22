# AHK Åhus Beach 2026 – matchschema

Live-uppdaterat matchschema, prenumererbara kalendrar och Excel för
**Alingsås HK:s sex lag** (3× P15 + 3× F15) under Åhus Beach Handboll 2026.

**Sida (öppna / lägg till på hemskärmen):**
https://martinwelen.github.io/alingsas-ahus-beach-2026/

Allt hostas gratis på GitHub Pages och **uppdateras automatiskt** av en robot i
GitHubs moln (GitHub Actions) som hämtar från cupmanager – ingen dator behöver
köra något manuellt.

---

## Vad som ingår

| Del | Beskrivning |
|-----|-------------|
| **Live-schemasida** (`index.html`) | Tre flikar: **Schema** (alla matcher i tidsordning med slutresultat på spelade, filter per lag, "härnäst"-nedräkning, "pågår nu"), **Tabeller** (grupptabeller med A/B/C-slutspelsgräns) och **Slutspel** (klassiskt träd A/B/C, dra-med-finger). Installerbar som app (PWA) med AHK-ikon, fungerar offline. |
| **7 kalendrar** (`ics/`) | En per lag + en samlad. Prenumereras på (auto-uppdateras hos prenumeranten). |
| **Excel** (`Alingsas_HK_Ahus_Beach_2026.xlsx`) | Alla matcher + ett blad per lag. |
| **Besöksstatistik** | Cloudflare Web Analytics (cookielöst, ingen samtyckesruta). |

Speldagar: **fre 17 juli & lör 18 juli 2026**. Matchtid: 2×5 min + 60 s paus.
Gruppspelet är 51 matcher; slutspelsmatcher dyker upp automatiskt när Alingsås
lottats in i dem (se nedan).

---

## Arkitektur / dataflöde

```
cupmanager (publikt API)
        │  fetch_matches.py  (filtrerar på de 6 lagens id, inkl. resultat)
        ▼
   matches.json            ← enda aktuella matchkällan (skrivs bara vid ändring)
        │  schedule.py      (gemensam laddare: matches.json annars seed)
        ├──────────────► build_site.py  → index.html, manifest.json, sw.js
        ├──────────────► build_ics.py   → ics/*.ics  (7 st)
        └──────────────► build_excel.py → .xlsx
        ▲                        ▲
   matches_data.py               │  standings.json  ← grupptabeller + slutspelsträd
   (seed/fallback + metadata)    │  fetch_standings.py (Division$table + Playoff)

.github/workflows/update.yml  → kör allt ovan i molnet (cron + manuellt),
                                committar bara när match- eller standings-datan ändrats
```

### Filer

| Fil | Roll |
|-----|------|
| `matches_data.py` | Lagmetadata (namn, slug, **cupmanager-id**, färg, grupp, klass), turnerings-id, konstanter (matchtid, tidszon, Pages-URL) **+ statisk seed-lista** som fallback. |
| `fetch_matches.py` | Hämtar matcher (inkl. slutresultat) via cupmanagers API, filtrerar på lag-id, skriver `matches.json`. Skriver bara om datan ändrats (hash); lämnar filen orörd vid fel. |
| `fetch_standings.py` | Hämtar de sex gruppernas tabeller och A/B/C-slutspelsträd, skriver `standings.json`. **Speglar cupmanagers tabellordning** (ingen egen tie-break-logik); skriver bara vid ändring. |
| `schedule.py` | Laddar `matches.json` (annars seed) och normaliserar alla matcher till samma form. |
| `build_site.py` | Genererar `index.html` (+ `manifest.json`, `sw.js`) med flikarna Schema/Tabeller/Slutspel. Läser `standings.json` om den finns (annars döljs de två extra flikarna). All HTML/CSS/JS finns här. |
| `build_ics.py` | Genererar de 7 `.ics`-filerna. Stabila UID per match; `SEQUENCE` = ändringstid. |
| `build_excel.py` | Genererar Excel-dokumentet. |
| `make_icons.py` | Rasteriserar `Alingsas_HK_logo.svg` → app-/favicon-PNG (körs lokalt vid behov; ikoner är statiska). |
| `Alingsas_HK_logo.svg` | Klubblogga (källa för ikonerna + favicon). |
| `.github/workflows/update.yml` | Molnroboten (cron + manuell körning). |

---

## Hur uppdateringen fungerar (utan din dator)

Roboten kör:

- **var 30:e minut** till vardags, och
- **var 10:e minut den 17–18 juli** (turneringshelgen),
- samt **manuellt**: repo → *Actions → Uppdatera schema → Run workflow*.

Varje körning: hämtar från cupmanager → om matchdatan ändrats byggs sida +
kalendrar + Excel om och committas → GitHub Pages publicerar. Ändras inget görs
ingen commit (inget brus).

**Slutspel:** filtreringen sker på lagens **id**, så när Alingsås lottas in i en
slutspelsmatch får den matchen Alingsås som lag och plockas upp automatiskt –
inget handpåläggande.

> GitHub pausar schemalagda jobb om repot är helt inaktivt i 60 dagar. Är det
> nära turneringen är det ingen risk; annars väck det med en manuell "Run workflow".

---

## Köra/bygga lokalt

```bash
pip install openpyxl                 # för Excel
python fetch_matches.py             # uppdaterar matches.json från cupmanager (~1–2 min)
python fetch_standings.py           # uppdaterar standings.json (tabeller + slutspel)
python build_ics.py && python build_excel.py && python build_site.py
```

Utan `matches.json` används den statiska seed-listan i `matches_data.py`.
Utan `standings.json` byggs sidan ändå – flikarna Tabeller/Slutspel döljs bara.

Regenerera ikonerna (sällan; kräver cairosvg + Pillow):
```bash
pip install cairosvg Pillow && python make_icons.py
```

---

## Drift / vanliga ändringar

- **Cron-frekvens:** `cron`-raderna i `.github/workflows/update.yml`.
- **Matchtid (kalenderlängd):** `MATCH_DURATION_MIN` i `matches_data.py`.
- **Lagfärger:** `team_colors` i `matches_data.py`.
- **App-ikon:** byt `Alingsas_HK_logo.svg`, kör `make_icons.py`, committa PNG:erna.
- **Statistik:** Cloudflare-token ligger i `build_site.py` (publik enligt design).

### Cupmanager-detaljer (för underhåll)

- API (publikt, ingen nyckel):
  `https://ahusbeachhandboll.cupmanager.net/rest/results_api/call?call=MatchWindow(...)&tournamentId=70944382`
- **Turnerings-id:** `70944382`
- **Lagens id:** P15 Blå `74904162`, P15 Orange `76280580`, P15 Vit `74904168`,
  F15 Blå `74294026`, F15 Gul `76514811`, F15 Vit `74294028`.

---

## Återanvända för kommande år (t.ex. 2027)

1. Hitta nya **turnerings-id** och **lag-id** (öppna årets resultatsida, kolla
   nätverksanropen till `rest/results_api/call`, eller lagsidornas URL `/result/team/<id>`).
2. Uppdatera `TOURNAMENT_ID` och `team_ids` i `matches_data.py` (och seed-listan om du vill).
3. Justera `cron`-datumen för turneringshelgen i workflowen.
4. Kör `python fetch_matches.py` och bygg om.

---

## Kalendrar – prenumerera (inte importera!)

Bas: `https://martinwelen.github.io/alingsas-ahus-beach-2026/ics/`
(`alingsas-alla.ics`, `alingsas-p15-bla.ics`, `…-p15-orange/-p15-vit/-f15-bla/-f15-gul/-f15-vit.ics`)

> **Prenumerera på URL:en** – importerar du filen blir matcherna fasta och
> uppdateras aldrig. Android/Outlook: lägg till via outlook.com i webbläsare.
> iPhone: Inställningar → Kalender → Lägg till prenumererad kalender.

---

## Medvetet ej byggt

**Push-notiser vid ändrad tid/bana.** Möjligt men kräver backend (t.ex. Cloudflare
Worker + VAPID) och har en iOS-hake (kräver installerad PWA). Enklaste vägen om det
blir aktuellt: roboten mejlar en färdig text att klistra in i lagets Messenger-grupp,
eller postar via en Discord-webhook. Roboten upptäcker redan ändringar – det som
saknas är bara utskicksdelen.

---

Källa: ahusbeachhandboll.cupmanager.net · Tider kan ändras av arrangören.
