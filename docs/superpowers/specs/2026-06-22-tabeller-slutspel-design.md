# Designdokument: Grupptabeller & slutspelsträd

**Datum:** 2026-06-22
**Projekt:** AHK Åhus Beach 2026 – matchschema (PWA på GitHub Pages)
**Status:** Godkänd design – nästa steg är implementationsplan (writing-plans)

## Bakgrund & mål

Sidan visar idag ett live-uppdaterat **matchschema** för Alingsås HK:s sex lag
(3× P15 + 3× F15) under Åhus Beach Handboll 17–18 juli 2026. Vi vill lägga till två
saker så man kan följa hur det går:

1. **Grupptabeller** för de sex grupper lagen spelar i.
2. **Slutspelsträd** (A/B/C-slutspel per åldersklass), med resultat ifyllda allt
   eftersom matcherna spelas.

Allt ska vara **läsbart på mobilskärm** (primär enhet, ofta i solen på plats) och
drivas av samma robot (GitHub Action) som redan uppdaterar schemat – ingen
klient­hämtning, ingen lokal dator.

## Regelmodell (Åhus Classic)

Detta är **inte** internationell beachhandboll utan *Åhus Classic*: vanlig
målräkning, två halvlekar med 60 s paus emellan.

- **Gruppspel:** kan sluta **oavgjort** (därav O-kolumnen i tabellen).
- **Slutspel:** **sudden death** vid lika → alltid en vinnare/förlorare.

Tabellens ordningsföljd avgörs (enligt cupens regelbok) av: 1) poäng, 2) inbördes
möte-poäng, 3) IM-målskillnad, 4) IM flest mål, 5) målskillnad, 6) flest mål,
7) lottning. **Vi implementerar INTE denna sortering** – se "Tie-breaks" nedan.

## Datakälla (cupmanager results_api)

Bekräftat genom probing mot `ahusbeachhandboll.cupmanager.net/rest/results_api`
(tournamentId = `matches_data.TOURNAMENT_ID` = `70944382`):

- **Grupptabell:** `Division({id})$table` → entitet `Division$ConferenceTable`.
  `rows` ligger i **färdig ställningsordning** (inget `rank`-fält – radens index =
  placering). Radfält: `name, played, won, tied, lost, goalsWon, goalsLost,
  points`, samt `im_*` (inbördes möte) och **`targetStage`** per placering → den
  slutspels-stage placeringen går till.
- **Sex distinkta grupper** (en per lag):
  P15 Vit→Grupp 1, P15 Blå→Grupp 2, P15 Orange→Grupp 4 (10 lag/grupp);
  F15 Blå→Grupp 1, F15 Gul→Grupp 3, F15 Vit→Grupp 4 (9 lag/grupp).
- **Slutspel:** per åldersklass tre stages → `Playoff`-divisioner som heter
  **A-Slutspel / B-Slutspel / C-Slutspel**. För P15 (10-lagsgrupper) är splitten
  plats 1–4 / 5–7 / 8–10. **Splitten läses ur datan** (`targetStage` per rad), inte
  hårdkodas – F15 har 9-lagsgrupper och kan ha annan split.
- **Slutspelsmatcher** är seedade med platshållare ("1:an i Grupp 1"). Ronder:
  Åttondelar → Kvart → Semi → Final. Match-entiteten bär `result`
  (→ `MatchResult`), `winner` och `loser`, plus `nextMatchWinner` /
  `nextMatchLoser` (driver trädets kopplingar). Resultat = vanlig målsiffra.
- **Schemat sköter sig självt:** verifierat att `fetch_matches.py` redan ser alla
  ~989 slutspelsmatcher via `MatchWindow`. När en grupp spelats klar byts
  platshållaren mot riktigt lag-id och nuvarande `build_matches` plockar
  automatiskt in matchen i schemat. **Ingen extra åtgärd krävs för det.**

## Arkitektur

Bygger vidare på befintligt mönster (separata `fetch_*`-skript som skriver JSON,
`build_site.py` som bakar in i `index.html`). Två nya enheter:

### `fetch_standings.py` (nytt)
Körs i samma GitHub Action som `fetch_matches.py`. Hämtar för de sex grupperna:
- tabellrader i API-ordning + härled `tier` (A/B/C) per rad ur `targetStage`,
- markera vilka rader som är Alingsås (via `schedule.TEAM_BY_ID`),
- per åldersklass: de tre slutspelsträden (ronder, matcher, platshållartexter,
  bana/tid, samt `result`/`winner`/`loser` när de finns).

Skriver **`standings.json`** endast vid faktisk ändring (hash-jämförelse, samma
mönster som `matches.json`). Vid hämtningsfel lämnas filen orörd.

**Datamodell (skiss, detaljeras i planen):**
```
{ meta: {...},
  groups: [ { klass, division_id, name, alingsas_team_ids,
              tiers: [{tier, name, positions:[..]}],
              rows: [ {pos, name, is_alingsas, played, won, tied, lost,
                       goals_for, goals_against, diff, points, tier} ] } ],
  playoffs: [ { klass,
                tiers: [ {tier, name, division_id,
                          rounds: [ {name, matches: [
                            {id, time, day, bana,
                             home:{label, team_id, group, seed, is_alingsas, score},
                             away:{...}, winner, src_home, src_away} ]} ] } ] } ] }
```

### `build_site.py` (utökas)
- Läser `standings.json` (om den finns; annars döljs Tabeller/Slutspel-flikarna
  graciöst).
- Bakar in standings-datan som JSON i sidan, parallellt med matchdatan.
- Lägger till toppnavigationen och de två nya vyerna (se nedan).

## UI

### Toppnavigation
Tre flikar: **`Schema · Tabeller · Slutspel`**. Alla tre lyder samma befintliga
lagfilter (Alla / P15 / F15 / per-lag), som redan sparas i localStorage + speglas i
URL-hash. Schemat är default. Aktiv flik kan också speglas i URL för delbarhet.

### Tabeller-vyn (layout "Variant A – kompakt")
Kolumner: **`# · Lag · S · ±M · P`**. Alingsås-raden markeras i lagets färg. Mellan
slutspelsnivåerna ritas en tunn **färgad avdelarrad** (A=guld, B=hav, C=dämpad)
med etikett ("B-Slutspel ↓"). Filterstyrt:
- ett lag valt → den gruppens tabell,
- P15 / F15 → de tre tabellerna i klassen,
- Alla → alla sex tabeller.

### Slutspel-vyn (layout "Variant 3 – klassiskt träd")
Klassiskt vänster-till-höger-träd (Åttondel → Kvart → Semi → Final) som går att
**dra runt med fingret** (pan) eftersom det är bredare än mobilskärmen. **A/B/C
väljs med flikar** högst upp; default-fliken är den nivå det filtrerade laget
projiceras till just nu (annars A). Ett filtrerat lags platshållare/väg markeras i
lagfärg. När en match är spelad fylls **resultatet** i och **vinnaren visas i
accentfärg, förloraren överstruken** – allt ur API:ts `winner`/`loser`, vi räknar
inget själva (sudden death inräknat).

Implementationsdetalj för planen: pan görs med vanilla JS/CSS (overflow + pointer-
drag), inga beroenden – i linje med projektets noll-beroende-stil. Trädets
kopplingar byggs från `nextMatchWinner`/`nextMatchLoser`.

## Tie-breaks (medvetet beslut)

Vi **speglar API:ts radordning** och bygger **ingen egen tie-break-logik**.
Motivering: `Division$table` är samma källa som den officiella publika tabellen
(`publicResultsUrl`), så ordningen är redan regelbokskorrekt inklusive inbördes
möte och lottning (steg 7, som bara arrangören kan göra). Egen sortering skulle
riskera att säga emot den officiella tabellen.

**Skyddsräcke:** `fetch_standings.py` assertar att raderna är icke-växande i poäng
och loggar varning annars (fångar om cupmanager någon gång skulle returnera
osorterat). Dessutom dubbelkollas ordningen mot de första riktiga resultaten under
turneringshelgen.

## Felhantering & robusthet

- Hämtningsfel → `standings.json` lämnas orörd, bygget kör på befintlig data
  (samma som `fetch_matches.py`).
- Saknas `standings.json` helt → Tabeller/Slutspel-flikarna visas inte (schemat
  fungerar som idag).
- Innan turneringen startat är alla rader 0 och träden består av platshållare –
  vyerna ska se vettiga ut även då (inga resultat, ingen "vinnare").

## Test / verifiering

- Enhetstest av härledningen tier-ur-`targetStage` och Alingsås-markering mot
  inspelad API-fixtur.
- Verifiera tabell-förhandssortering mot första riktiga resultaten (eller en
  inspelad färdigspelad grupp) – bekräfta att två poänglika lag ligger sorterade
  efter inbördes möte.
- Rendera sidan med tom/saknad `standings.json` och bekräfta graciös nedgradering.

## Avgränsningar (YAGNI)

- Ingen visning av inbördes-möte-statistik i tabellen (datan finns om det önskas
  senare).
- Ingen spelarstatistik, inga kort/fair play-kolumner i v1.
- Ingen egen sorteringslogik (se Tie-breaks).

## Beslutslogg

| Fråga | Beslut |
|---|---|
| Integration | Tre toppflikar `Schema · Tabeller · Slutspel`, delar lagfiltret |
| Tabell-layout | Variant A – kompakt (`# · Lag · S · ±M · P`), A/B/C-avdelare |
| Slutspels-layout | Variant 3 – klassiskt träd, dra-med-finger, A/B/C-flikar |
| Resultat | Ifyllt ur API; vinnare i accentfärg, förlorare överstruken |
| Tie-breaks | Spegla API-ordning, ingen egen logik, bygg-tids-skyddsräcke |
| Datadrift | Nytt `fetch_standings.py` i samma Action → `standings.json` |
