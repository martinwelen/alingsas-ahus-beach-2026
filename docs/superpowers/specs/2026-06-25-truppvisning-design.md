# Truppvisning – design

**Datum:** 2026-06-25
**Status:** Godkänd design, redo för implementationsplan

## Mål

Visa vilka spelare som ingår i respektive Alingsås-lag i PWA:n. Ingen
frontend för inmatning – spelardata underhålls i en statisk Python-källa och
bakas in i sidan vid bygge, precis som matchdata.

## Datamodell

Ny fil `roster_data.py` – statisk källa (ingen live-hämtning; cupmanager har
ingen spelardata). En dict keyad på lagets `slug` (samma slugs som
`matches_data.teams`):

```python
rosters = {
    "p15-bla": [
        {"namn": "Oskar Viklund", "pos": "UT"},
        {"namn": "Alfred Lindblad", "pos": "MV", "smek": "Affe"},
        ...
    ],
    ...
}
```

Fält per spelare:

| Fält   | Krav     | Beskrivning                          |
|--------|----------|--------------------------------------|
| `namn` | Ja       | Hela namnet                          |
| `nr`   | Valfritt | Tröjnummer (int)                     |
| `pos`  | Valfritt | `"MV"` (målvakt) eller `"UT"` (utespelare) |
| `smek` | Valfritt | Smeknamn                             |

Inga tränare/ledare, inget födelseår. Saknade fält utelämnas helt (visas inte).
Alla sex slugs finns med; lag utan data har tom lista.

### Initial data

Tröjnummer saknas ännu (utelämnas). F15-lagen tomma tills data kommer.

**p15-bla:**
- Oskar Viklund – UT
- Alfred Lindblad – MV – "Affe"
- Theodor Kangas – UT
- Maurits Fridberg – UT – "Marre"
- Filip Holmgren – UT
- Terje Hegge – UT

**p15-vit:**
- Samuel Welén – MV
- Filip Landström – UT
- Sixten Herbertsson – UT
- Filip Larsson – UT
- Liam Bergaoui – UT
- Love Jönsson – UT

**p15-orange:**
- Olle Laas – MV
- Hjalmar Oscarsson – UT – "Hjalle"
- Alexander Westberg – UT
- Theodor Herou – UT
- Fabian Mattsson – UT – "Fabbe"
- Frank Jannerland – UT

**f15-bla, f15-gul, f15-vit:** tomma listor.

## Inbäddning

`build_site.py` får en ny placeholder `__ROSTERS__` som ersätts med
`json.dumps(roster_data.rosters, ensure_ascii=False)` i den befintliga
`.replace()`-kedjan. En `import roster_data`-rad till.

## Presentation – ny flik "Trupp"

- Fjärde flik efter Slutspel i `index.html`. Följer det befintliga lagfiltret
  (knappraden som redan delas av alla vyer).
- Filter = ett lag → den truppens lista. Filter = "Alla" → alla sex trupper
  grupperade per lag, med samma rubrikstil som grupptabellerna.
- **Sortering:** målvakter först, sedan efter tröjnummer stigande; spelare utan
  nummer sist, alfabetiskt på namn.
- **Visning per spelare:** `nr` · `namn` ("smek") · positionsmärke. Tomma fält
  visas inte.
- Tom trupp (men fliken synlig för andra lag) → "Trupp ej publicerad ännu".
- **Fliken döljs helt om ingen trupp har spelare** – samma logik som
  Tabeller/Slutspel-flikarna döljs utan data. Så fliken syns inte förrän minst
  ett lag har spelardata (dvs. den syns direkt med P15-datan ovan).

## Tester

Utöka befintlig testsvit:
- `roster_data` importerbar och är en dict.
- Alla nycklar i `rosters` matchar en `slug` i `matches_data.teams` (och tvärtom
  finns alla slugs som nycklar).
- Varje spelare har ett icke-tomt `namn`; `pos` om satt är `"MV"`/`"UT"`.
- `build_site` producerar output utan kvarvarande `__ROSTERS__`-placeholder.

## Avgränsningar (YAGNI)

- Ingen inmatnings-UI, ingen redigering i appen.
- Ingen live-hämtning.
- Inga tränare/ledare, inget födelseår.
- Ingen export av trupp till Excel/iCal (bara webbpresentation).
