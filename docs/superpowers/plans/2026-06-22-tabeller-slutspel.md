# Grupptabeller & slutspelsträd – Implementationsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lägg till en `standings.json`-datakälla och två nya vyer (Tabeller + Slutspel) på schemasidan, drivna av samma GitHub Action-robot.

**Architecture:** Nytt `fetch_standings.py` hämtar grupptabeller och A/B/C-slutspelsträd från cupmanagers `results_api` (återanvänder hjälpfunktioner ur `fetch_matches.py`), skriver `standings.json` endast vid ändring. `build_site.py` bakar in datan och renderar tre toppflikar (`Schema · Tabeller · Slutspel`) som delar det befintliga lagfiltret. Tabellordningen speglas från API:t – ingen egen tie-break-logik.

**Tech Stack:** Python 3.12 (stdlib `urllib`, `re`, `json`, `hashlib`), pytest 9, vanilla JS/CSS i `build_site.py`-mallen (noll beroenden, som resten av projektet).

---

## Filstruktur

| Fil | Ansvar |
|---|---|
| `fetch_standings.py` (ny) | Hämta + normalisera tabeller och slutspelsträd → `standings.json`. Rena transformfunktioner + tunn `main()`. |
| `standings.json` (ny, genereras) | De sex gruppernas tabeller + de tre slutspelsträden per åldersklass. |
| `build_site.py` (ändras) | Läs `standings.json`, baka in som JSON, rendera flik-nav + Tabeller-vy + Slutspel-vy. |
| `.github/workflows/update.yml` (ändras) | Kör `fetch_standings.py`; trigga bygge när `matches.json` ELLER `standings.json` ändrats. |
| `tests/` (ny) | pytest-enheter för transformfunktionerna + bygg-output-assertions. |

**Återanvänds från `fetch_matches.py`:** `call(query)`, `name_of(entity)`, `ref_id(node)`, `bana_num(field)`, `fetch_store()`. Importeras som `import fetch_matches as fmx`.

**Datamodell `standings.json`:**
```json
{
  "meta": {"source": "...", "generated": "ISO", "seq": 0, "data_hash": "..."},
  "groups": [
    {"klass": "P15", "division_id": 82146197, "name": "Grupp 1",
     "tiers": [{"tier": "A-Slutspel", "from": 1, "to": 4}],
     "rows": [
       {"pos": 1, "name": "H43 Lund HF 1", "team_id": 74504786, "is_alingsas": false,
        "played": 4, "won": 4, "tied": 0, "lost": 0,
        "goals_for": 60, "goals_against": 41, "diff": 19, "points": 8, "tier": "A-Slutspel"}
     ]}
  ],
  "playoffs": [
    {"klass": "P15", "tiers": [
      {"tier": "A-Slutspel", "division_id": 82146483, "rounds": [
        {"name": "Åttondelar", "matches": [
          {"id": 81462146, "start": 1784741400000, "bana": 11, "round": "Åttondelar",
           "home": {"label": "1:an i Grupp 1", "team_id": null, "is_alingsas": false, "goals": null},
           "away": {"label": "4:an i Grupp 3", "team_id": null, "is_alingsas": false, "goals": null},
           "winner": null}
        ]}
      ]}
    ]}
  ]
}
```

---

## Task 1: Testskelett + projektets första pytest

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_standings.py`
- Create: `pytest.ini`

- [ ] **Step 1: Skapa pytest-konfig**

Skapa `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 2: Skapa tom testpaketsfil**

Skapa `tests/__init__.py` (tom fil).

- [ ] **Step 3: Skriv ett sanity-test**

Skapa `tests/test_standings.py`:
```python
# -*- coding: utf-8 -*-
"""Enhetstester för fetch_standings transformfunktioner (offline, syntetiska entiteter)."""


def test_sanity():
    assert True
```

- [ ] **Step 4: Kör och verifiera grönt**

Run: `python -m pytest -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add pytest.ini tests/__init__.py tests/test_standings.py
git commit -m "test: lägg till pytest-skelett"
```

---

## Task 2: `winner_side` – härled vinnare ur målsiffror

Vinnaren härleds ur `MatchResult` (`homeGoals`/`awayGoals`/`finished`) i stället för det tomma `winner`-objektet. Sudden death-resultatet ligger redan i slutsiffran, så detta gäller även slutspel.

**Files:**
- Create: `fetch_standings.py`
- Test: `tests/test_standings.py`

- [ ] **Step 1: Skriv de failande testerna**

Lägg till i `tests/test_standings.py`:
```python
import fetch_standings as fs


def test_winner_side_home():
    assert fs.winner_side({"finished": True, "homeGoals": 14, "awayGoals": 11}) == "home"


def test_winner_side_away():
    assert fs.winner_side({"finished": True, "homeGoals": 9, "awayGoals": 12}) == "away"


def test_winner_side_unfinished_is_none():
    assert fs.winner_side({"finished": False, "homeGoals": 0, "awayGoals": 0}) is None


def test_winner_side_missing_result_is_none():
    assert fs.winner_side(None) is None


def test_winner_side_tie_is_none():
    # Slutspel kan inte sluta lika (sudden death), men var defensiv.
    assert fs.winner_side({"finished": True, "homeGoals": 10, "awayGoals": 10}) is None
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_standings.py -q`
Expected: FAIL – `ModuleNotFoundError: No module named 'fetch_standings'`

- [ ] **Step 3: Skapa `fetch_standings.py` med minimal implementation**

Skapa `fetch_standings.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hämtar Alingsås HK:s grupptabeller och A/B/C-slutspelsträd från cupmanagers
publika API och skriver standings.json. Körs av GitHub Action (cron).

Speglar API:ts tabellordning – ingen egen tie-break-logik (se designdok).
Skriver bara om standings.json när datan FAKTISKT ändrats (hash-jämförelse).
"""

import re


def winner_side(result):
    """Returnerar 'home'/'away' för en avgjord match, annars None.

    Härleds ur målsiffrorna (sudden death-resultatet ligger i slutsiffran),
    inte ur API:ts winner-objekt som är tomt tills matchen rapporterats.
    """
    if not result or not result.get("finished"):
        return None
    hg, ag = result.get("homeGoals"), result.get("awayGoals")
    if hg is None or ag is None or hg == ag:
        return None
    return "home" if hg > ag else "away"
```

- [ ] **Step 4: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_standings.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add fetch_standings.py tests/test_standings.py
git commit -m "feat: winner_side härleder vinnare ur målsiffror"
```

---

## Task 3: Tabellrad + tier-mappning + sorterings-skyddsräcke

**Files:**
- Modify: `fetch_standings.py`
- Test: `tests/test_standings.py`

- [ ] **Step 1: Skriv de failande testerna**

Lägg till i `tests/test_standings.py`:
```python
def _row(name, tid, played, won, tied, lost, gf, ga, points, stage_id):
    """Bygger en syntetisk Division$ConferenceTableRow."""
    return {
        "name": {"sv": name}, "team": {"href": f"Team({{id:{tid}}})"},
        "played": played, "won": won, "tied": tied, "lost": lost,
        "goalsWon": gf, "goalsLost": ga, "points": points,
        "targetStage": {"href": f"Stage({{categoryId:1,stageId:{stage_id},tournamentId:2}})"},
    }


def test_stage_id_extracts_int():
    assert fs._stage_id("Stage({categoryId:1,stageId:70944379,tournamentId:2})") == 70944379


def test_stage_id_missing_is_none():
    assert fs._stage_id("") is None


def test_table_row_maps_fields_and_tier():
    tier_by_stage = {379: "A-Slutspel"}
    r = fs.table_row(_row("Alingsås HK VIT", 74904168, 4, 3, 0, 1, 55, 44, 6, 379),
                     alingsas_ids={74904168}, tier_by_stage=tier_by_stage)
    assert r["name"] == "Alingsås HK VIT"
    assert r["team_id"] == 74904168
    assert r["is_alingsas"] is True
    assert r["played"] == 4 and r["won"] == 3 and r["tied"] == 0 and r["lost"] == 1
    assert r["goals_for"] == 55 and r["goals_against"] == 44
    assert r["diff"] == 11
    assert r["points"] == 6
    assert r["tier"] == "A-Slutspel"


def test_table_row_non_alingsas():
    r = fs.table_row(_row("H43 Lund HF 1", 74504786, 4, 4, 0, 0, 60, 41, 8, 379),
                     alingsas_ids={74904168}, tier_by_stage={379: "A-Slutspel"})
    assert r["is_alingsas"] is False


def test_tier_spans_groups_consecutive_positions():
    rows = [
        {"tier": "A-Slutspel"}, {"tier": "A-Slutspel"},
        {"tier": "A-Slutspel"}, {"tier": "A-Slutspel"},
        {"tier": "B-Slutspel"}, {"tier": "B-Slutspel"}, {"tier": "B-Slutspel"},
        {"tier": "C-Slutspel"}, {"tier": "C-Slutspel"}, {"tier": "C-Slutspel"},
    ]
    spans = fs.tier_spans(rows)
    assert spans == [
        {"tier": "A-Slutspel", "from": 1, "to": 4},
        {"tier": "B-Slutspel", "from": 5, "to": 7},
        {"tier": "C-Slutspel", "from": 8, "to": 10},
    ]


def test_is_descending_points_true():
    assert fs.is_descending_points([{"points": 8}, {"points": 6}, {"points": 6}, {"points": 1}]) is True


def test_is_descending_points_false():
    assert fs.is_descending_points([{"points": 3}, {"points": 6}]) is False
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_standings.py -q`
Expected: FAIL – `AttributeError: module 'fetch_standings' has no attribute '_stage_id'`

- [ ] **Step 3: Implementera funktionerna**

Lägg till i `fetch_standings.py` (efter `winner_side`):
```python
import fetch_matches as fmx


def _stage_id(href):
    m = re.search(r"stageId:(\d+)", href or "")
    return int(m.group(1)) if m else None


def table_row(row, alingsas_ids, tier_by_stage):
    """Normaliserar en Division$ConferenceTableRow till vår radmodell."""
    tid = fmx.ref_id(row.get("team"))
    gf = row.get("goalsWon", 0) or 0
    ga = row.get("goalsLost", 0) or 0
    sid = _stage_id((row.get("targetStage") or {}).get("href", ""))
    return {
        "name": fmx.name_of(row),
        "team_id": tid,
        "is_alingsas": tid in alingsas_ids,
        "played": row.get("played", 0) or 0,
        "won": row.get("won", 0) or 0,
        "tied": row.get("tied", 0) or 0,
        "lost": row.get("lost", 0) or 0,
        "goals_for": gf,
        "goals_against": ga,
        "diff": gf - ga,
        "points": row.get("points", 0) or 0,
        "tier": tier_by_stage.get(sid),
    }


def tier_spans(rows):
    """Sammanfattar vilka placeringar (1-baserat) som hör till varje slutspelsnivå."""
    spans = []
    for i, r in enumerate(rows, 1):
        t = r.get("tier")
        if spans and spans[-1]["tier"] == t:
            spans[-1]["to"] = i
        else:
            spans.append({"tier": t, "from": i, "to": i})
    return spans


def is_descending_points(rows):
    """Skyddsräcke: API:ts ordning ska vara icke-växande i poäng."""
    pts = [r.get("points", 0) for r in rows]
    return all(pts[i] >= pts[i + 1] for i in range(len(pts) - 1))
```

- [ ] **Step 4: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_standings.py -q`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add fetch_standings.py tests/test_standings.py
git commit -m "feat: tabellrad-normalisering, tier-spans och sorterings-skyddsräcke"
```

---

## Task 4: Slutspelsmatch-normalisering (bracket_match)

**Files:**
- Modify: `fetch_standings.py`
- Test: `tests/test_standings.py`

- [ ] **Step 1: Skriv de failande testerna**

Lägg till i `tests/test_standings.py`:
```python
def _playoff_store():
    """Syntetisk store för en spelad slutspelsmatch (hemmavinst 15-12)."""
    return {
        "Match({id:900})": {
            "__typename": "Match", "id": 900, "start": 1784741400000,
            "home": {"href": "MatchActor({actor:\"home\",id:900})"},
            "away": {"href": "MatchActor({actor:\"away\",id:900})"},
            "arena": {"href": "Arena({id:11})"},
            "round": {"href": "Round({id:5})"},
            "result": {"href": "MatchResult({id:900})"},
        },
        "MatchActor({actor:\"home\",id:900})": {
            "__typename": "MatchActor", "name": {"sv": "Alingsås HK VIT"},
            "team": {"href": "Team({id:74904168})"}},
        "MatchActor({actor:\"away\",id:900})": {
            "__typename": "MatchActor", "name": {"sv": "Lugi HF 2"},
            "team": {"href": "Team({id:77344845})"}},
        "Arena({id:11})": {"__typename": "Arena", "fieldName": "Bana 11"},
        "Round({id:5})": {"__typename": "Round", "name": {"sv": "Kvartsfinal"}},
        "MatchResult({id:900})": {
            "__typename": "MatchResult", "finished": True,
            "homeGoals": 15, "awayGoals": 12},
    }


def test_bracket_match_finished_home_win():
    store = _playoff_store()
    m = fs.bracket_match(store["Match({id:900})"], store, alingsas_ids={74904168})
    assert m["id"] == 900
    assert m["bana"] == 11
    assert m["round"] == "Kvartsfinal"
    assert m["home"]["label"] == "Alingsås HK VIT"
    assert m["home"]["is_alingsas"] is True
    assert m["home"]["goals"] == 15
    assert m["away"]["label"] == "Lugi HF 2"
    assert m["away"]["goals"] == 12
    assert m["winner"] == "home"


def test_bracket_match_placeholder_unplayed():
    """Oavgjord seedmatch: platshållarnamn, inga mål, ingen vinnare."""
    store = {
        "Match({id:901})": {
            "__typename": "Match", "id": 901, "start": 1784741400000,
            "home": {"href": "MatchActor({actor:\"home\",id:901})"},
            "away": {"href": "MatchActor({actor:\"away\",id:901})"},
            "arena": {"href": "Arena({id:12})"},
            "round": {"href": "Round({id:6})"},
            "result": {"href": "MatchResult({id:901})"},
        },
        "MatchActor({actor:\"home\",id:901})": {
            "__typename": "MatchActor", "name": {"sv": "1:an i Grupp 1"}, "team": None},
        "MatchActor({actor:\"away\",id:901})": {
            "__typename": "MatchActor", "name": {"sv": "4:an i Grupp 3"}, "team": None},
        "Arena({id:12})": {"__typename": "Arena", "fieldName": "Bana 12"},
        "Round({id:6})": {"__typename": "Round", "name": {"sv": "Åttondelar"}},
        "MatchResult({id:901})": {"__typename": "MatchResult", "finished": False,
                                  "homeGoals": 0, "awayGoals": 0},
    }
    m = fs.bracket_match(store["Match({id:901})"], store, alingsas_ids={74904168})
    assert m["home"]["label"] == "1:an i Grupp 1"
    assert m["home"]["team_id"] is None
    assert m["home"]["is_alingsas"] is False
    assert m["home"]["goals"] is None
    assert m["winner"] is None
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_standings.py -q`
Expected: FAIL – `AttributeError: module 'fetch_standings' has no attribute 'bracket_match'`

- [ ] **Step 3: Implementera `bracket_match`**

Lägg till i `fetch_standings.py`:
```python
def _get(store, ref):
    return store.get(ref.get("href")) if isinstance(ref, dict) else None


def bracket_match(m, store, alingsas_ids):
    """Normaliserar en slutspelsmatch (Match-entitet + store) till vår modell."""
    home = _get(store, m.get("home")) or {}
    away = _get(store, m.get("away")) or {}
    arena = _get(store, m.get("arena")) or {}
    rnd = _get(store, m.get("round")) or {}
    result = _get(store, m.get("result")) or {}
    side = winner_side(result)

    def actor(a):
        tid = fmx.ref_id(a.get("team")) if isinstance(a.get("team"), dict) else None
        goals = None
        if result.get("finished"):
            goals = result.get("homeGoals") if a is home else result.get("awayGoals")
        return {
            "label": fmx.name_of(a),
            "team_id": tid,
            "is_alingsas": tid in alingsas_ids if tid else False,
            "goals": goals,
        }

    return {
        "id": m.get("id"),
        "start": m.get("start"),
        "bana": fmx.bana_num(arena.get("fieldName", "")),
        "round": fmx.name_of(rnd),
        "home": actor(home),
        "away": actor(away),
        "winner": side,
    }
```

- [ ] **Step 4: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_standings.py -q`
Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add fetch_standings.py tests/test_standings.py
git commit -m "feat: bracket_match normaliserar slutspelsmatcher med resultat"
```

---

## Task 5: Gruppera matcher till ronder (group_rounds)

**Files:**
- Modify: `fetch_standings.py`
- Test: `tests/test_standings.py`

- [ ] **Step 1: Skriv de failande testerna**

Lägg till i `tests/test_standings.py`:
```python
def test_group_rounds_orders_by_first_start():
    matches = [
        {"round": "Final", "start": 400, "id": 4},
        {"round": "Åttondelar", "start": 100, "id": 1},
        {"round": "Åttondelar", "start": 100, "id": 2},
        {"round": "Semifinal", "start": 300, "id": 3},
        {"round": "Kvartsfinal", "start": 200, "id": 5},
    ]
    rounds = fs.group_rounds(matches)
    assert [r["name"] for r in rounds] == ["Åttondelar", "Kvartsfinal", "Semifinal", "Final"]
    assert [m["id"] for m in rounds[0]["matches"]] == [1, 2]
    assert len(rounds) == 4


def test_group_rounds_sorts_matches_within_round_by_start_then_id():
    matches = [
        {"round": "Åttondelar", "start": 100, "id": 9},
        {"round": "Åttondelar", "start": 100, "id": 2},
        {"round": "Åttondelar", "start": 50, "id": 7},
    ]
    rounds = fs.group_rounds(matches)
    assert [m["id"] for m in rounds[0]["matches"]] == [7, 2, 9]
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_standings.py -q`
Expected: FAIL – `AttributeError: module 'fetch_standings' has no attribute 'group_rounds'`

- [ ] **Step 3: Implementera `group_rounds`**

Lägg till i `fetch_standings.py`:
```python
def group_rounds(matches):
    """Grupperar normaliserade matcher per rond, ordnade efter rondens första start.
    Matcher inom en rond sorteras på (start, id)."""
    by_round = {}
    for m in matches:
        by_round.setdefault(m["round"], []).append(m)
    rounds = []
    for name, ms in by_round.items():
        ms.sort(key=lambda x: (x.get("start") or 0, x.get("id") or 0))
        rounds.append({"name": name, "matches": ms, "_first": ms[0].get("start") or 0})
    rounds.sort(key=lambda r: r["_first"])
    for r in rounds:
        del r["_first"]
    return rounds
```

- [ ] **Step 4: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_standings.py -q`
Expected: `16 passed`

- [ ] **Step 5: Commit**

```bash
git add fetch_standings.py tests/test_standings.py
git commit -m "feat: group_rounds ordnar slutspelsmatcher per rond"
```

---

## Task 6: Nätverkslager + `standings.json`-skrivning (main)

Denna task binder ihop de rena funktionerna med live-API:t. Den testas inte med enheter (nätverk), utan verifieras manuellt mot live-API:t i Step 4.

**Files:**
- Modify: `fetch_standings.py`

- [ ] **Step 1: Implementera datahämtning och orchestrering**

Lägg till i `fetch_standings.py`:
```python
import os
import sys
import json
import hashlib
from datetime import datetime, timezone

import matches_data as md
import schedule as sch

STANDINGS_JSON = os.path.join(sch.ROOT, "standings.json")
ALINGSAS_IDS = set(sch.TEAM_BY_ID.keys())


def _resolve(query):
    """Kör en API-fråga och returnerar {key: entity} ur svaret."""
    resp = fmx.call(query).get("responses", {})
    return {k: v["entity"] for k, v in resp.items()
            if isinstance(v, dict) and isinstance(v.get("entity"), dict)}


def discover_divisions(store):
    """Hittar {division_id: {'klass','name'}} för de grupper Alingsås-lag spelar i."""
    out = {}
    for e in store.values():
        if e.get("__typename") != "Match":
            continue
        home = store.get(e.get("home", {}).get("href"), {})
        away = store.get(e.get("away", {}).get("href"), {})
        hid, aid = fmx.ref_id(home.get("team")), fmx.ref_id(away.get("team"))
        team = sch.TEAM_BY_ID.get(hid) or sch.TEAM_BY_ID.get(aid)
        if not team:
            continue
        did = fmx.ref_id(e.get("division"))
        if did is None:
            continue
        dent = store.get(e.get("division", {}).get("href"), {})
        out[did] = {"klass": md.short_klass(team["klass"]), "name": fmx.name_of(dent)}
    return out


def fetch_group(division_id, info):
    """Hämtar en grupps tabell + härleder tier per rad. Returnerar group-dict."""
    q = f"Division({{id:{division_id}}})$table"
    ent = _resolve(q).get(q.replace("$table", "") + "$table") \
        or list(_resolve(q).values())[0]
    rows_raw = ent.get("rows", [])
    tier_by_stage = _tier_by_stage_for_category(division_id)
    rows = [table_row(r, ALINGSAS_IDS, tier_by_stage) for r in rows_raw]
    for i, r in enumerate(rows, 1):
        r["pos"] = i
    if not is_descending_points(rows):
        print(f"VARNING: grupp {info['name']} ({division_id}) är inte poäng-sorterad "
              f"från API:t – kontrollera mot officiella tabellen.")
    return {"klass": info["klass"], "division_id": division_id,
            "name": info["name"], "tiers": tier_spans(rows), "rows": rows}


def _category_playoffs(division_id):
    """Returnerar [(stage_id, playoff_division_id, tier_name)] för divisionens kategori."""
    dent = _resolve(f"Division({{id:{division_id}}})")
    div = dent.get(f"Division({{id:{division_id}}})", {})
    cat_href = div.get("category", {}).get("href", "")
    cm = re.search(r"categoryId:(\d+)", cat_href)
    if not cm:
        return []
    cat = cm.group(1)
    # Gruppspels-stagen → dess targetStages är slutspelen. Vi listar kategorins
    # stages via en grupps targetStage-uppsättning i stället: enklare att läsa
    # targetStage-href:arna direkt ur tabellraderna.
    traw = _resolve(f"Division({{id:{division_id}}})$table")
    table = list(traw.values())[0]
    stage_ids = []
    for r in table.get("rows", []):
        sid = _stage_id((r.get("targetStage") or {}).get("href", ""))
        if sid and sid not in stage_ids:
            stage_ids.append(sid)
    out = []
    for sid in stage_ids:
        sresp = _resolve(f"Stage({{categoryId:{cat},stageId:{sid},tournamentId:{md.TOURNAMENT_ID}}})$divisions")
        # $divisions ger en lista av href:ar
        divs = fmx.call(f"Stage({{categoryId:{cat},stageId:{sid},tournamentId:{md.TOURNAMENT_ID}}})$divisions") \
            .get("responses", {})
        for v in divs.values():
            ent = v.get("entity") if isinstance(v, dict) else None
            if isinstance(ent, list):
                for dref in ent:
                    pid = fmx.ref_id(dref)
                    pe = _resolve(f"Division({{id:{pid}}})").get(f"Division({{id:{pid}}})", {})
                    out.append((sid, pid, fmx.name_of(pe)))
    return out


def _tier_by_stage_for_category(division_id):
    return {sid: name for (sid, _pid, name) in _category_playoffs(division_id)}


def fetch_playoffs(division_ids_by_klass):
    """Bygger slutspelsträden per åldersklass (A/B/C)."""
    playoffs = []
    seen_klass = {}
    for did, info in division_ids_by_klass.items():
        klass = info["klass"]
        if klass in seen_klass:
            continue
        seen_klass[klass] = True
        tiers = []
        for (_sid, pid, tier_name) in _category_playoffs(did):
            q = (f"Division({{id:{pid}}}){{matches:[{{... on Match:"
                 f"{{home:{{}},away:{{}},arena:{{}},round:{{}},result:{{}}}}}}]}}")
            store = _resolve(q)
            ms = [bracket_match(e, store, ALINGSAS_IDS)
                  for e in store.values() if e.get("__typename") == "Match"]
            tiers.append({"tier": tier_name, "division_id": pid,
                          "rounds": group_rounds(ms)})
        playoffs.append({"klass": klass, "tiers": tiers})
    return playoffs


def _hash(groups, playoffs):
    key = json.dumps({"g": groups, "p": playoffs}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()


def build():
    store = fmx.fetch_store()
    divisions = discover_divisions(store)
    groups = [fetch_group(did, info) for did, info in divisions.items()]
    groups.sort(key=lambda g: (g["klass"], g["name"]))
    playoffs = fetch_playoffs(divisions)
    return groups, playoffs


def main():
    try:
        groups, playoffs = build()
    except Exception as e:
        print("FEL vid hämtning:", e, "- lämnar standings.json orörd")
        return 0
    if not groups:
        print("0 grupper hittades - lämnar standings.json orörd")
        return 0

    h = _hash(groups, playoffs)
    if os.path.exists(STANDINGS_JSON):
        try:
            with open(STANDINGS_JSON, encoding="utf-8") as f:
                if json.load(f).get("meta", {}).get("data_hash") == h:
                    print(f"Ingen förändring ({len(groups)} grupper). Skriver inte om.")
                    return 0
        except Exception:
            pass

    now = datetime.now(timezone.utc)
    doc = {"meta": {"source": "cupmanager API (Division$table + Playoff)",
                    "generated": now.isoformat(timespec="seconds"),
                    "seq": int(now.timestamp()), "data_hash": h,
                    "groups": len(groups)},
           "groups": groups, "playoffs": playoffs}
    with open(STANDINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"Skrev {len(groups)} grupper + {len(playoffs)} slutspel till standings.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verifiera att enhetstesterna fortfarande är gröna**

Run: `python -m pytest -q`
Expected: `16 passed`

- [ ] **Step 3: Kör mot live-API:t**

Run: `python fetch_standings.py`
Expected: `Skrev 6 grupper + 2 slutspel till standings.json`

- [ ] **Step 4: Inspektera resultatet manuellt**

Run: `python -c "import json; d=json.load(open('standings.json')); g=d['groups'][0]; print(g['klass'], g['name'], [t['tier']+f\" {t['from']}-{t['to']}\" for t in g['tiers']]); print('rader:', len(g['rows']), '| alingsås:', [r['name'] for r in g['rows'] if r['is_alingsas']]); print('slutspel-nivåer:', [t['tier'] for t in d['playoffs'][0]['tiers']]); print('ronder A:', [r['name'] for r in d['playoffs'][0]['tiers'][0]['rounds']])"`
Expected: 6 grupper, varje med en Alingsås-rad; slutspel med A/B/C-Slutspel och ronderna Åttondelar→…→Final.

- [ ] **Step 5: Commit**

```bash
git add fetch_standings.py standings.json
git commit -m "feat: hämta tabeller + slutspelsträd till standings.json"
```

---

## Task 7: `build_site.py` läser standings + renderar flik-nav

**Files:**
- Modify: `build_site.py`
- Test: `tests/test_build_site.py` (ny)

- [ ] **Step 1: Skriv de failande bygg-output-testerna**

Skapa `tests/test_build_site.py`:
```python
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build(tmp_standings=None):
    """Kör build_site.py och returnerar genererad index.html som sträng."""
    env = dict(os.environ)
    subprocess.run([sys.executable, "build_site.py"], cwd=ROOT, check=True, env=env)
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        return f.read()


def test_nav_tabs_present():
    html = _build()
    assert 'id="tab-schema"' in html
    assert 'id="tab-tabeller"' in html
    assert 'id="tab-slutspel"' in html


def test_standings_data_injected():
    html = _build()
    # standings.json finns (skapad i Task 6) → datan ska bäddas in
    assert "__STANDINGS__" not in html  # platshållaren ska vara ersatt
    assert "STANDINGS =" in html
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_build_site.py -q`
Expected: FAIL – `assert 'id="tab-schema"' in html`

- [ ] **Step 3: Lägg till standings-laddning i `build_site.py`**

I `build_site.py`, lägg till efter `import schedule as sch` (rad ~17):
```python

STANDINGS_JSON = os.path.join(sch.ROOT, "standings.json")


def load_standings():
    """Läser standings.json om den finns, annars None (vyer döljs graciöst)."""
    if os.path.exists(STANDINGS_JSON):
        try:
            with open(STANDINGS_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("VARNING: kunde inte läsa standings.json:", e)
    return None
```

- [ ] **Step 4: Lägg till flik-nav i HTML-mallen**

I `build_site.py`, ersätt raden `  <nav class="filters" id="filters" aria-label="Filtrera lag"></nav>` med:
```html
  <nav class="tabs" id="tabs" aria-label="Vyer">
    <button class="tab" id="tab-schema" data-view="schema" aria-pressed="true">Schema</button>
    <button class="tab" id="tab-tabeller" data-view="tabeller" aria-pressed="false" hidden>Tabeller</button>
    <button class="tab" id="tab-slutspel" data-view="slutspel" aria-pressed="false" hidden>Slutspel</button>
  </nav>

  <nav class="filters" id="filters" aria-label="Filtrera lag"></nav>

  <section id="tables" hidden></section>
  <section id="bracket" hidden></section>
```

- [ ] **Step 5: Lägg till tab-CSS**

I `build_site.py`, lägg till i `<style>` precis före `/* filter */`:
```css
/* vy-flikar */
.tabs{display:flex; gap:8px; margin:14px 0 2px}
.tab{flex:0 0 auto; border:1.5px solid var(--ink); background:transparent; color:var(--ink);
  padding:8px 16px; border-radius:999px; font-weight:800; font-size:.9rem; cursor:pointer;
  font-family:inherit; transition:all .15s}
.tab[aria-pressed=true]{background:var(--ink); color:#fff}
.tab[hidden]{display:none}
```

- [ ] **Step 6: Injicera standings-data + tab-JS**

I `build_site.py`, i `<script>`, ersätt raden `const DUR = __DUR_MIN__ * 60000;` med:
```javascript
const DUR = __DUR_MIN__ * 60000;
const STANDINGS = __STANDINGS__;
let view = "schema";
```

Lägg till precis före `render();` (nära slutet av scriptet, raden som först anropar render):
```javascript
// vy-flikar: visa Tabeller/Slutspel bara om data finns
const tabsWrap = document.getElementById("tabs");
const elTables = document.getElementById("tables");
const elBracket = document.getElementById("bracket");
const elList = document.getElementById("list");
const elHero = document.getElementById("hero");
if(STANDINGS && STANDINGS.groups && STANDINGS.groups.length){
  document.getElementById("tab-tabeller").hidden = false;
  if(STANDINGS.playoffs && STANDINGS.playoffs.length) document.getElementById("tab-slutspel").hidden = false;
}
function setView(v){
  view = v;
  for(const t of tabsWrap.children) t.setAttribute("aria-pressed", t.dataset.view===v);
  const schema = v==="schema";
  elHero.hidden = !schema; elList.hidden = !schema;
  elTables.hidden = v!=="tabeller";
  elBracket.hidden = v!=="slutspel";
  if(v==="tabeller") renderTables();
  if(v==="slutspel") renderBracket();
}
tabsWrap.addEventListener("click", e=>{ const b=e.target.closest(".tab"); if(b) setView(b.dataset.view); });
```

In `main()` i `build_site.py`, lägg till i `.replace(...)`-kedjan:
```python
            .replace("__STANDINGS__", json.dumps(load_standings(), ensure_ascii=False))
```

Lägg också till tomma stub-funktioner i scriptet (fylls i Task 8–9), precis efter `setView`-blocket:
```javascript
function renderTables(){ /* Task 8 */ }
function renderBracket(){ /* Task 9 */ }
```

- [ ] **Step 7: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_build_site.py -q`
Expected: `2 passed`

- [ ] **Step 8: Commit**

```bash
git add build_site.py tests/test_build_site.py
git commit -m "feat: flik-nav (Schema/Tabeller/Slutspel) + standings-injektion"
```

---

## Task 8: Tabeller-vyn (Variant A) i `build_site.py`

**Files:**
- Modify: `build_site.py`
- Test: `tests/test_build_site.py`

- [ ] **Step 1: Skriv de failande testerna**

Lägg till i `tests/test_build_site.py`:
```python
def test_tables_render_function_uses_filter_and_tiers():
    html = _build()
    # renderTables ska finnas på riktigt (inte stub) och referera filter + tier-avdelare
    assert "function renderTables()" in html
    assert "tier-row" in html          # CSS-klass för A/B/C-avdelarrad
    assert "matchPass" not in "renderTables"  # sanity, ignoreras
    assert "groupsForFilter" in html   # hjälpare som väljer grupper enligt filter
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_build_site.py::test_tables_render_function_uses_filter_and_tiers -q`
Expected: FAIL

- [ ] **Step 3: Lägg till tabell-CSS**

I `build_site.py` `<style>`, lägg till efter tab-CSS:
```css
/* tabeller */
.gtable{background:var(--paper); border:1px solid var(--line); border-radius:14px;
  padding:10px 12px 6px; margin:14px 0; box-shadow:var(--shadow)}
.gtitle{display:flex; align-items:baseline; gap:8px; margin:2px 2px 8px}
.gtitle .gcls{font-size:.64rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-soft)}
.gtitle .gname{font-family:"Anton"; text-transform:uppercase; font-size:1rem; letter-spacing:.02em}
table.gt{width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums}
.gt th,.gt td{padding:7px 4px; font-size:.82rem; text-align:center}
.gt th{font-size:.6rem; letter-spacing:.05em; text-transform:uppercase; color:var(--ink-soft); font-weight:800; border-bottom:2px solid var(--line)}
.gt th.lt,.gt td.lt{text-align:left}
.gt td{border-bottom:1px solid var(--line)}
.gt .pos{color:var(--ink-soft); font-weight:800; width:26px}
.gt .nm{font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:150px}
.gt .pts{font-family:"Anton"; font-size:1rem}
.gt tr.me td{background:var(--mecol,rgba(20,40,60,.10))}
.gt tr.me .pos{color:var(--meink,var(--ink))}
.tier-row td{padding:4px; border:none}
.tier-row .bar{display:flex; align-items:center; gap:8px; font-size:.6rem; font-weight:800;
  letter-spacing:.08em; text-transform:uppercase}
.tier-row .bar::before,.tier-row .bar::after{content:""; flex:1; height:2px; border-radius:2px; background:currentColor; opacity:.5}
.tierA{color:#c79114} .tierB{color:var(--sea)} .tierC{color:#9a8f86}
.empty-tab{padding:24px 4px; color:var(--ink-soft); text-align:center; font-weight:600}
```

- [ ] **Step 4: Implementera `renderTables` (ersätt stubben)**

I `build_site.py`, ersätt `function renderTables(){ /* Task 8 */ }` med:
```javascript
function tierClass(name){ return name && name[0]==="A" ? "tierA" : name && name[0]==="B" ? "tierB" : "tierC"; }
function groupsForFilter(){
  const gs = STANDINGS.groups;
  if(filter==="all") return gs;
  if(filter==="P15"||filter==="F15") return gs.filter(g=>g.klass===filter);
  const team = TEAMS.find(t=>t.slug===filter);
  if(!team) return gs;
  return gs.filter(g=>g.rows.some(r=>r.is_alingsas && r.name && team));
}
function renderTables(){
  const groups = groupsForFilter();
  if(!groups.length){ elTables.innerHTML='<div class="empty-tab">Inga tabeller för det här filtret.</div>'; return; }
  let html="";
  for(const g of groups){
    const meColor = teamColorForGroup(g);
    html += `<div class="gtable"><div class="gtitle"><span class="gcls">${esc(g.klass==="P15"?"Pojkar 15":"Flickor 15")}</span><span class="gname">${esc(g.name)}</span></div>`;
    html += `<table class="gt"><thead><tr><th>#</th><th class="lt">Lag</th><th>S</th><th>±M</th><th>P</th></tr></thead><tbody>`;
    let curTier=null;
    for(const r of g.rows){
      if(r.tier!==curTier){
        curTier=r.tier;
        if(r.pos!==1) html += `<tr class="tier-row"><td colspan="5"><div class="bar ${tierClass(r.tier)}">${esc(r.tier||"")} ↓</div></td></tr>`;
      }
      const me = r.is_alingsas ? ` class="me" style="--mecol:${hexA(meColor,.16)};--meink:#${meColor}"` : "";
      const diff = (r.diff>0?"+":"") + r.diff;
      html += `<tr${me}><td class="pos">${r.pos}</td><td class="lt nm">${esc(r.name)}</td><td>${r.played}</td><td>${esc(diff)}</td><td class="pts">${r.points}</td></tr>`;
    }
    html += `</tbody></table></div>`;
  }
  elTables.innerHTML = html;
}
function teamColorForGroup(g){
  const me = g.rows.find(r=>r.is_alingsas);
  if(!me) return "13293d";
  const t = TEAMS.find(t=>g.klass + " " === g.klass + " " && me); // fallback
  // matcha via lag-id genom TEAMS-färg: leta team vars slug-klass matchar
  const byKlass = TEAMS.filter(t=>t.klass===g.klass);
  return (byKlass[0] && byKlass[0].color) || "13293d";
}
function hexA(hex,a){ const n=parseInt(hex,16); const r=(n>>16)&255,g=(n>>8)&255,b=n&255; return `rgba(${r},${g},${b},${a})`; }
```

> **Obs för implementeraren:** `teamColorForGroup` ovan är medvetet enkel (väljer klassens första lagfärg). Om flera lag i samma klass har olika färg och du vill ha exakt lagets färg, matcha `me.team_id` mot ett `team_id→color`-index. Lägg i så fall till ett sådant index i `__TEAMS__` (se Task 8b nedan) – men det är valfritt; klassfärg räcker för v1.

- [ ] **Step 5: (Task 8b, valfritt men rekommenderat) exponera team_id→färg**

I `build_site.py` `main()`, utöka `teams_js`:
```python
    teams_js = [{"lag": t["lag"], "slug": t["slug"], "klass": md.short_klass(t["klass"]),
                 "id": t["id"], "color": md.team_colors[t["lag"]]} for t in md.teams]
```
Ersätt sedan `teamColorForGroup` med en exakt variant:
```javascript
function teamColorForGroup(g){
  const me = g.rows.find(r=>r.is_alingsas);
  if(me){ const t = TEAMS.find(t=>t.id===me.team_id); if(t) return t.color; }
  return "13293d";
}
```

- [ ] **Step 6: Koppla filterbyten till aktiv vy**

I `build_site.py`, i pillrets `b.onclick`-hanterare (raden med `filter = id; saveFilter(id); render();`), ersätt med:
```javascript
  b.onclick = () => { filter = id; saveFilter(id); render(); if(view==="tabeller") renderTables(); if(view==="slutspel") renderBracket(); for(const p of fwrap.children) p.setAttribute("aria-pressed", p.dataset.id===id); };
```

- [ ] **Step 7: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_build_site.py -q`
Expected: `3 passed`

- [ ] **Step 8: Manuell visuell kontroll**

Run: `python build_site.py && python -m http.server -d . 8765 >/dev/null 2>&1 & sleep 1; echo "öppna http://localhost:8765 → klicka Tabeller, växla filter"; `
Verifiera: Tabeller-fliken visar grupptabeller, Alingsås-raden färgmarkerad, A/B/C-avdelare mellan nivåerna. Stoppa servern med `kill %1` när klar.

- [ ] **Step 9: Commit**

```bash
git add build_site.py tests/test_build_site.py
git commit -m "feat: Tabeller-vyn (Variant A) med A/B/C-avdelare och lagmarkering"
```

---

## Task 9: Slutspel-vyn (Variant 3, klassiskt träd med pan)

**Files:**
- Modify: `build_site.py`
- Test: `tests/test_build_site.py`

- [ ] **Step 1: Skriv de failande testerna**

Lägg till i `tests/test_build_site.py`:
```python
def test_bracket_render_present():
    html = _build()
    assert "function renderBracket()" in html
    assert "bracket-scroll" in html     # pan-container
    assert "pointerdown" in html        # dra-med-finger
    assert "bm-win" in html             # vinnar-accentklass
    assert "bm-lose" in html            # förlorar-strike-through-klass
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_build_site.py::test_bracket_render_present -q`
Expected: FAIL

- [ ] **Step 3: Lägg till slutspels-CSS**

I `build_site.py` `<style>`, lägg till efter tabell-CSS:
```css
/* slutspelsträd */
.btabs{display:flex; gap:6px; margin:14px 2px 8px}
.btab{font-size:.72rem; font-weight:800; padding:6px 13px; border-radius:999px; border:1.5px solid var(--line); color:var(--ink-soft); background:transparent; cursor:pointer; font-family:inherit}
.btab[aria-pressed=true]{background:var(--ink); border-color:var(--ink); color:#fff}
.bracket-scroll{overflow:hidden; cursor:grab; touch-action:pan-y; border:1px solid var(--line); border-radius:14px; background:var(--paper); box-shadow:var(--shadow); padding:12px}
.bracket-scroll.drag{cursor:grabbing}
.btree{display:flex; gap:16px; min-width:max-content; user-select:none}
.bcol{display:flex; flex-direction:column; justify-content:space-around; gap:10px; min-width:130px}
.bcol .clabel{font-size:.56rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-soft); margin-bottom:2px}
.bm{background:var(--sand); border:1px solid var(--line); border-radius:9px; padding:6px 8px; font-size:.7rem; line-height:1.5}
.bm .row{display:flex; justify-content:space-between; gap:8px}
.bm .row span:first-child{white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.bm.ali{border-color:var(--ink); box-shadow:0 0 0 1.5px var(--c,#999)}
.bm-win{font-weight:800; color:var(--ink)}
.bm-lose{text-decoration:line-through; color:var(--ink-soft); opacity:.75}
.bm .g{font-variant-numeric:tabular-nums; font-weight:800; margin-left:6px}
.empty-tab{padding:24px 4px; color:var(--ink-soft); text-align:center; font-weight:600}
```

- [ ] **Step 4: Implementera `renderBracket` (ersätt stubben)**

I `build_site.py`, ersätt `function renderBracket(){ /* Task 9 */ }` med:
```javascript
let btier = 0;
function playoffForFilter(){
  const ps = STANDINGS.playoffs || [];
  if(!ps.length) return null;
  if(filter==="P15"||filter==="F15") return ps.find(p=>p.klass===filter) || ps[0];
  const team = TEAMS.find(t=>t.slug===filter);
  if(team) return ps.find(p=>p.klass===team.klass) || ps[0];
  return ps[0];
}
function renderBracket(){
  const po = playoffForFilter();
  if(!po || !po.tiers.length){ elBracket.innerHTML='<div class="empty-tab">Inget slutspel att visa.</div>'; return; }
  if(btier>=po.tiers.length) btier=0;
  let html = `<div class="btabs">`;
  po.tiers.forEach((t,i)=>{ html += `<button class="btab" data-i="${i}" aria-pressed="${i===btier}">${esc(t.tier.replace("-Slutspel",""))}</button>`; });
  html += `</div><div class="bracket-scroll" id="bscroll"><div class="btree">`;
  for(const rnd of po.tiers[btier].rounds){
    html += `<div class="bcol"><div class="clabel">${esc(rnd.name)}</div>`;
    for(const m of rnd.matches){
      const hw = m.winner==="home", aw = m.winner==="away";
      const ali = (m.home.is_alingsas||m.away.is_alingsas) ? " ali" : "";
      const c = aliColor(m);
      html += `<div class="bm${ali}" style="--c:#${c}">`+
        bmRow(m.home, hw, aw) + bmRow(m.away, aw, hw) + `</div>`;
    }
    html += `</div>`;
  }
  html += `</div></div>`;
  elBracket.innerHTML = html;
  wirePan(document.getElementById("bscroll"));
  elBracket.querySelector(".btabs").addEventListener("click", e=>{
    const b=e.target.closest(".btab"); if(b){ btier=+b.dataset.i; renderBracket(); }});
}
function bmRow(side, isWin, isLose){
  const cls = isWin ? "bm-win" : (isLose ? "bm-lose" : "");
  const g = side.goals==null ? "" : `<span class="g">${side.goals}</span>`;
  return `<div class="row ${cls}"><span>${esc(side.label||"–")}</span>${g}</div>`;
}
function aliColor(m){
  const s = m.home.is_alingsas ? m.home : (m.away.is_alingsas ? m.away : null);
  if(s){ const t=TEAMS.find(t=>t.id===s.team_id); if(t) return t.color; }
  return "999999";
}
function wirePan(el){
  if(!el) return;
  let down=false, sx=0, sl=0;
  el.addEventListener("pointerdown", e=>{ down=true; sx=e.clientX; sl=el.scrollLeft; el.classList.add("drag"); el.setPointerCapture(e.pointerId); });
  el.addEventListener("pointermove", e=>{ if(down) el.scrollLeft = sl - (e.clientX - sx); });
  el.addEventListener("pointerup", ()=>{ down=false; el.classList.remove("drag"); });
  el.addEventListener("pointercancel", ()=>{ down=false; el.classList.remove("drag"); });
}
```

> **Obs:** `.bracket-scroll` har `overflow:hidden` + manuell `scrollLeft`-styrning via pointer (dra-med-finger). `touch-action:pan-y` låter vertikal sidscroll fungera medan horisontell dragning panorerar trädet.

- [ ] **Step 5: Default-flik = lagets projicerade nivå (valfritt, om ett lag är filtrerat)**

I `renderBracket`, direkt efter `if(btier>=po.tiers.length) btier=0;`, lägg till:
```javascript
  // om ett enskilt lag är filtrerat: öppna den nivå laget projiceras till
  const team = TEAMS.find(t=>t.slug===filter);
  if(team && !renderBracket._userPicked){
    const g = (STANDINGS.groups||[]).find(g=>g.rows.some(r=>r.is_alingsas && r.team_id===team.id));
    const me = g && g.rows.find(r=>r.is_alingsas && r.team_id===team.id);
    if(me && me.tier){ const idx = po.tiers.findIndex(t=>t.tier===me.tier); if(idx>=0) btier=idx; }
  }
```
Och i btabs-klickhanteraren, sätt flaggan:
```javascript
    const b=e.target.closest(".btab"); if(b){ renderBracket._userPicked=true; btier=+b.dataset.i; renderBracket(); }
```

- [ ] **Step 6: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_build_site.py -q`
Expected: `4 passed`

- [ ] **Step 7: Manuell visuell kontroll**

Run: `python build_site.py && python -m http.server -d . 8765 >/dev/null 2>&1 & sleep 1; echo "öppna http://localhost:8765 → Slutspel: dra trädet i sidled, växla A/B/C"; `
Verifiera: trädet går att dra med musen/fingret, A/B/C-flikar växlar, era matcher ramas in i lagfärg. (Resultat/strike-through syns först när matcher spelats – pre-turnering är allt platshållare.) Stoppa: `kill %1`.

- [ ] **Step 8: Commit**

```bash
git add build_site.py tests/test_build_site.py
git commit -m "feat: Slutspel-vyn (klassiskt träd, dra-med-finger, A/B/C, vinnar/förlorar-stil)"
```

---

## Task 10: Graciös nedgradering utan standings.json

**Files:**
- Test: `tests/test_build_site.py`

- [ ] **Step 1: Skriv testet**

Lägg till i `tests/test_build_site.py`:
```python
def test_graceful_without_standings(tmp_path):
    """Utan standings.json ska sidan byggas och Tabeller/Slutspel-flikarna döljas."""
    src = os.path.join(ROOT, "standings.json")
    bak = src + ".bak"
    had = os.path.exists(src)
    if had:
        os.rename(src, bak)
    try:
        html = _build()
        assert 'id="tab-schema"' in html          # schemat finns alltid
        assert "STANDINGS = null" in html         # ingen data injicerad
        # flikarna finns i markup men startar hidden och avslöjas bara av JS om data finns
        assert 'id="tab-tabeller"' in html
    finally:
        if had:
            os.rename(bak, src)
```

- [ ] **Step 2: Kör testet**

Run: `python -m pytest tests/test_build_site.py::test_graceful_without_standings -q`
Expected: `1 passed` (koden från Task 7 hanterar redan `None`)

- [ ] **Step 3: Återställ index.html med data**

Run: `python build_site.py`
Expected: `index.html` byggd med standings igen.

- [ ] **Step 4: Commit**

```bash
git add tests/test_build_site.py
git commit -m "test: verifiera graciös nedgradering utan standings.json"
```

---

## Task 11: Koppla in i GitHub Action-workflow

**Files:**
- Modify: `.github/workflows/update.yml`

- [ ] **Step 1: Lägg till hämtningssteg + utöka ändringsdetektering**

I `.github/workflows/update.yml`, efter steget "Hämta matcher från cupmanager", lägg till:
```yaml
      - name: Hämta tabeller & slutspel från cupmanager
        run: python fetch_standings.py
```

Ersätt steget "Avgör om matchdatan ändrats" med:
```yaml
      - name: Avgör om datan ändrats
        id: changed
        run: |
          if git diff --quiet -- matches.json standings.json; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            echo "matches.json + standings.json oförändrade – hoppar över bygge/commit."
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi
```

- [ ] **Step 2: Verifiera YAML-syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/update.yml')); print('YAML ok')"`
Expected: `YAML ok`
(Om PyYAML saknas: `pip install pyyaml` först.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update.yml
git commit -m "ci: hämta standings.json och trigga bygge när den ändras"
```

---

## Task 12: Resultat på spelade matcher i matchdatan

Schemavyn dämpar redan spelade matcher men visar ingen slutsiffra. Vi hämtar
resultatet (målsiffra) in i `matches.json` så schemat kan visa det.

**Files:**
- Modify: `fetch_matches.py`
- Modify: `schedule.py`
- Test: `tests/test_matches.py` (ny)

- [ ] **Step 1: Skriv de failande testerna**

Skapa `tests/test_matches.py`:
```python
# -*- coding: utf-8 -*-
import fetch_matches as fm
import schedule as sch


def test_extract_result_finished():
    assert fm.extract_result({"finished": True, "homeGoals": 14, "awayGoals": 11}) == {"hg": 14, "ag": 11}


def test_extract_result_unfinished_is_none():
    assert fm.extract_result({"finished": False, "homeGoals": 0, "awayGoals": 0}) is None


def test_extract_result_missing_is_none():
    assert fm.extract_result(None) is None
    assert fm.extract_result({"finished": True, "homeGoals": None, "awayGoals": 3}) is None


def test_make_match_carries_result():
    m = sch.make_match("2026-07-17", "13:45", 7, "P15 Vit", "p15-vit", "P15",
                       "Grupp 1", "Alingsås HK VIT", "IFK Malmö HF", "Hemma",
                       result={"hg": 18, "ag": 9})
    assert m["result"] == {"hg": 18, "ag": 9}


def test_make_match_result_defaults_none():
    m = sch.make_match("2026-07-17", "13:45", 7, "P15 Vit", "p15-vit", "P15",
                       "Grupp 1", "Alingsås HK VIT", "IFK Malmö HF", "Hemma")
    assert m["result"] is None
```

- [ ] **Step 2: Kör testerna, verifiera fail**

Run: `python -m pytest tests/test_matches.py -q`
Expected: FAIL – `AttributeError: module 'fetch_matches' has no attribute 'extract_result'`

- [ ] **Step 3: Lägg till `extract_result` i `fetch_matches.py`**

I `fetch_matches.py`, lägg till efter `bana_num`:
```python
def extract_result(res):
    """Returnerar {'hg','ag'} för en avgjord match, annars None."""
    if not res or not res.get("finished"):
        return None
    hg, ag = res.get("homeGoals"), res.get("awayGoals")
    if hg is None or ag is None:
        return None
    return {"hg": hg, "ag": ag}
```

- [ ] **Step 4: Selektera result i API-frågan + skicka in i make_match**

I `fetch_matches.py`, i `QUERY`, lägg till `result:{{}}` i Match-selektionen:
```python
QUERY = ("MatchWindow({{limit:{limit},offset:{offset},tournamentId:" + md.TOURNAMENT_ID + "}})"
         "{{matches:[{{... on Match:{{arena:{{}},away:{{team:{{}}}},"
         "division:{{category:{{}},name:{{}}}},home:{{team:{{}}}},result:{{}}}}}}]}}")
```

I `build_matches`, efter `dt = sch.parts_from_ms(e["start"])`, lägg till:
```python
        result = extract_result(get(e.get("result", {})))
```
och lägg till `result=result` i `sch.make_match(...)`-anropet.

I `data_hash`, ta med resultatet så ändringar triggar omskrivning:
```python
    key = [(m["slug"], m["start_ms"], m["bana"], m["hemma"], m["borta"], m["grupp"], m.get("result"))
           for m in rows]
```

- [ ] **Step 5: Lägg till `result`-param i `schedule.make_match`**

I `schedule.py`, ändra `make_match`-signaturen och returdicten:
```python
def make_match(datum, tid, bana, lag, slug, klass, grupp, hemma, borta, hb, result=None):
```
och lägg till i den returnerade dicten (t.ex. efter `"hb": hb,`):
```python
        "result": result,
```

- [ ] **Step 6: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_matches.py -q`
Expected: `5 passed`

- [ ] **Step 7: Kör mot live + verifiera att schemat fortfarande byggs**

Run: `python fetch_matches.py && python build_ics.py && python build_excel.py && python build_site.py`
Expected: körs utan fel (resultat = null pre-turnering).

- [ ] **Step 8: Commit**

```bash
git add fetch_matches.py schedule.py tests/test_matches.py matches.json
git commit -m "feat: hämta matchresultat (målsiffra) till matches.json"
```

---

## Task 13: Visa resultat på spelade matcher i schemavyn

**Files:**
- Modify: `build_site.py`
- Test: `tests/test_build_site.py`

- [ ] **Step 1: Skriv testet**

Lägg till i `tests/test_build_site.py`:
```python
def test_schedule_renders_score_markup():
    html = _build()
    assert '"res"' in html or "m.res" in html   # resultatfält propageras till JS
    assert "score" in html                       # score-rendering finns
```

- [ ] **Step 2: Kör testet, verifiera fail**

Run: `python -m pytest tests/test_build_site.py::test_schedule_renders_score_markup -q`
Expected: FAIL

- [ ] **Step 3: Propagera result i `js_matches`**

I `build_site.py` `js_matches`, lägg till i den emittade dicten:
```python
            "res": m.get("result"),
```

- [ ] **Step 4: Lägg till score-CSS**

I `build_site.py` `<style>`, efter `.vs`-reglerna:
```css
.score{display:inline-flex; gap:5px; align-items:baseline; font-family:"Anton"; font-size:1.05rem; margin-top:2px}
.score .x{color:var(--ink-soft); font-size:.8rem}
.score b{font-weight:400}
.score .w{color:var(--sun)}
.score .l{color:var(--ink-soft)}
```

- [ ] **Step 5: Rendera score i matchkortet**

I `build_site.py` `render()`, i `html +=` för `<article class="match ...">`, ersätt vs-raden:
```javascript
          <div class="vs"><span class="${homeAli?"ali":""}">${esc(m.home)}</span> – <span class="${homeAli?"":"ali"}">${esc(m.away)}</span></div>
```
med vs-raden + ett villkorat score-block:
```javascript
          <div class="vs"><span class="${homeAli?"ali":""}">${esc(m.home)}</span> – <span class="${homeAli?"":"ali"}">${esc(m.away)}</span></div>
          ${m.res ? `<div class="score"><b class="${m.res.hg>m.res.ag?'w':m.res.hg<m.res.ag?'l':''}">${m.res.hg}</b><span class="x">–</span><b class="${m.res.ag>m.res.hg?'w':m.res.ag<m.res.hg?'l':''}">${m.res.ag}</b></div>` : ""}
```

- [ ] **Step 6: Kör testerna, verifiera grönt**

Run: `python -m pytest tests/test_build_site.py -q`
Expected: alla gröna (inkl. nya score-testet).

- [ ] **Step 7: Manuell kontroll (med simulerat resultat)**

Run: `python -c "import json,subprocess,sys; d=json.load(open('matches.json')); d['matches'][0]['result']={'hg':18,'ag':9}; json.dump(d,open('matches.json','w'),ensure_ascii=False,indent=1)"; python build_site.py`
Öppna sidan: första matchen ska visa **18–9** med vinnarsiffran i accentfärg.
Återställ sedan: `python fetch_matches.py` (skriver om matches.json från API:t, utan det fejkade resultatet) eller `git checkout matches.json`.

- [ ] **Step 8: Commit**

```bash
git add build_site.py tests/test_build_site.py
git commit -m "feat: visa slutresultat på spelade matcher i schemat"
```

---

## Task 14: Uppdatera README + slutverifiering

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Lägg till en rad om den nya datakällan i README**

I `README.md`, i dataflödes-/filbeskrivningen, lägg till en mening:
```markdown
`fetch_standings.py` hämtar grupptabeller och A/B/C-slutspelsträd → `standings.json`
(speglar cupmanagers tabellordning). `build_site.py` renderar dem som flikarna
**Tabeller** och **Slutspel** på schemasidan. Spelade matcher visar slutresultat
i schemavyn (`fetch_matches.py` hämtar målsiffran).
```

- [ ] **Step 2: Kör hela testsviten**

Run: `python -m pytest -q`
Expected: alla tester gröna (16 standings-enheter + 5 match-enheter + bygg-output/nedgradering ≈ 28 passed).

- [ ] **Step 3: Bygg hela sidan rent och inspektera**

Run: `python fetch_standings.py && python build_site.py`
Expected: `standings.json` + `index.html` genereras utan fel.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: dokumentera fetch_standings.py och de nya vyerna"
```

---

## Självgranskning (genomförd vid planskrivning)

- **Spec-täckning:** Tre flikar (Task 7) ✓, Variant A med A/B/C-avdelare (Task 8) ✓, Variant 3 träd + pan (Task 9) ✓, vinnare/förlorare ur API (Task 2, 9) ✓, spegla API-ordning + skyddsräcke (Task 3, 6) ✓, `fetch_standings.py` i samma Action (Task 11) ✓, graciös nedgradering (Task 7, 10) ✓, targetStage-driven tier-split (Task 3, 6) ✓, Åhus Classic-resultat som målsiffra (Task 2) ✓.
- **Verifiering av API-förhandssortering:** skyddsräcket `is_descending_points` (Task 3) loggar varning; manuell kontroll mot live-API i Task 6 Step 4 och under turneringshelgen.
- **Typkonsistens:** `tier`-strängar ("A-Slutspel" etc.) konsekvent från `fetch_standings` → `standings.json` → `tierClass`/`renderBracket`. Radfält (`pos,name,team_id,is_alingsas,played,won,tied,lost,goals_for,goals_against,diff,points,tier`) identiska i datamodell och konsumtion.
- **Öppen YAGNI-punkt:** `teamColorForGroup`/`aliColor` använder `team_id→color` via `TEAMS` (kräver `id` i `__TEAMS__`, Task 8b) – tas med eftersom flera lag delar klass.
