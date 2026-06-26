# Klubbomfattande app (evergreen) – design

**Datum:** 2026-06-26
**Status:** Godkänd design, redo för implementationsplan

## Bakgrund & mål

Dagens app täcker **U15** (P15 + F15 Classic, 6 lag) och är live i repot
`alingsas-ahus-beach-2026`, redan installerad som PWA på föräldrars hemskärmar.

Mål: göra appen användbar för **hela Alingsås HK över hela Åhus Beach-turneringen**
— alla åldersgrupper, alla lag — **utan att röra den installerade U15-appen.**
Börja smalt (Åhus 2026) men bygg **parametriserat** (klubbkod + turnerings-id) så
lösningen kan återanvändas år efter år = evergreen.

## Fakta (verifierat mot cupmanager-API:t 2026-06-26)

- **Klubbkod:** `NameClub({id:73383031})`. Varje Team-entitet bär en `club`-referens
  → datan kan drivas på klubbkod istället för hårdkodade lag-id. Se [[club-wide-scaling]].
- **Omfattning:** 43 Alingsås-lag i 17 kategorier ≈ **10 åldersgrupper**.
- **Format:** **Classic** (U12–U18) och **Mini** (U8/U10/U11, "P8 Mini"/"F11 Mini"…).
  **Inga internationella Alingsås-lag 2026** — men internationella klasser finns i
  turneringen för andra klubbar.
- **Matchtid & poäng** (arrangörens regler, ahusbeach.com/spelregler): Classic *och*
  Mini kör **"2 × 5 min med 60 sek paus" = 11 min**, **1 poäng per mål**. Oavgjort i
  slutspel avgörs av **sudden death / shoot-out** vars utfall hamnar i slutsiffran —
  appens befintliga `winner_side` (härleder vinnare ur målsiffrorna) klarar detta.
  Internationella 2-set-reglerna beskrivs inte på Classic-sidan.
- **MatchResult är regel-agnostiskt:** samma objekt bär `homeGoals/awayGoals`
  (Classic) *och* `periodScores`/`pointsPerPeriod`/`winByPeriods`/`penalties`
  (set-baserat + shootout) *och* `homeState/awayState`. En hämtning täcker alla
  format; bara presentationen skiljer.
- Åldrar med både P och F spelar **samma dagar** (verifierat).

## Beslut

1. **Produktform:** en app **per åldersgrupp** (P+F ihop, som dagens app).
   ~10 appar, U-namngivna: **U8, U10, U11, U12, U13, U14, U15, U16, U17, U18.**
2. **Distribution:** **nytt evergreen-repo** för klubb-systemet. **U15 stannar i
   gamla repot** (underhållbart, ej fryst — fixar kan begäras där). Hubben i nya
   repot länkar till U15-appens befintliga URL i stället för att generera en dubblett.
3. **Kodisolering:** nya repot är en **självständig generaliserad build utan delad
   runtime** med gamla. Isoleringen *är* säkerhetsgarantin — nya repot kan aldrig
   röra den live U15-appen. Beprövade skript kopieras in och generaliseras; gemensamma
   fixar portas manuellt (medvetet pris för säkerhet).
4. **Mini (U8/U10/U11):** **schema bara** — inga resultat eller tabeller (minihandboll
   rankas oftast inte; minst antaganden om oprovad resultatmodell).
5. **Internationella regler:** **förberedd söm, byggs senare.** Abstraktionen detekterar
   formatet, men set/shootout-renderaren byggs när det faktiskt behövs.

## Topologi

```
GAMLA repot  (alingsas-ahus-beach-2026)   — oförändrad URL, underhållbart
   └── U15-appen (P15+F15 Classic)         ← föräldrarnas installerade app, rörs ej

NYA repot  (t.ex. alingsas-ahus-beach)     — evergreen, parametriserat
   ├── /                 → hubb: listar alla åldersgrupper (U15 → GAMLA URL:en)
   ├── /u8/  /u10/  /u11/ → Mini-appar (schema bara)
   ├── /u12/ … /u18/      → Classic-appar (utom u15)
   └── data + build genererar alla på en loop
```

## Arkitektur

### Datalager (klubbkodsdrivet)

Ersätter den handskrivna `matches_data.teams`-listan med **upptäckt** från API:t:

1. Hämta alla matchfönster (som idag), behåll bara matcher där hemma-/bortalagets
   `club` = `NameClub(73383031)`.
2. Härled per lag ur team-entiteten: `id`, kategori → **åldersnummer (U)** + **kön (P/F)**,
   `suffix` (Blå/Vit/1/2…), division (grupp), genererad `slug`.
3. **Bucketa per åldersgrupp** → varje bucket = en app (kan rymma P och/eller F).
4. **Färger** härleds ur suffix (Blå/Vit/Svart/Orange/Gul/Röd → resp.; siffror 1–4 →
   palett) med fallback.

`fetch_standings.py` generaliseras likadant: grupptabeller + A/B/C-träd för klubbens
alla divisioner, bucketade per åldersgrupp.

En liten **config-modul** håller `TOURNAMENT_ID`, `CLUB_ID`, matchlängder per regeltyp,
`PAGES_BASE` samt härledningshjälparna (ålder/kön/färg/regeltyp). Byt `TOURNAMENT_ID`
nästa år → allt fungerar igen.

### Format-abstraktion

- **Detektera regeltyp** robust ur resultatflaggorna (`winByPeriods`/`pointsPerPeriod`/
  `ordinaryPeriodCount`) + kategorinamn — inte bara genom att läsa "Classic" i namnet.
- Varje regeltyp mappar till: **resultat-renderare**, **matchlängd** (iCal),
  **om tabeller/slutspel gäller**.
- **Varje åldersgrupps-app är ett enda format** (U8 = Mini, U15 = Classic) → appen väljer
  renderare/längd efter sin grupp; ingen blandning inom en app.
- **Classic:** en målsiffra (befintlig logik). **Mini:** schema bara. **Set-baserat:**
  definierad men stubbad renderare (söm för framtiden).

### Build (multi-app-loop)

`build_site.py` refaktoreras till en funktion av *(en åldersgrupps lag + matcher +
standings) → output-mapp*. Loopa över åldersgrupperna. Varje får:

- **`index.html`** — samma beprövade UI (schema/tabeller/slutspel), renderare enligt format.
- **`manifest.json`** — unik identitet: `name:"AHK U14"`, `scope:"./"`, `start_url:"."`
  (relativt → löser till `/u14/`), AHK-ikoner, tema.
- **`sw.js`** — **unikt cache-namn per app** (`ahk-u14-v1`…). Kritiskt: alla appar delar
  origin; ett delat cache-namn skulle låta dem skriva över varandras offline-cache.
- Egna **`.ics`**-kalendrar per lag.

Ikoner återanvänds (allt är Alingsås AHK), kopieras per app-mapp; hemskärmen skiljer
apparna åt via **namnet**.

### Hubb

Nya repots rot = enkel katalogsida (samma AHK-stil) som listar åldersgrupps-apparna
(namn, speldagar, antal lag), var och en länkar in i sin undermapp. **U15 → gamla
repots URL.**

### CI / Actions

Nya repot får egen workflow (cron + manuell): klubbkods-hämtning → multi-app-build →
commit-bara-vid-ändring. Samma mönster som dagens robot.

## Säkerhet för den installerade U15-appen

- Gamla repot/URL **rörs aldrig** i grundflödet; den relativa scopen (`start_url:"."`,
  `scope:"./"`) binder installen till URL-sökvägen, som består.
- Nya repot är en **separat Pages-sajt** → kan fysiskt inte kollidera med installen.
- **Byt aldrig namn på gamla repot** medan U15-installen lever — det ändrar Pages-URL:en
  och bryter appens scope. Se [[pages-nojekyll-gotcha]] för andra Pages-fällor.

## Avgränsningar (YAGNI)

- Ingen truppfunktion i nya repots appar v1 (fliken auto-döljs utan data).
- Ingen internationell set/shootout-renderare v1 (sömmen finns).
- Ingen sammanslagen "en app + väljare"-modell.
- Inga åldersmärkta ikoner (namnet räcker).
- Mini: inga resultat/tabeller.

## Öppna verifieringar

- ~~Mini matchlängd för iCal~~ — **löst:** samma 11 min som Classic (arrangörens regler).
- **Färg-härledning** täcker alla suffix som faktiskt dyker upp i klubbens 43 lag.
- **Nya repots namn** + Pages-aktivering.
- Bekräfta att Mini-klasser saknar tabell i API:t (annars döljs fliken ändå automatiskt).
  OBS: Mini *räknar* mål (1 p/mål) — "schema bara" är ett produktval, inte tekniskt
  tvång; kan omprövas om Mini-resultat önskas.

## Implementationsordning (för writing-plans)

1. Config-modul + klubbkodsdriven match-hämtning med åldersgrupp-partition.
2. Generalisering av standings-hämtningen.
3. Format-abstraktion (Classic + Mini; stubbad set-renderare).
4. Multi-app-build + per-app PWA-identitet (unik manifest + cache-namn).
5. Hubb-sida.
6. CI-workflow i nya repot.
