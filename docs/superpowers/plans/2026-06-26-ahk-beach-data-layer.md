# AHK Beach – Data Layer Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the club-code-driven data layer for the new evergreen `ahk-beach` repo: fetch all Alingsås HK teams/matches/standings from cupmanager, partition by age group, and write a verifiable `data.json`.

**Architecture:** A fresh, isolated repo (no shared runtime with the live `alingsas-ahus-beach-2026` repo). Pure derivation functions (parse category → gender/age/rule/suffix; color rule; rule profile) are unit-tested offline against synthetic entity stores. A thin network client pages the cupmanager API; all transform logic operates on an in-memory entity store so it is testable without the network.

**Tech Stack:** Python 3 (stdlib only: `urllib`, `re`, `json`, `hashlib`), pytest. Mirrors the proven patterns in the existing repo (`fetch_matches.py`, `fetch_standings.py`, `schedule.py`) but generalized.

**Scope of this plan:** data layer only. Plan 2 = multi-app build + hub. Plan 3 = CI workflow + repo creation + Pages. This plan produces a committed `data.json` (via `fetch_data.main`) plus the **pure** standings transforms (`winner_side`, `table_row`, `bucket_groups`). The standings *network wiring* and `standings.json` output are deferred to Plan 2 — `table_row`/`bucket_groups` are intentionally orphan (tested, not yet called) until then.

**Deferred to Plan 2/3 (from the Plan 1 final review — honor these):**
- **Plan 2 build must honor `profile.has_results`** — `data.json` carries `result` for Mini groups too, so the renderer must hide Mini results (spec: Mini = schema bara).
- **Plan 2 standings wiring** — build `club_team_ids` + `tier_by_stage` and the Division$ConferenceTable/Playoff queries; reuse the transforms from Task 11; write `standings.json` bucketed by `age_slug`.
- **Plan 2 per-team rendering note** — intra-club matches (both sides are club teams) attribute to the *home* team's slug/color only; fine for age-group bucketing, relevant only if rendering per-team schedules.
- **Plan 3 CI** — `main()` always exits 0 (so the cron never breaks on a transient outage); add alerting on a distinct "fetched but 0 teams" condition if desired. `data.json` is a committed artifact; the hash-guard keeps no-op commits out.

**Reference (read before starting):**
- Spec: `docs/superpowers/specs/2026-06-26-klubbapp-evergreen-design.md`
- Existing proven code to generalize (in the current repo, for reference only — do NOT import): `fetch_matches.py`, `fetch_standings.py`, `schedule.py`.

**Key API facts (verified 2026-06-26):**
- API: `https://ahusbeachhandboll.cupmanager.net/rest/results_api/call?call={urlencoded}&lang=sv&tournamentId=70944382`
- Club code: `NameClub({id:73383031})`. Each Team entity has `club.href` → that ref.
- Team entity `name`: `{fullName, suffix, clubName, categoryName}`. `clubName` = display name incl. suffix (e.g. `"Alingsås HK Blå"`). `categoryName` e.g. `"P15 Classic (f. 2011) Blå"`. The `suffix` field is unreliable — parse suffix from `categoryName`.
- Match entity: `start` (epoch ms), `arena` → `completeName` (e.g. `"Bana 7"`), `home`/`away` actors (each has `name` + `team` ref), `division` (has `name` + `category` ref), `result`.
- `name` dicts may carry only `"en"` (not `"sv"`) — fall back.
- Result: `{finished, homeGoals, awayGoals, winByPeriods, pointsPerPeriod, ordinaryPeriodCount, periodScores, penalties}`.
- Rules: Classic & Mini both 2×5 min + 60 s = **11 min**, 1 pt/goal. Mini has **no tables/playoffs**.

---

## File Structure

New repo root: `~/dev/ahk-beach/`

- Create: `config.py` — constants only (tournament id, club id, pages base, UTC offset, color palette/map, club blue, default durations).
- Create: `derive.py` — pure derivation: `slugify`, `parse_category`, `derive_group_colors`. No I/O.
- Create: `rules.py` — `rule_profile(rule)` → format flags (duration, has_results, has_tables, has_playoffs).
- Create: `api.py` — entity helpers (`ref_id`, `name_of`, `store_get`) + network (`call`, `fetch_store`).
- Create: `fetch_data.py` — `build_team_registry`, `normalize_match`, `bucket_by_age_group`, `assemble`, `main` → writes `data.json`.
- Create: `fetch_standings.py` — generalize group tables + A/B/C tiers, bucketed by age group → writes `standings.json`.
- Create: `tests/__init__.py`, `tests/test_derive.py`, `tests/test_rules.py`, `tests/test_api.py`, `tests/test_fetch_data.py`, `tests/test_standings.py`.
- Create: `pytest.ini`, `.gitignore`, `README.md` (stub).
- Copy (static assets, from current repo): `icon-192.png`, `icon-512.png`, `icon-512-maskable.png`, `icon-180.png`, `favicon-32.png`, `Alingsas_HK_logo.svg`.

---

## Task 1: Scaffold the `ahk-beach` repo

**Files:**
- Create: `~/dev/ahk-beach/pytest.ini`, `.gitignore`, `README.md`, `tests/__init__.py`
- Copy: icon/logo assets from `~/dev/ahusbeach/`

*(Scaffolding/config — no TDD.)*

- [ ] **Step 1: Create the repo and directories**

```bash
mkdir -p ~/dev/ahk-beach/tests
cd ~/dev/ahk-beach
git init -q
```

- [ ] **Step 2: Copy static assets from the current repo**

```bash
cd ~/dev/ahk-beach
cp ~/dev/ahusbeach/icon-192.png ~/dev/ahusbeach/icon-512.png \
   ~/dev/ahusbeach/icon-512-maskable.png ~/dev/ahusbeach/icon-180.png \
   ~/dev/ahusbeach/favicon-32.png ~/dev/ahusbeach/Alingsas_HK_logo.svg .
```

- [ ] **Step 3: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 4: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 5: Write `README.md` (stub)**

```markdown
# AHK Beach

Evergreen klubb-app för Alingsås HK på Åhus Beach Handboll — en installerbar
PWA per åldersgrupp (U8–U18). Data hämtas från cupmanager på klubbkod
(NameClub 73383031) och byggs till statiska appar på GitHub Pages.

U15 (P15+F15) bor kvar i det separata repot `alingsas-ahus-beach-2026`.

Se `docs/` i `alingsas-ahus-beach-2026` för design/spec.
```

- [ ] **Step 6: Create `tests/__init__.py` (empty) and commit**

```bash
cd ~/dev/ahk-beach
touch tests/__init__.py
git add -A
git commit -q -m "chore: scaffold ahk-beach repo (assets, pytest, gitignore)"
```

---

## Task 2: `derive.slugify`

**Files:**
- Create: `~/dev/ahk-beach/derive.py`
- Test: `~/dev/ahk-beach/tests/test_derive.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_derive.py
# -*- coding: utf-8 -*-
import derive


def test_slugify_lowercases_and_hyphenates():
    assert derive.slugify("Lag Blå") == "lag-bla"


def test_slugify_maps_swedish_vowels():
    assert derive.slugify("Gulö Ärt") == "gulo-art"


def test_slugify_strips_non_alnum_and_collapses():
    assert derive.slugify("AHK  2 / B") == "ahk-2-b"


def test_slugify_empty_is_empty():
    assert derive.slugify("") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_derive.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'derive'`

- [ ] **Step 3: Write minimal implementation**

```python
# derive.py
# -*- coding: utf-8 -*-
"""Rena härledningsfunktioner: slug, kategoritolkning, färgregel. Ingen I/O."""

import re

_SV = str.maketrans({"å": "a", "ä": "a", "ö": "o", "é": "e",
                     "Å": "a", "Ä": "a", "Ö": "o", "É": "e"})


def slugify(s):
    s = (s or "").translate(_SV).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_derive.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add derive.py tests/test_derive.py
git commit -q -m "feat: derive.slugify"
```

---

## Task 3: `derive.parse_category`

**Files:**
- Modify: `~/dev/ahk-beach/derive.py`
- Test: `~/dev/ahk-beach/tests/test_derive.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_derive.py

def test_parse_category_classic_with_color():
    p = derive.parse_category("P15 Classic (f. 2011) Blå")
    assert p == {"gender": "P", "age": 15, "rule": "Classic", "suffix": "Blå"}


def test_parse_category_mini_numeric_suffix():
    p = derive.parse_category("F11 Mini (f. 2015) 1")
    assert p == {"gender": "F", "age": 11, "rule": "Mini", "suffix": "1"}


def test_parse_category_no_suffix():
    p = derive.parse_category("P10 Mini (f. 2016)")
    assert p == {"gender": "P", "age": 10, "rule": "Mini", "suffix": ""}


def test_parse_category_multiword_suffix():
    p = derive.parse_category("P8 Mini (f. 2018) Lag Blå")
    assert p == {"gender": "P", "age": 8, "rule": "Mini", "suffix": "Lag Blå"}


def test_parse_category_unknown_rule_falls_back():
    p = derive.parse_category("P14 Beachhandboll (f. 2012) 2")
    assert p["gender"] == "P" and p["age"] == 14 and p["suffix"] == "2"
    assert p["rule"] == "Beachhandboll"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_derive.py -k parse_category -q`
Expected: FAIL — `AttributeError: module 'derive' has no attribute 'parse_category'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to derive.py

_CAT_RE = re.compile(r"^\s*([PF])(\d+)\s+(\S+)\s*\(f\.\s*\d{4}\)\s*(.*?)\s*$")


def parse_category(category_name):
    """'P15 Classic (f. 2011) Blå' -> {gender, age, rule, suffix}.

    Suffix tolkas ur kategorinamnet (team-entitetens suffix-fält är opålitligt).
    """
    name = category_name or ""
    m = _CAT_RE.match(name)
    if m:
        return {"gender": m.group(1), "age": int(m.group(2)),
                "rule": m.group(3), "suffix": m.group(4)}
    # Fallback: minst kön + ålder ur inledningen.
    g = name[:1] if name[:1] in ("P", "F") else "?"
    am = re.search(r"[PF](\d+)", name)
    rm = re.search(r"\b(Classic|Mini|Beachhandboll)\b", name)
    return {"gender": g, "age": int(am.group(1)) if am else 0,
            "rule": rm.group(1) if rm else "?", "suffix": ""}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_derive.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add derive.py tests/test_derive.py
git commit -q -m "feat: derive.parse_category (gender/age/rule/suffix)"
```

---

## Task 4: `config.py` constants + `derive.derive_group_colors`

**Files:**
- Create: `~/dev/ahk-beach/config.py`
- Modify: `~/dev/ahk-beach/derive.py`
- Test: `~/dev/ahk-beach/tests/test_derive.py`

Implements the locked color rule: one team → club blue; all teams have a color-word suffix → that color; otherwise → palette by index.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_derive.py
import config


def _team(suffix):
    return {"id": hash(suffix) & 0xffff, "suffix": suffix}


def test_colors_single_team_is_club_blue():
    teams = [_team("1")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.CLUB_BLUE


def test_colors_all_color_suffixes_use_color_map():
    teams = [_team("Blå"), _team("Vit"), _team("Orange")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.COLOR_MAP["bla"]
    assert out[teams[1]["id"]] == config.COLOR_MAP["vit"]
    assert out[teams[2]["id"]] == config.COLOR_MAP["orange"]


def test_colors_mixed_suffixes_use_palette_by_index():
    teams = [_team("Blå"), _team("1"), _team("Vit")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.PALETTE[0]
    assert out[teams[1]["id"]] == config.PALETTE[1]
    assert out[teams[2]["id"]] == config.PALETTE[2]


def test_colors_multiword_color_suffix_detected():
    teams = [_team("Lag Blå"), _team("Lag Vit")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.COLOR_MAP["bla"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_derive.py -k colors -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write `config.py`**

```python
# config.py
# -*- coding: utf-8 -*-
"""Konstanter för ahk-beach. Byt TOURNAMENT_ID nästa år → allt funkar igen."""

TOURNAMENT_ID = "70944382"
CLUB_ID = 73383031                       # NameClub({id:73383031}) = Alingsås HK
CLUB_NAME = "Alingsås HK"

PAGES_HOST = "martinwelen.github.io"
PAGES_PATH = "/ahk-beach"
PAGES_BASE = f"https://{PAGES_HOST}{PAGES_PATH}"

UTC_OFFSET_HOURS = 2                      # Åhus i juli = CEST = UTC+2

CLUB_BLUE = "#1f5fbf"                     # klubbens standardfärg (ensamt lag)

# Färgord (slugifierat) → hex. Används när ALLA lag i en grupp har färgsuffix.
COLOR_MAP = {
    "bla": "#1f5fbf",
    "vit": "#c9c2b4",
    "svart": "#23303a",
    "orange": "#e8730c",
    "gul": "#f2bd0c",
    "rod": "#d22f27",
    "gron": "#2f9e44",
    "rosa": "#e864a4",
}

# Distinkta färger för fallback (siffer-/blandade suffix).
PALETTE = ["#1f5fbf", "#e8730c", "#2f9e44", "#d22f27", "#9c36b5", "#f2bd0c"]
```

- [ ] **Step 4: Add `derive_group_colors` to `derive.py`**

```python
# append to derive.py
import config


def _color_word(suffix):
    """Returnerar färgnyckel (COLOR_MAP) om suffixet innehåller ett färgord, annars None."""
    tokens = slugify(suffix).split("-")
    for t in tokens:
        if t in config.COLOR_MAP:
            return t
    return None


def derive_group_colors(teams):
    """teams: lista av dict med 'id' och 'suffix' (en åldersgrupp).

    Regel: ett lag → klubbens blå; alla har färgsuffix → den färgen;
    annars → palett per index. Returnerar {team_id: hexfärg}.
    """
    if len(teams) == 1:
        return {teams[0]["id"]: config.CLUB_BLUE}
    words = [_color_word(t["suffix"]) for t in teams]
    if all(w is not None for w in words):
        return {t["id"]: config.COLOR_MAP[w] for t, w in zip(teams, words)}
    return {t["id"]: config.PALETTE[i % len(config.PALETTE)]
            for i, t in enumerate(teams)}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_derive.py -q`
Expected: PASS (13 passed)

- [ ] **Step 6: Commit**

```bash
cd ~/dev/ahk-beach
git add config.py derive.py tests/test_derive.py
git commit -q -m "feat: config constants + derive_group_colors (locked color rule)"
```

---

## Task 5: `rules.rule_profile`

**Files:**
- Create: `~/dev/ahk-beach/rules.py`
- Test: `~/dev/ahk-beach/tests/test_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rules.py
# -*- coding: utf-8 -*-
import rules


def test_classic_profile():
    p = rules.rule_profile("Classic")
    assert p == {"duration_min": 11, "has_results": True,
                 "has_tables": True, "has_playoffs": True}


def test_mini_profile_schedule_only():
    p = rules.rule_profile("Mini")
    assert p == {"duration_min": 11, "has_results": False,
                 "has_tables": False, "has_playoffs": False}


def test_unknown_rule_defaults_to_full_for_future_formats():
    # Internationellt/okänt: behåll data så den finns när renderaren byggs (Plan 2).
    p = rules.rule_profile("Beachhandboll")
    assert p["has_results"] is True and p["has_tables"] is True
    assert p["duration_min"] == 11
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_rules.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'rules'`

- [ ] **Step 3: Write minimal implementation**

```python
# rules.py
# -*- coding: utf-8 -*-
"""Format-profil per regeltyp. Driver vad datalagret tar med och (i Plan 2) hur
det renderas. Mini = schema bara (inga tabeller/slutspel). Internationellt
behandlas som 'full' tills set/shootout-renderaren byggs (Plan 2)."""

_PROFILES = {
    "Classic": {"duration_min": 11, "has_results": True,
                "has_tables": True, "has_playoffs": True},
    "Mini":    {"duration_min": 11, "has_results": False,
                "has_tables": False, "has_playoffs": False},
}

_DEFAULT = {"duration_min": 11, "has_results": True,
            "has_tables": True, "has_playoffs": True}


def rule_profile(rule):
    return dict(_PROFILES.get(rule, _DEFAULT))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_rules.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add rules.py tests/test_rules.py
git commit -q -m "feat: rules.rule_profile (Classic/Mini + future-format default)"
```

---

## Task 6: `api.py` entity helpers

**Files:**
- Create: `~/dev/ahk-beach/api.py`
- Test: `~/dev/ahk-beach/tests/test_api.py`

Pure helpers operating on an in-memory store. Network functions come in Task 11.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
# -*- coding: utf-8 -*-
import api


def test_ref_id_extracts_int():
    assert api.ref_id({"href": "Team({id:74384993})"}) == 74384993


def test_ref_id_nameclub():
    assert api.ref_id({"href": "NameClub({id:73383031})"}) == 73383031


def test_ref_id_missing_is_none():
    assert api.ref_id(None) is None
    assert api.ref_id({"href": "no-id-here"}) is None


def test_name_of_prefers_sv_then_en():
    assert api.name_of({"name": {"sv": "Grupp 4", "en": "Group 4"}}) == "Grupp 4"
    assert api.name_of({"name": {"en": "Grupp 4"}}) == "Grupp 4"


def test_name_of_missing_is_empty():
    assert api.name_of({}) == ""


def test_store_get_resolves_href():
    store = {"Team({id:5})": {"id": 5}}
    assert api.store_get(store, {"href": "Team({id:5})"}) == {"id": 5}
    assert api.store_get(store, {"href": "Team({id:9})"}) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'api'`

- [ ] **Step 3: Write minimal implementation**

```python
# api.py
# -*- coding: utf-8 -*-
"""cupmanager-API: rena entitetshjälpare + tunn nätverkshämtning."""

import re
import json
import time
import urllib.parse
import urllib.request

import config

_API = ("https://ahusbeachhandboll.cupmanager.net/rest/results_api/call"
        "?call={call}&lang=sv&tournamentId=" + config.TOURNAMENT_ID)


def ref_id(node):
    if isinstance(node, dict):
        m = re.search(r"id:(\d+)", node.get("href", ""))
        if m:
            return int(m.group(1))
    return None


def name_of(entity):
    n = entity.get("name") if isinstance(entity, dict) else None
    if isinstance(n, dict):
        return n.get("sv") or n.get("en") or ""
    return n or ""


def store_get(store, ref):
    return store.get(ref.get("href") if isinstance(ref, dict) else ref, {})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_api.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add api.py tests/test_api.py
git commit -q -m "feat: api.py entity helpers (ref_id, name_of, store_get)"
```

---

## Task 7: `fetch_data.build_team_registry`

**Files:**
- Create: `~/dev/ahk-beach/fetch_data.py`
- Test: `~/dev/ahk-beach/tests/test_fetch_data.py`

Filters Team entities by club, derives metadata, groups by age, assigns slugs + colors.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch_data.py
# -*- coding: utf-8 -*-
import fetch_data
import config


def _team(tid, category_name, club_id=config.CLUB_ID):
    return {
        "__typename": "Team", "id": tid,
        "club": {"href": f"NameClub({{id:{club_id}}})"},
        "name": {"clubName": f"Alingsås HK {category_name.split(') ')[-1]}",
                 "categoryName": category_name},
    }


def test_registry_filters_to_club_only():
    store = {
        "Team({id:1})": _team(1, "P15 Classic (f. 2011) Blå"),
        "Team({id:2})": _team(2, "P15 Classic (f. 2011) Vit", club_id=999),
    }
    reg = fetch_data.build_team_registry(store)
    assert [t["id"] for t in reg] == [1]


def test_registry_derives_fields_and_age_slug():
    store = {"Team({id:1})": _team(1, "P15 Classic (f. 2011) Blå")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["gender"] == "P" and t["age"] == 15 and t["rule"] == "Classic"
    assert t["suffix"] == "Blå" and t["age_slug"] == "u15"
    assert t["slug"] == "u15-p-bla"


def test_registry_assigns_colors_per_age_group():
    store = {
        "Team({id:1})": _team(1, "P15 Classic (f. 2011) Blå"),
        "Team({id:2})": _team(2, "P15 Classic (f. 2011) Orange"),
        "Team({id:3})": _team(3, "P15 Classic (f. 2011) VIT"),
    }
    reg = {t["id"]: t for t in fetch_data.build_team_registry(store)}
    assert reg[1]["color"] == config.COLOR_MAP["bla"]
    assert reg[2]["color"] == config.COLOR_MAP["orange"]
    assert reg[3]["color"] == config.COLOR_MAP["vit"]


def test_registry_single_team_age_group_is_club_blue():
    store = {"Team({id:9})": _team(9, "P18 Classic (f. 2008) 1")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["color"] == config.CLUB_BLUE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_fetch_data.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# fetch_data.py
# -*- coding: utf-8 -*-
"""Klubbkodsdriven datahämtning → data.json (lag + matcher per åldersgrupp)."""

from collections import defaultdict

import api
import derive


def build_team_registry(store):
    """Alla klubbens lag ur en entitets-store, med härledd metadata + färg.

    Returnerar en lista av dict:
      {id, gender, age, rule, suffix, team_name, age_slug, slug, color}
    """
    teams = []
    for e in store.values():
        if e.get("__typename") != "Team":
            continue
        if api.ref_id(e.get("club")) != __import__("config").CLUB_ID:
            continue
        nm = e.get("name") or {}
        p = derive.parse_category(nm.get("categoryName", ""))
        teams.append({
            "id": e["id"],
            "gender": p["gender"], "age": p["age"], "rule": p["rule"],
            "suffix": p["suffix"],
            "team_name": nm.get("clubName", ""),
            "age_slug": f"u{p['age']}",
            "slug": derive.slugify(f"u{p['age']}-{p['gender']}-{p['suffix'] or 'lag'}"),
        })

    # Färg tilldelas per åldersgrupp (regeln behöver hela gruppen).
    by_age = defaultdict(list)
    for t in teams:
        by_age[t["age_slug"]].append(t)
    for group in by_age.values():
        colors = derive.derive_group_colors(group)
        for t in group:
            t["color"] = colors[t["id"]]

    teams.sort(key=lambda t: (t["age"], t["gender"], t["slug"]))
    return teams
```

> Note: `__import__("config").CLUB_ID` avoids a circular-looking import ordering issue; alternatively add `import config` at the top. Prefer the explicit import — replace the line `if api.ref_id(...) != __import__("config").CLUB_ID:` and add `import config` to the top imports. Use:
> ```python
> import api
> import config
> import derive
> ```
> and `if api.ref_id(e.get("club")) != config.CLUB_ID:`

- [ ] **Step 4: Apply the import note, then run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_fetch_data.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add fetch_data.py tests/test_fetch_data.py
git commit -q -m "feat: fetch_data.build_team_registry (club filter + meta + colors)"
```

---

## Task 8: `fetch_data.normalize_match` + `bucket_by_age_group`

**Files:**
- Modify: `~/dev/ahk-beach/fetch_data.py`
- Test: `~/dev/ahk-beach/tests/test_fetch_data.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_fetch_data.py

def _match(mid, start_ms, bana, home_actor, away_actor, division_name,
           home_team_id, away_team_id, result=None):
    return {
        "__typename": "Match", "id": mid, "start": start_ms,
        "arena": {"href": f"Arena({{id:{mid}}})"},
        "home": {"href": f"H({mid})"}, "away": {"href": f"A({mid})"},
        "division": {"href": f"D({mid})"}, "result": {"href": f"R({mid})"},
        "_arena": {"completeName": f"Bana {bana}"},
        "_home": {"name": {"en": home_actor}, "team": {"href": f"Team({{id:{home_team_id}}})"}},
        "_away": {"name": {"en": away_actor}, "team": {"href": f"Team({{id:{away_team_id}}})"}},
        "_division": {"name": {"sv": division_name}},
        "_result": result or {"finished": False},
    }


def _store_for_match(m):
    """Lägg refererade entiteter i storen under sina href:ar."""
    mid = m["id"]
    return {
        f"Arena({{id:{mid}}})": m["_arena"],
        f"H({mid})": m["_home"], f"A({mid})": m["_away"],
        f"D({mid})": m["_division"], f"R({mid})": m["_result"],
        f"Match({{id:{mid}}})": m,
    }


def test_normalize_match_basic_fields():
    m = _match(100, 1783585800000, 7, "Alingsås HK Blå", "Lugi HF 3",
               "Grupp 2", home_team_id=1, away_team_id=50)
    store = _store_for_match(m)
    reg_by_id = {1: {"id": 1, "slug": "u15-p-bla", "age_slug": "u15",
                     "gender": "P", "rule": "Classic", "color": "#1f5fbf"}}
    nm = fetch_data.normalize_match(m, store, reg_by_id)
    assert nm["age_slug"] == "u15"
    assert nm["slug"] == "u15-p-bla"
    assert nm["bana"] == 7
    assert nm["hemma"] == "Alingsås HK Blå"
    assert nm["borta"] == "Lugi HF 3"
    assert nm["hb"] == "Hemma"
    assert nm["mots"] == "Lugi HF 3"
    assert nm["grupp"] == "Grupp 2"
    assert nm["tid"] == "10:30"          # 1783585800000 ms = 08:30 UTC = 10:30 CEST
    assert nm["result"] is None


def test_normalize_match_away_side_and_result():
    res = {"finished": True, "homeGoals": 9, "awayGoals": 14}
    m = _match(101, 1783585800000, 3, "IFK Kristianstad 2", "Alingsås HK Blå",
               "Grupp 2", home_team_id=50, away_team_id=1, result=res)
    store = _store_for_match(m)
    reg_by_id = {1: {"id": 1, "slug": "u15-p-bla", "age_slug": "u15",
                     "gender": "P", "rule": "Classic", "color": "#1f5fbf"}}
    nm = fetch_data.normalize_match(m, store, reg_by_id)
    assert nm["hb"] == "Borta"
    assert nm["mots"] == "IFK Kristianstad 2"
    assert nm["result"] == {"hg": 9, "ag": 14}


def test_bucket_by_age_group_groups_and_sorts():
    reg = [
        {"id": 1, "slug": "u15-p-bla", "age_slug": "u15", "age": 15,
         "gender": "P", "rule": "Classic", "team_name": "Alingsås HK Blå",
         "suffix": "Blå", "color": "#1f5fbf"},
    ]
    m_late = _match(2, 1783589400000, 8, "Alingsås HK Blå", "X", "Grupp 2", 1, 50)
    m_early = _match(1, 1783585800000, 7, "Alingsås HK Blå", "Y", "Grupp 2", 1, 50)
    store = {}
    store.update(_store_for_match(m_late))
    store.update(_store_for_match(m_early))
    groups = fetch_data.bucket_by_age_group(reg, [m_early, m_late], store)
    assert "u15" in groups
    g = groups["u15"]
    assert g["age"] == 15 and g["label"] == "U15" and g["rule"] == "Classic"
    assert [t["id"] for t in g["teams"]] == [1]
    assert [mm["start_ms"] for mm in g["matches"]] == [1783585800000, 1783589400000]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_fetch_data.py -k "normalize or bucket" -q`
Expected: FAIL — `AttributeError: module 'fetch_data' has no attribute 'normalize_match'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to fetch_data.py
import re
from datetime import datetime, timezone, timedelta

import rules

_CEST = timezone(timedelta(hours=config.UTC_OFFSET_HOURS))
_SV_DAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
_SV_MONTHS = ["", "januari", "februari", "mars", "april", "maj", "juni",
              "juli", "augusti", "september", "oktober", "november", "december"]


def _bana_num(field):
    m = re.search(r"(\d+)", field or "")
    return int(m.group(1)) if m else (field or "")


def _extract_result(res):
    if not res or not res.get("finished"):
        return None
    hg, ag = res.get("homeGoals"), res.get("awayGoals")
    if hg is None or ag is None:
        return None
    return {"hg": hg, "ag": ag}


def normalize_match(e, store, reg_by_id):
    """En Match-entitet → normaliserad dict, knuten till klubbens lag.

    Returnerar None om matchen inte rör något av klubbens lag.
    """
    home_a = api.store_get(store, e.get("home", {}))
    away_a = api.store_get(store, e.get("away", {}))
    hid = api.ref_id(home_a.get("team")) if home_a else None
    aid = api.ref_id(away_a.get("team")) if away_a else None
    team = reg_by_id.get(hid) or reg_by_id.get(aid)
    if not team:
        return None

    hb = "Hemma" if hid in reg_by_id else "Borta"
    hemma = api.name_of(home_a)
    borta = api.name_of(away_a)
    div = api.store_get(store, e.get("division", {}))
    grupp = api.name_of(div)
    bana = _bana_num(api.store_get(store, e.get("arena", {})).get("completeName", ""))
    start_ms = e["start"]
    dt = datetime.fromtimestamp(start_ms / 1000, _CEST)
    result = _extract_result(api.store_get(store, e.get("result", {})))

    return {
        "age_slug": team["age_slug"], "slug": team["slug"],
        "gender": team["gender"], "rule": team["rule"], "color": team["color"],
        "datum": f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}",
        "dag": _SV_DAYS[dt.weekday()],
        "tid": f"{dt.hour:02d}:{dt.minute:02d}",
        "bana": bana, "grupp": grupp,
        "hemma": hemma, "borta": borta,
        "mots": borta if hb == "Hemma" else hemma,
        "hb": hb, "result": result,
        "start_ms": start_ms,
        "start_iso": dt.isoformat(timespec="minutes"),
        "day_label": f"{_SV_DAYS[dt.weekday()]} {dt.day} {_SV_MONTHS[dt.month]}",
    }


def bucket_by_age_group(registry, match_entities, store):
    """Bygger {age_slug: {age,label,rule,profile,teams,matches}} ur lag + matcher."""
    reg_by_id = {t["id"]: t for t in registry}
    groups = {}
    for t in registry:
        a = t["age_slug"]
        if a not in groups:
            groups[a] = {"age": t["age"], "label": f"U{t['age']}",
                         "rule": t["rule"], "profile": rules.rule_profile(t["rule"]),
                         "teams": [], "matches": []}
        groups[a]["teams"].append(t)

    for e in match_entities:
        nm = normalize_match(e, store, reg_by_id)
        if nm and nm["age_slug"] in groups:
            groups[nm["age_slug"]]["matches"].append(nm)

    for g in groups.values():
        g["matches"].sort(key=lambda m: (m["start_ms"], str(m["bana"])))
    return groups
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_fetch_data.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add fetch_data.py tests/test_fetch_data.py
git commit -q -m "feat: fetch_data.normalize_match + bucket_by_age_group"
```

---

## Task 9: `fetch_data.assemble` + hash-guarded write + `main`

**Files:**
- Modify: `~/dev/ahk-beach/fetch_data.py`
- Test: `~/dev/ahk-beach/tests/test_fetch_data.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_fetch_data.py
import json
import os


def test_assemble_shapes_doc_with_meta_and_groups():
    groups = {"u15": {"age": 15, "label": "U15", "rule": "Classic",
                      "profile": {"duration_min": 11}, "teams": [], "matches": []}}
    doc = fetch_data.assemble(groups, generated="2026-06-26T00:00:00Z", seq=1)
    assert doc["meta"]["club_id"] == config.CLUB_ID
    assert doc["meta"]["seq"] == 1
    assert "data_hash" in doc["meta"]
    assert doc["groups"]["u15"]["label"] == "U15"


def test_data_hash_stable_regardless_of_meta():
    groups = {"u15": {"age": 15, "label": "U15", "rule": "Classic",
                      "profile": {}, "teams": [], "matches": []}}
    a = fetch_data.assemble(groups, generated="2026-01-01T00:00:00Z", seq=1)
    b = fetch_data.assemble(groups, generated="2026-09-09T00:00:00Z", seq=2)
    assert a["meta"]["data_hash"] == b["meta"]["data_hash"]


def test_write_if_changed_writes_then_skips(tmp_path):
    groups = {"u15": {"age": 15, "label": "U15", "rule": "Classic",
                      "profile": {}, "teams": [], "matches": []}}
    path = os.path.join(tmp_path, "data.json")
    wrote1 = fetch_data.write_if_changed(groups, path,
                                         generated="2026-06-26T00:00:00Z", seq=1)
    wrote2 = fetch_data.write_if_changed(groups, path,
                                         generated="2026-06-27T00:00:00Z", seq=2)
    assert wrote1 is True and wrote2 is False
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["meta"]["seq"] == 1     # andra körningen skrev inte över
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_fetch_data.py -k "assemble or hash or write_if_changed" -q`
Expected: FAIL — `AttributeError: module 'fetch_data' has no attribute 'assemble'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to fetch_data.py
import os
import json
import hashlib


def _hash_groups(groups):
    key = []
    for a in sorted(groups):
        g = groups[a]
        key.append((a, g["rule"], [t["id"] for t in g["teams"]],
                    [(m["slug"], m["start_ms"], str(m["bana"]),
                      m["hemma"], m["borta"], m["grupp"], m.get("result"))
                     for m in g["matches"]]))
    return hashlib.sha256(json.dumps(key, ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def assemble(groups, generated, seq):
    return {
        "meta": {
            "source": f"cupmanager API (klubbkod {config.CLUB_ID}, "
                      f"tournamentId {config.TOURNAMENT_ID})",
            "club_id": config.CLUB_ID,
            "generated": generated, "seq": seq,
            "data_hash": _hash_groups(groups),
        },
        "groups": groups,
    }


def write_if_changed(groups, path, generated, seq):
    """Skriver data.json bara om innehållet ändrats. Returnerar True om skrivet."""
    new_hash = _hash_groups(groups)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("meta", {}).get("data_hash") == new_hash:
                return False
        except Exception:
            pass
    doc = assemble(groups, generated, seq)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_fetch_data.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add fetch_data.py tests/test_fetch_data.py
git commit -q -m "feat: fetch_data.assemble + hash-guarded write_if_changed"
```

---

## Task 10: `api` network (`call`, `fetch_store`) + `fetch_data.main`

**Files:**
- Modify: `~/dev/ahk-beach/api.py`, `~/dev/ahk-beach/fetch_data.py`
- Test: `~/dev/ahk-beach/tests/test_api.py`

Network is thin and side-effecting; we test the query-builder purely and keep an opt-in live smoke check.

- [ ] **Step 1: Write the failing test (query builder is pure)**

```python
# append to tests/test_api.py

def test_match_query_includes_tournament_and_paging():
    q = api.match_query(limit=300, offset=600)
    assert "limit:300" in q and "offset:600" in q
    assert "tournamentId:70944382" in q
    assert "MatchWindow" in q and "result:{}" in q
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_api.py -k match_query -q`
Expected: FAIL — `AttributeError: module 'api' has no attribute 'match_query'`

- [ ] **Step 3: Add network + query builder to `api.py`**

```python
# append to api.py

PAGE = 300


def match_query(limit, offset):
    return (
        "MatchWindow({{limit:{l},offset:{o},tournamentId:{t}}})"
        "{{matches:[{{... on Match:{{start:{{}},arena:{{}},"
        "away:{{team:{{}}}},division:{{category:{{}},name:{{}}}},"
        "home:{{team:{{}}}},result:{{}}}}}}]}}"
    ).format(l=limit, o=offset, t=config.TOURNAMENT_ID)


def call(query, retries=4):
    url = _API.format(call=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={
        "accept": "application/json", "user-agent": "ahk-beach-bot/1.0"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:           # nät/transient → backoff och försök igen
            last = e
            time.sleep(2 + 2 * i)
    raise last


def fetch_store():
    """Sidar igenom alla matchfönster → entitets-store {href: entity}."""
    store, offset = {}, 0
    while True:
        resp = call(match_query(PAGE, offset)).get("responses", {})
        page = 0
        for k, v in resp.items():
            if isinstance(v, dict) and isinstance(v.get("entity"), dict):
                store[k] = v["entity"]
                if v["entity"].get("__typename") == "Match":
                    page += 1
        if page < PAGE:
            break
        offset += PAGE
    return store
```

- [ ] **Step 4: Add `main()` to `fetch_data.py`**

```python
# append to fetch_data.py
import sys
from datetime import datetime as _dt, timezone as _tz

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")


def main():
    try:
        store = api.fetch_store()
    except Exception as e:
        print("FEL vid hämtning:", e, "- lämnar data.json orörd")
        return 0
    registry = build_team_registry(store)
    if not registry:
        print("0 lag för klubbkoden - lämnar data.json orörd")
        return 0
    match_entities = [e for e in store.values() if e.get("__typename") == "Match"]
    groups = bucket_by_age_group(registry, match_entities, store)
    now = _dt.now(_tz.utc)
    wrote = write_if_changed(groups, DATA_JSON,
                             generated=now.isoformat(timespec="seconds"),
                             seq=int(now.timestamp()))
    n_t = sum(len(g["teams"]) for g in groups.values())
    n_m = sum(len(g["matches"]) for g in groups.values())
    print(f"{'Skrev' if wrote else 'Ingen ändring;'} {len(groups)} "
          f"åldersgrupper, {n_t} lag, {n_m} matcher"
          + ("" if wrote else " (skrev inte om)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run unit tests, then a live smoke check**

Run: `cd ~/dev/ahk-beach && python3 -m pytest -q`
Expected: PASS (all tests)

Then (network — verifies the real fetch end-to-end):
Run: `cd ~/dev/ahk-beach && python3 fetch_data.py && python3 -c "import json;d=json.load(open('data.json'));print(sorted(d['groups']));print('lag', sum(len(g['teams']) for g in d['groups'].values()))"`
Expected: prints ~9–10 age-group slugs (`u8 u10 u11 u12 u13 u14 u15 u16 u17 u18`) and **43** teams total. (U15 will appear here too — it is excluded from the *build* in Plan 2, not from the data.)

- [ ] **Step 6: Commit**

```bash
cd ~/dev/ahk-beach
git add api.py fetch_data.py tests/test_api.py
git commit -q -m "feat: api network fetch_store + fetch_data.main → data.json"
```

---

## Task 11: `fetch_standings.py` (group tables + A/B/C tiers, bucketed by age)

**Files:**
- Create: `~/dev/ahk-beach/fetch_standings.py`
- Test: `~/dev/ahk-beach/tests/test_standings.py`

Generalizes the existing standings transform to all club divisions, bucketed by age group, honoring `rule_profile` (skip Mini). Mirrors the proven mapping in the current repo's `fetch_standings.py` (read it for reference). This task implements the pure transforms; the network call reuses `api.call`. Only `winner_side` and `table_row` normalization + bucketing are needed for Plan 1; the full division/playoff query wiring can mirror the current repo.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_standings.py
# -*- coding: utf-8 -*-
import fetch_standings as fs


def test_winner_side_home_away_none():
    assert fs.winner_side({"finished": True, "homeGoals": 14, "awayGoals": 11}) == "home"
    assert fs.winner_side({"finished": True, "homeGoals": 9, "awayGoals": 12}) == "away"
    assert fs.winner_side({"finished": False, "homeGoals": 0, "awayGoals": 0}) is None
    assert fs.winner_side({"finished": True, "homeGoals": 10, "awayGoals": 10}) is None


def test_table_row_normalizes_and_flags_club():
    row = {
        "name": {"sv": "Alingsås HK Blå"}, "team": {"href": "Team({id:1})"},
        "played": 3, "won": 2, "tied": 0, "lost": 1,
        "goalsWon": 40, "goalsLost": 33, "points": 4,
        "targetStage": {"href": "Stage({categoryId:1,stageId:70944379,tournamentId:2})"},
    }
    out = fs.table_row(row, club_team_ids={1}, tier_by_stage={70944379: "A-Slutspel"})
    assert out["team_id"] == 1 and out["is_alingsas"] is True
    assert out["diff"] == 7 and out["points"] == 4 and out["tier"] == "A-Slutspel"


def test_bucket_groups_by_age_slug_skips_mini():
    groups_in = [
        {"age_slug": "u15", "rule": "Classic", "name": "Grupp 2", "rows": []},
        {"age_slug": "u10", "rule": "Mini", "name": "Grupp 1", "rows": []},
    ]
    out = fs.bucket_groups(groups_in)
    assert "u15" in out and "u10" not in out      # Mini har inga tabeller
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_standings.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_standings'`

- [ ] **Step 3: Write minimal implementation**

```python
# fetch_standings.py
# -*- coding: utf-8 -*-
"""Grupptabeller + A/B/C-slutspelsträd per åldersgrupp (klubbkodsdrivet).

Speglar API:ts tabellordning (ingen egen tie-break). Mini hoppas över
(inga tabeller). Mirror av proven logik i alingsas-ahus-beach-2026."""

import re

import api
import rules


def winner_side(result):
    if not result or not result.get("finished"):
        return None
    hg, ag = result.get("homeGoals"), result.get("awayGoals")
    if hg is None or ag is None or hg == ag:
        return None
    return "home" if hg > ag else "away"


def _stage_id(href):
    m = re.search(r"stageId:(\d+)", href or "")
    return int(m.group(1)) if m else None


def table_row(row, club_team_ids, tier_by_stage):
    tid = api.ref_id(row.get("team"))
    gf = row.get("goalsWon", 0) or 0
    ga = row.get("goalsLost", 0) or 0
    sid = _stage_id((row.get("targetStage") or {}).get("href", ""))
    return {
        "name": api.name_of(row), "team_id": tid,
        "is_alingsas": tid in club_team_ids,
        "played": row.get("played", 0) or 0,
        "won": row.get("won", 0) or 0, "tied": row.get("tied", 0) or 0,
        "lost": row.get("lost", 0) or 0,
        "goals_for": gf, "goals_against": ga, "diff": gf - ga,
        "points": row.get("points", 0) or 0,
        "tier": tier_by_stage.get(sid),
    }


def bucket_groups(groups):
    """Lista av grupp-dict (med age_slug + rule) → {age_slug: [grupper]}.

    Hoppar över regeltyper utan tabeller (Mini)."""
    out = {}
    for g in groups:
        if not rules.rule_profile(g["rule"])["has_tables"]:
            continue
        out.setdefault(g["age_slug"], []).append(g)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/dev/ahk-beach && python3 -m pytest tests/test_standings.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd ~/dev/ahk-beach
git add fetch_standings.py tests/test_standings.py
git commit -q -m "feat: fetch_standings transforms (winner_side, table_row, bucket_groups)"
```

> **Note for Plan 2/3:** the full standings *network wiring* (Division$ConferenceTable + Playoff stage queries, tier-by-stage assembly) mirrors the current repo's `fetch_standings.py` and writes `standings.json` bucketed by `age_slug`. It is split out because it needs the live division/stage query shapes; capture it as the first task of Plan 2 (or a dedicated task) once `data.json` is proven, reusing `table_row` and `bucket_groups` here.

---

## Self-Review

**Spec coverage:**
- Klubbkodsdriven data (filter by `CLUB_ID`) → Tasks 7, 10. ✓
- Åldersgrupp-partition (P+F ihop) → Task 8 (`bucket_by_age_group`). ✓
- Färgregel (ett lag→blå; alla färgsuffix→färg; annars palett) → Task 4. ✓
- Format-abstraktion / rule profile (Classic + Mini; future default) → Task 5; applied in Tasks 8, 11. ✓
- Mini = schema bara (no tables/playoffs) → Task 5 flags + Task 11 `bucket_groups` skips Mini. ✓
- Matchtid 11 min (Classic+Mini) → Task 5 `duration_min: 11`. ✓ (consumed by iCal in Plan 2.)
- Generaliserad standings → Task 11 (transforms); network wiring deferred to Plan 2 (noted). ✓
- Config parametriserat (tournament id + club id) → Task 4 `config.py`. ✓
- Isolering (eget repo, ingen delad runtime) → Task 1. ✓
- Multi-app build, per-app PWA-identitet, hubb, CI → **Plans 2 & 3** (out of scope here, by design).

**Placeholder scan:** No TBD/TODO. The one explanatory "Note" (Task 7 import) and the Plan-2 hand-off note (Task 11) are guidance, not code placeholders — the actual code is complete in every step.

**Type consistency:** Registry entry keys (`id, gender, age, rule, suffix, team_name, age_slug, slug, color`) are produced in Task 7 and consumed unchanged in Tasks 8–9. `normalize_match` output keys match the bucket/hash usage in Tasks 8–9. `rule_profile` keys (`duration_min, has_results, has_tables, has_playoffs`) consistent across Tasks 5, 8, 11. `winner_side`/`table_row`/`bucket_groups` signatures match their tests. ✓

**Verification note:** Task 10 Step 5 includes a live end-to-end check asserting ~43 teams across the expected `uXX` slugs — the real proof the data layer works against cupmanager.
