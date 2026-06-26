# AHK Beach – Build & Hub Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Produce `standings.json` (group tables + A/B/C brackets, bucketed by age group) and build one installable PWA per age group (U8…U18 except U15) plus a hub page — all from the `data.json`/`standings.json` the data layer produces.

**Architecture:** Extends the `ahk-beach` repo from Plan 1. Standings network wiring is added to `fetch_standings.py` (reusing the Plan 1 pure transforms). A new `build_apps.py` renders each age group into `/uXX/` using a `template.py` copied verbatim from the proven live app, parameterized for one group and format-aware (Mini = schedule only). `build_ics.py` writes per-team calendars; `build_hub.py` writes the root directory page (U15 links to the live repo's URL). Each app gets a unique PWA identity and a unique service-worker cache name.

**Tech Stack:** Python 3 stdlib + pytest. Same patterns as Plan 1 and the live `alingsas-ahus-beach-2026` repo.

**Prerequisite:** Plan 1 complete (`config.py`, `derive.py`, `rules.py`, `api.py`, `fetch_data.py`, `fetch_standings.py` with pure transforms, committed; `data.json` present).

**Reference (read, do NOT import — these live in `/home/martin/dev/ahusbeach`):**
- `build_site.py` — the page TEMPLATE, MANIFEST, SERVICE_WORKER, and render approach to copy.
- `build_ics.py` — the iCal generation to port.
- `fetch_standings.py` — the standings network wiring (`discover_divisions`, `category_playoffs`, `bracket_match`, `group_rounds`, `build`) to generalize.
- Plan 1 final-review notes (in `docs/superpowers/plans/2026-06-26-ahk-beach-data-layer.md`): honor `profile.has_results` (hide Mini results); `data.json` is committed; intra-club matches attribute to home team.

**Key data shapes (from Plan 1):**
- `data.json`: `{meta, groups: {age_slug: {age, label, rule, profile, teams:[...], matches:[...]}}}`. Each team: `{id, gender, age, rule, suffix, team_name, age_slug, slug, color}`. Each match: `{age_slug, slug, gender, rule, color, datum, dag, tid, bana, grupp, hemma, borta, mots, hb, result, start_ms, start_iso, day_label}`.
- `profile`: `{duration_min, has_results, has_tables, has_playoffs}`.

---

## File Structure

In `~/dev/ahk-beach/`:
- Modify: `fetch_standings.py` — add network wiring + `main()` → `standings.json` bucketed by `age_slug`.
- Create: `template.py` — TEMPLATE / MANIFEST_BASE / SERVICE_WORKER copied from live `build_site.py`, parameterized.
- Create: `build_apps.py` — per-age-group app builder (`app_manifest`, `service_worker_js`, `render_app`, `main`).
- Create: `build_ics.py` — per-team `.ics` (ported from live).
- Create: `build_hub.py` — root hub page listing all age-group apps.
- Create: `build_all.py` — orchestration (fetch + all builds), for local/CI use.
- Tests: `tests/test_standings.py` (extend), `tests/test_build_apps.py`, `tests/test_hub.py`, `tests/test_ics.py`.
- Output dirs (gitignored build artifacts decision deferred to Plan 3; for now committed like `data.json`): `u8/ u10/ … u18/` each with `index.html, manifest.json, sw.js, ics/*.ics`; root `index.html` (hub); `standings.json`.

---

## PHASE A — standings.json (bucketed by age group)

### Task A1: `bracket_match` + `group_rounds` (pure)

**Files:** Modify `fetch_standings.py`; Test `tests/test_standings.py`.

- [ ] **Step 1: Append tests to `tests/test_standings.py`:**
```python
def _bm_store(mid, home_name, away_name, hid, aid, rnd, bana, result):
    return {
        f"M({mid})": {"__typename": "Match", "id": mid, "start": 1000 + mid,
                      "home": {"href": f"HO({mid})"}, "away": {"href": f"AW({mid})"},
                      "arena": {"href": f"AR({mid})"}, "round": {"href": f"RN({mid})"},
                      "result": {"href": f"RE({mid})"}},
        f"HO({mid})": {"name": {"sv": home_name}, "team": {"href": f"Team({{id:{hid}}})"}},
        f"AW({mid})": {"name": {"sv": away_name}, "team": {"href": f"Team({{id:{aid}}})"}},
        f"AR({mid})": {"fieldName": f"Bana {bana}"},
        f"RN({mid})": {"name": {"sv": rnd}},
        f"RE({mid})": result,
    }


def test_bracket_match_normalizes_and_flags_winner():
    st = _bm_store(1, "Alingsås HK Blå", "Lugi HF", 10, 20, "Semifinal", 7,
                   {"finished": True, "homeGoals": 12, "awayGoals": 9})
    m = fs.bracket_match(st["M(1)"], st, club_ids={10})
    assert m["round"] == "Semifinal" and m["bana"] == 7
    assert m["home"]["label"] == "Alingsås HK Blå" and m["home"]["is_alingsas"] is True
    assert m["home"]["goals"] == 12 and m["away"]["goals"] == 9
    assert m["winner"] == "home"


def test_group_rounds_orders_by_first_start():
    ms = [{"round": "Final", "start": 200, "id": 2},
          {"round": "Semifinal", "start": 100, "id": 1}]
    rounds = fs.group_rounds(ms)
    assert [r["name"] for r in rounds] == ["Semifinal", "Final"]
    assert "_first" not in rounds[0]
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: ... 'bracket_match'`)
Run: `cd /home/martin/dev/ahk-beach && python3 -m pytest tests/test_standings.py -k "bracket or group_rounds" -q`

- [ ] **Step 3: Append to `fetch_standings.py`** (uses existing `api`, `winner_side`):
```python

def bracket_match(m, store, club_ids):
    """Slutspelsmatch (Match-entitet + store) → vår bracket-modell."""
    home = api.store_get(store, m.get("home")) or {}
    away = api.store_get(store, m.get("away")) or {}
    arena = api.store_get(store, m.get("arena")) or {}
    rnd = api.store_get(store, m.get("round")) or {}
    result = api.store_get(store, m.get("result")) or {}
    side = winner_side(result)

    def actor(a):
        tid = api.ref_id(a.get("team")) if isinstance(a.get("team"), dict) else None
        goals = None
        if result.get("finished"):
            goals = result.get("homeGoals") if a is home else result.get("awayGoals")
        return {"label": api.name_of(a), "team_id": tid,
                "is_alingsas": tid in club_ids if tid else False, "goals": goals}

    return {"id": m.get("id"), "start": m.get("start"),
            "bana": _bana_num(arena.get("fieldName", "")),
            "round": api.name_of(rnd), "home": actor(home), "away": actor(away),
            "winner": side}


def group_rounds(matches):
    """Normaliserade matcher → ronder, ordnade efter rondens första start."""
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
Also add a `_bana_num` helper near the top of `fetch_standings.py` (mirrors `fetch_data._bana_num`), since standings needs it too:
```python
def _bana_num(field):
    import re as _re
    m = _re.search(r"(\d+)", field or "")
    return int(m.group(1)) if m else (field or "")
```

- [ ] **Step 4: Run — expect PASS**
Run: `cd /home/martin/dev/ahk-beach && python3 -m pytest tests/test_standings.py -q`

- [ ] **Step 5: Commit**
```bash
cd /home/martin/dev/ahk-beach
git add fetch_standings.py tests/test_standings.py
git commit -q -m "feat: standings bracket_match + group_rounds (pure)"
```

### Task A2: `discover_divisions` (age-group aware)

**Files:** Modify `fetch_standings.py`; Test `tests/test_standings.py`.

- [ ] **Step 1: Append test:**
```python
def test_discover_divisions_tags_age_slug():
    store = {
        "Match({id:1})": {"__typename": "Match",
                          "home": {"href": "HO1"}, "away": {"href": "AW1"},
                          "division": {"href": "Div({id:500})"}},
        "HO1": {"team": {"href": "Team({id:10})"}},
        "AW1": {"team": {"href": "Team({id:99})"}},
        "Div({id:500})": {"name": {"sv": "Grupp 2"},
                          "category": {"href": "Category({categoryId:70,tournamentId:2})"}},
    }
    reg_by_id = {10: {"age_slug": "u15", "rule": "Classic"}}
    out = fs.discover_divisions(store, reg_by_id)
    assert out[500] == {"age_slug": "u15", "rule": "Classic",
                        "name": "Grupp 2", "category": "70"}
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Append to `fetch_standings.py`:**
```python
def _category_id(division_entity):
    import re as _re
    cat = division_entity.get("category") if isinstance(division_entity, dict) else None
    href = cat.get("href", "") if isinstance(cat, dict) else ""
    m = _re.search(r"categoryId:(\d+)", href)
    return m.group(1) if m else None


def discover_divisions(store, reg_by_id):
    """{division_id: {age_slug, rule, name, category}} för klubbens grupper."""
    out = {}
    for e in store.values():
        if e.get("__typename") != "Match":
            continue
        home = api.store_get(store, e.get("home", {}))
        away = api.store_get(store, e.get("away", {}))
        hid, aid = api.ref_id(home.get("team")), api.ref_id(away.get("team"))
        team = reg_by_id.get(hid) or reg_by_id.get(aid)
        if not team:
            continue
        did = api.ref_id(e.get("division"))
        if did is None:
            continue
        dent = api.store_get(store, e.get("division", {}))
        out[did] = {"age_slug": team["age_slug"], "rule": team["rule"],
                    "name": api.name_of(dent), "category": _category_id(dent)}
    return out
```

- [ ] **Step 4: Run — expect PASS**
- [ ] **Step 5: Commit** (`feat: standings discover_divisions (age-group tagged)`)

### Task A3: standings network wiring + `main` → `standings.json`

**Files:** Modify `fetch_standings.py`; Test: live smoke check.

This ports the live `category_playoffs` + `build` + `main`, generalized: bucket by `age_slug`, skip Mini via `rule_profile(...).has_tables`. Reuses `fetch_data.build_team_registry` for the registry.

- [ ] **Step 1: Append network section to `fetch_standings.py`** (full code):
```python

import os
import sys
import json
import hashlib
from datetime import datetime, timezone

import fetch_data

ROOT = os.path.dirname(os.path.abspath(__file__))
STANDINGS_JSON = os.path.join(ROOT, "standings.json")
_TID = config.TOURNAMENT_ID  # config imported at top via `import config`? ensure it is.


def _resolve(query):
    resp = api.call(query).get("responses", {})
    if query in resp and isinstance(resp[query], dict):
        return resp[query].get("entity")
    for v in resp.values():
        if isinstance(v, dict) and "entity" in v:
            return v["entity"]
    return None


def _store(query):
    resp = api.call(query).get("responses", {})
    return {k: v["entity"] for k, v in resp.items()
            if isinstance(v, dict) and isinstance(v.get("entity"), dict)}


def category_playoffs(cat_id, sample_division_id):
    """[(stage_id, playoff_division_id, tier_namn)] för en kategori."""
    table = _resolve(f"Division({{id:{sample_division_id}}})$table") or {}
    stage_ids = []
    for r in table.get("rows", []):
        sid = _stage_id((r.get("targetStage") or {}).get("href", ""))
        if sid and sid not in stage_ids:
            stage_ids.append(sid)
    out = []
    for sid in stage_ids:
        ent = _resolve(f"Stage({{categoryId:{cat_id},stageId:{sid},"
                       f"tournamentId:{config.TOURNAMENT_ID}}})$divisions")
        if isinstance(ent, list):
            for dref in ent:
                pid = api.ref_id(dref)
                pe = _resolve(f"Division({{id:{pid}}})")
                out.append((sid, pid, api.name_of(pe)))
    return out


def build():
    store = api.fetch_store()
    registry = fetch_data.build_team_registry(store)
    reg_by_id = {t["id"]: t for t in registry}
    club_ids = set(reg_by_id)
    divisions = discover_divisions(store, reg_by_id)

    cat_play, cat_age = {}, {}
    for did, info in divisions.items():
        if not rules.rule_profile(info["rule"])["has_tables"]:
            continue                       # Mini → inga tabeller/slutspel
        cat = info["category"]
        cat_age.setdefault(cat, info["age_slug"])
        if cat not in cat_play:
            cat_play[cat] = category_playoffs(cat, did)

    by_age = {}                            # age_slug → {"groups": [...], "playoffs": [...]}
    for did, info in divisions.items():
        if not rules.rule_profile(info["rule"])["has_tables"]:
            continue
        tier_by_stage = {sid: name for (sid, _p, name) in cat_play.get(info["category"], [])}
        table = _resolve(f"Division({{id:{did}}})$table") or {}
        rows = [table_row(r, club_ids, tier_by_stage) for r in table.get("rows", [])]
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        bucket = by_age.setdefault(info["age_slug"], {"groups": [], "playoffs": []})
        bucket["groups"].append({"name": info["name"], "division_id": did, "rows": rows})

    for cat, plist in cat_play.items():
        age = cat_age.get(cat)
        tiers = []
        for (_sid, pid, name) in plist:
            q = (f"Division({{id:{pid}}}){{matches:[{{... on Match:"
                 f"{{start:{{}},home:{{}},away:{{}},arena:{{}},round:{{}},result:{{}}}}}}]}}")
            st = _store(q)
            ms = [bracket_match(e, st, club_ids)
                  for e in st.values() if e.get("__typename") == "Match"]
            tiers.append({"tier": name, "division_id": pid, "rounds": group_rounds(ms)})
        if age:
            by_age.setdefault(age, {"groups": [], "playoffs": []})["playoffs"].extend(tiers)

    for b in by_age.values():
        b["groups"].sort(key=lambda g: g["name"])
    return by_age


def _hash(by_age):
    return hashlib.sha256(json.dumps(by_age, ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def main():
    try:
        by_age = build()
    except Exception as e:
        print("FEL vid hämtning:", e, "- lämnar standings.json orörd")
        return 0
    if not by_age:
        print("0 grupper - lämnar standings.json orörd")
        return 0
    h = _hash(by_age)
    if os.path.exists(STANDINGS_JSON):
        try:
            with open(STANDINGS_JSON, encoding="utf-8") as f:
                if json.load(f).get("meta", {}).get("data_hash") == h:
                    print(f"Ingen ändring ({len(by_age)} åldersgrupper). Skriver inte om.")
                    return 0
        except Exception:
            pass
    now = datetime.now(timezone.utc)
    doc = {"meta": {"source": "cupmanager API (Division$table + Playoff)",
                    "generated": now.isoformat(timespec="seconds"),
                    "seq": int(now.timestamp()), "data_hash": h},
           "by_age": by_age}
    with open(STANDINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"Skrev standings.json för {len(by_age)} åldersgrupper")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
Ensure the top of `fetch_standings.py` imports `config` and `rules` (it already imports `api`, `rules`; add `import config` if missing).

- [ ] **Step 2: Run unit tests — expect PASS**
Run: `cd /home/martin/dev/ahk-beach && python3 -m pytest -q`

- [ ] **Step 3: LIVE smoke check**
```bash
cd /home/martin/dev/ahk-beach
python3 fetch_standings.py
python3 -c "import json;d=json.load(open('standings.json'));print('åldersgrupper:', sorted(d['by_age']));import sys;[print(a, 'grupper', len(b['groups']), 'slutspel', len(b['playoffs'])) for a,b in sorted(d['by_age'].items())]"
```
Expected: age groups u12–u18 present (NOT u8/u10/u11 — Mini excluded), each with ≥1 group. Report actual output. If empty or Mini appears, report DONE_WITH_CONCERNS.

- [ ] **Step 4: Commit** (`feat: standings network wiring → standings.json bucketed by age`)

---

## PHASE B — Per-age-group apps + hub

### Task B1: `template.py` (copy from live build_site.py, parameterized)

**Files:** Create `template.py`.

This is a COPY task, not original code. Open `/home/martin/dev/ahusbeach/build_site.py` and copy three top-level objects into a new `~/dev/ahk-beach/template.py`:
1. The `TEMPLATE` triple-quoted string (the whole HTML document, from `TEMPLATE = """` to its closing `"""`).
2. `MANIFEST` → rename to `MANIFEST_BASE`.
3. `SERVICE_WORKER` → rename to `SERVICE_WORKER_TPL`.

Apply exactly these parameterization edits:
- [ ] **Step 1:** Copy `TEMPLATE` verbatim. It already uses placeholders `__DATA__`, `__TEAMS__`, `__DUR_MIN__`, `__STANDINGS__`, `__ROSTERS__`, `__CAL_ITEMS__`, `__BASE__`, `__UPDATED__`. Add one more placeholder: in the `<title>` and header, the app must show its age label — find the header `<h1>` block and the `<title>` and insert a `__APPLABEL__` placeholder (e.g. title `AHK __APPLABEL__ · Åhus Beach`). Leave all other placeholders intact. (Rosters: there are no rosters in this repo, so `__ROSTERS__` will be filled with `{}`.)
- [ ] **Step 2:** Copy `MANIFEST` as `MANIFEST_BASE`. Change nothing yet (parameterized in B2).
- [ ] **Step 3:** Copy `SERVICE_WORKER` as `SERVICE_WORKER_TPL`, and change the first line from `const C = "ahus-schema-v1";` to `const C = "__CACHE__";` (placeholder for a per-app cache name).
- [ ] **Step 4:** Add at the bottom of `template.py`:
```python
# template.py innehåller TEMPLATE (HTML), MANIFEST_BASE (dict), SERVICE_WORKER_TPL (str)
# kopierade från alingsas-ahus-beach-2026/build_site.py och parametriserade med
# __APPLABEL__ (rubrik) och __CACHE__ (per-app service-worker-cache).
```
- [ ] **Step 5:** Sanity check it imports:
Run: `cd /home/martin/dev/ahk-beach && python3 -c "import template; assert '__APPLABEL__' in template.TEMPLATE; assert '__CACHE__' in template.SERVICE_WORKER_TPL; print('ok')"`
Expected: `ok`
- [ ] **Step 6: Commit** (`chore: template.py (copied + parameterized from live build_site.py)`)

### Task B2: `build_apps.app_manifest` + `service_worker_js`

**Files:** Create `build_apps.py`; Test `tests/test_build_apps.py`.

- [ ] **Step 1: Create `tests/test_build_apps.py`:**
```python
# -*- coding: utf-8 -*-
import build_apps


def _group(age_slug="u14", label="U14"):
    return {"age": 14, "label": label, "rule": "Classic",
            "profile": {"duration_min": 11, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": [{"slug": f"{age_slug}-p-bla", "team_name": "Alingsås HK Blå",
                       "color": "#1f5fbf", "gender": "P"}],
            "matches": []}


def test_app_manifest_has_unique_identity():
    m = build_apps.app_manifest(_group())
    assert m["name"] == "AHK U14"
    assert m["short_name"] == "AHK U14"
    assert m["start_url"] == "." and m["scope"] == "./"
    assert any(i["src"] == "icon-192.png" for i in m["icons"])


def test_service_worker_has_unique_cache_name():
    sw = build_apps.service_worker_js("u14")
    assert 'const C = "ahk-u14-v1";' in sw
    assert "__CACHE__" not in sw
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError: build_apps`)

- [ ] **Step 3: Create `build_apps.py` (start):**
```python
# build_apps.py
# -*- coding: utf-8 -*-
"""Bygger en installerbar PWA per åldersgrupp ur data.json/standings.json."""

import os
import json

import config
import template

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
STANDINGS_JSON = os.path.join(ROOT, "standings.json")
SKIP_AGE_SLUGS = {"u15"}                  # U15 bor kvar i alingsas-ahus-beach-2026


def app_manifest(group):
    m = dict(template.MANIFEST_BASE)
    m["name"] = f"AHK {group['label']}"
    m["short_name"] = f"AHK {group['label']}"
    m["description"] = f"Matchschema för Alingsås HK {group['label']} på Åhus Beach Handboll"
    m["start_url"] = "."
    m["scope"] = "./"
    return m


def service_worker_js(age_slug):
    return template.SERVICE_WORKER_TPL.replace("__CACHE__", f"ahk-{age_slug}-v1")
```

- [ ] **Step 4: Run — expect PASS**
- [ ] **Step 5: Commit** (`feat: build_apps.app_manifest + service_worker_js`)

### Task B3: `build_apps.render_app` (format-aware page)

**Files:** Modify `build_apps.py`; Test `tests/test_build_apps.py`.

- [ ] **Step 1: Append tests:**
```python
def test_render_app_replaces_placeholders_and_labels():
    html = build_apps.render_app(_group(), standings=None, base="https://x/ahk-beach/u14",
                                 updated="nyss")
    assert "__DATA__" not in html and "__STANDINGS__" not in html
    assert "__APPLABEL__" not in html and "U14" in html
    assert 'ahk-' not in html  # cache name lives in sw.js, not the page


def test_render_app_strips_results_when_has_results_false():
    g = _group()
    g["rule"] = "Mini"
    g["profile"]["has_results"] = False
    g["matches"] = [{"start_ms": 1, "tid": "10:00", "bana": 1, "slug": "u14-p-bla",
                     "grupp": "G1", "hemma": "A", "borta": "B", "hb": "Hemma",
                     "day_label": "x", "color": "#1f5fbf", "gender": "P",
                     "result": {"hg": 5, "ag": 3}}]
    html = build_apps.render_app(g, standings=None, base="b", updated="u")
    data = html.split('const MATCHES = ', 1)[1].split(';\n', 1)[0]
    assert '"res": null' in data or '"res":null' in data
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Append to `build_apps.py`:**
```python
def _js_matches(group):
    """Matcher → den form sidans JS väntar (samma nycklar som live-appen)."""
    has_res = group["profile"]["has_results"]
    out = []
    for m in group["matches"]:
        out.append({
            "ms": m["start_ms"], "t": m["tid"], "bana": m["bana"],
            "lag": m["slug"], "slug": m["slug"], "klass": group["label"],
            "grp": m["grupp"], "home": m["hemma"], "away": m["borta"],
            "hb": m["hb"], "day": m["day_label"], "color": m["color"],
            "res": m.get("result") if has_res else None,
        })
    out.sort(key=lambda x: x["ms"])
    return out


def _teams_js(group):
    return [{"lag": t["team_name"], "slug": t["slug"], "klass": group["label"],
             "id": t["slug"], "color": t["color"].lstrip("#")} for t in group["teams"]]


def render_app(group, standings, base, updated):
    """Renderar en åldersgrupps index.html. `standings` = by_age[age_slug] eller None."""
    st = standings if (standings and group["profile"]["has_tables"]) else None
    html = (template.TEMPLATE
            .replace("__DATA__", json.dumps(_js_matches(group), ensure_ascii=False))
            .replace("__TEAMS__", json.dumps(_teams_js(group), ensure_ascii=False))
            .replace("__DUR_MIN__", str(group["profile"]["duration_min"]))
            .replace("__STANDINGS__", json.dumps(st, ensure_ascii=False))
            .replace("__ROSTERS__", "{}")
            .replace("__CAL_ITEMS__", "")
            .replace("__APPLABEL__", group["label"])
            .replace("__BASE__", base)
            .replace("__UPDATED__", updated))
    return html
```
> NOTE on the `__STANDINGS__` shape: the live template expects `STANDINGS = {groups:[...], playoffs:[...]}`. Our `by_age[age_slug]` is exactly `{groups:[...], playoffs:[...]}`, so it drops in directly. Confirm the template's `renderTables`/`renderBracket` read `STANDINGS.groups`/`STANDINGS.playoffs` (they do in the live app).
> NOTE on `_teams_js`: the live filter pills key on team slug; here team `id` is set to the slug (apps don't use cupmanager numeric ids client-side).

- [ ] **Step 4: Run — expect PASS**
- [ ] **Step 5: Commit** (`feat: build_apps.render_app (format-aware, Mini hides results)`)

### Task B4: `build_apps.main` (write all apps)

**Files:** Modify `build_apps.py`; Test `tests/test_build_apps.py`.

- [ ] **Step 1: Append test (uses a temp tree via monkeypatch of ROOT/paths):**
```python
def test_build_apps_writes_each_group_dir(tmp_path, monkeypatch):
    data = {"meta": {"generated": "2026-06-26T00:00:00Z"},
            "groups": {"u14": _group("u14", "U14"), "u15": _group("u15", "U15")}}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(build_apps, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_apps, "DATA_JSON", str(tmp_path / "data.json"))
    monkeypatch.setattr(build_apps, "STANDINGS_JSON", str(tmp_path / "nope.json"))
    n = build_apps.main()
    assert (tmp_path / "u14" / "index.html").exists()
    assert (tmp_path / "u14" / "manifest.json").exists()
    assert (tmp_path / "u14" / "sw.js").exists()
    assert not (tmp_path / "u15").exists()       # U15 skippas
    assert n == 1
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Append to `build_apps.py`:**
```python
def _load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    data = _load(DATA_JSON, {"groups": {}, "meta": {}})
    standings = _load(STANDINGS_JSON, {"by_age": {}}).get("by_age", {})
    updated = data.get("meta", {}).get("generated", "")
    built = 0
    for age_slug, group in data.get("groups", {}).items():
        if age_slug in SKIP_AGE_SLUGS:
            continue
        out_dir = os.path.join(ROOT, age_slug)
        os.makedirs(out_dir, exist_ok=True)
        base = f"{config.PAGES_BASE}/{age_slug}"
        html = render_app(group, standings.get(age_slug), base, updated)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(app_manifest(group), f, ensure_ascii=False, indent=2)
        with open(os.path.join(out_dir, "sw.js"), "w", encoding="utf-8") as f:
            f.write(service_worker_js(age_slug))
        built += 1
    print(f"Byggde {built} appar")
    return built


if __name__ == "__main__":
    main()
```
> The icons referenced by each manifest (`icon-192.png` etc.) must exist inside each `/uXX/` dir for installability. Add to `main()` after writing sw.js: copy the icon set into `out_dir` (use `shutil.copy`). Add `import shutil` at top and:
> ```python
> for ic in ("icon-192.png", "icon-512.png", "icon-512-maskable.png", "icon-180.png", "favicon-32.png"):
>     shutil.copy(os.path.join(ROOT, ic), os.path.join(out_dir, ic))
> ```

- [ ] **Step 4: Run unit tests — expect PASS** (update the test to also assert an icon was copied if you added the copy step)
- [ ] **Step 5: LIVE build check**
```bash
cd /home/martin/dev/ahk-beach
python3 build_apps.py
ls u14 && python3 -c "import json;print(json.load(open('u14/manifest.json'))['name'])"
grep -o 'const C = \"[^\"]*\"' u14/sw.js
```
Expected: `Byggde 9 appar`; `u14/` has index.html/manifest.json/sw.js/icons; manifest name `AHK U14`; sw cache `ahk-u14-v1`.
- [ ] **Step 6: Commit** (`feat: build_apps.main writes one PWA per age group`)

### Task B5: `build_ics.py` (per-team calendars, ported)

**Files:** Create `build_ics.py`; Test `tests/test_ics.py`.

Port `/home/martin/dev/ahusbeach/build_ics.py` with these changes: source matches from `data.json` groups (not `schedule`/`matches_data`); write per-team `.ics` into each `/uXX/ics/`; `PRODID`/labels use the age label; duration from the group's `profile.duration_min`. The folding/escaping/UID/vevent logic is copied verbatim.

- [ ] **Step 1: Create `tests/test_ics.py`:**
```python
# -*- coding: utf-8 -*-
import build_ics


def test_vevent_has_stable_uid_and_times():
    m = {"slug": "u14-p-bla", "mots": "Lugi HF", "grupp": "Grupp 2",
         "start_ms": 1783585800000, "bana": 7, "hemma": "Alingsås HK Blå",
         "borta": "Lugi HF", "hb": "Hemma", "tid": "10:30"}
    lines = build_ics.vevent(m, label="U14", duration_min=11, seq=1, dtstamp="20260101T000000Z")
    text = "\n".join(lines)
    assert "BEGIN:VEVENT" in text and "END:VEVENT" in text
    assert "UID:u14-p-bla-vs-lugi-hf-grupp-2@" in text
    assert "DTSTART:20260709T083000Z" in text     # 10:30 CEST = 08:30 UTC
    assert "DTEND:20260709T084100Z" in text        # +11 min


def test_fold_wraps_long_lines():
    long = "X" * 200
    out = build_ics.fold(long)
    assert all(len(l.encode("utf-8")) <= 75 for l in out.split("\r\n "))
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Create `build_ics.py`** by porting the live file. Copy `ms_to_utc`, `iso_to_utc_compact`, `slug_ascii`, `uid_for`, `esc`, `fold` verbatim. Adapt `vevent`, `build_calendar`, `main`:
```python
# build_ics.py
# -*- coding: utf-8 -*-
"""iCalendar (.ics) per lag, per åldersgrupp, ur data.json. Ported från
alingsas-ahus-beach-2026/build_ics.py."""

import os
import json
from datetime import datetime, timezone

import config

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
SKIP = {"u15"}
PRODID = "-//Alingsas HK//Ahus Beach Handboll//SV"
SOURCE_NOTE = "Källa: ahusbeachhandboll.cupmanager.net"

# --- copied verbatim from live build_ics.py ---
def ms_to_utc(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def slug_ascii(s):
    import unicodedata, re
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()

def uid_for(m):
    base = f"{m['slug']}-vs-{slug_ascii(m['mots'])}-{slug_ascii(str(m['grupp']))}"
    return f"{base}@ahusbeach.cupmanager.net"

def esc(t):
    return (t.replace("\\\\", "\\\\\\\\").replace(";", "\\\\;")
             .replace(",", "\\\\,").replace("\n", "\\\\n"))

def fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, start, limit = [], 0, 75
    while start < len(raw):
        end = min(start + limit, len(raw))
        while end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        parts.append(raw[start:end]); start = end; limit = 74
    return parts[0].decode("utf-8") + "".join("\r\n " + p.decode("utf-8") for p in parts[1:])
# --- end verbatim ---


def vevent(m, label, duration_min, seq, dtstamp):
    dur_ms = duration_min * 60 * 1000
    dtstart = ms_to_utc(m["start_ms"])
    dtend = ms_to_utc(m["start_ms"] + dur_ms)
    summary = f"{label}: {m['hemma']} – {m['borta']}"
    location = f"Bana {m['bana']}, Åhus Beach Handboll, Åhus"
    desc = (f"{m['grupp']}\\nAlingsås spelar {m['hb'].lower()}lag mot {m['mots']}.\\n"
            f"Avspark {m['tid']} (lokal tid).\\n{SOURCE_NOTE}")
    return ["BEGIN:VEVENT", f"UID:{uid_for(m)}", f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}", f"DTEND:{dtend}", f"SUMMARY:{esc(summary)}",
            f"LOCATION:{esc(location)}", f"DESCRIPTION:{desc}", f"SEQUENCE:{seq}",
            f"LAST-MODIFIED:{dtstamp}", "STATUS:CONFIRMED", "TRANSP:OPAQUE", "END:VEVENT"]


def build_calendar(rows, cal_name, cal_desc, label, duration_min, seq, dtstamp):
    rows = sorted(rows, key=lambda m: (m["start_ms"], str(m["bana"])))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{esc(cal_name)}",
             "X-WR-TIMEZONE:Europe/Stockholm", f"X-WR-CALDESC:{esc(cal_desc)}",
             "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
    for m in rows:
        lines += vevent(m, label, duration_min, seq, dtstamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("meta", {})
    seq = int(meta.get("seq", 1))
    dtstamp = ms_to_utc(int(__import__("time").time() * 1000)) if False else \
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for age_slug, g in data.get("groups", {}).items():
        if age_slug in SKIP:
            continue
        out_dir = os.path.join(ROOT, age_slug, "ics")
        os.makedirs(out_dir, exist_ok=True)
        dur = g["profile"]["duration_min"]
        by_team = {}
        for m in g["matches"]:
            by_team.setdefault(m["slug"], []).append(m)
        # samlad
        with open(os.path.join(out_dir, "alla.ics"), "w", encoding="utf-8", newline="") as f:
            f.write(build_calendar(g["matches"], f"Alingsås HK {g['label']} (alla) – Åhus Beach",
                                   f"Alla lag i {g['label']}. {SOURCE_NOTE}",
                                   g["label"], dur, seq, dtstamp))
        for t in g["teams"]:
            rows = by_team.get(t["slug"], [])
            with open(os.path.join(out_dir, f"{t['slug']}.ics"), "w",
                      encoding="utf-8", newline="") as f:
                f.write(build_calendar(rows, f"{t['team_name']} – Åhus Beach",
                                       f"{g['label']}. {SOURCE_NOTE}",
                                       g["label"], dur, seq, dtstamp))
    print("iCal genererad per åldersgrupp")


if __name__ == "__main__":
    main()
```
> Replace the convoluted `dtstamp` line with a clean `dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")` when implementing (the `if False` is illustrative of intent — just use the clean form).

- [ ] **Step 4: Run — expect PASS**
- [ ] **Step 5: Commit** (`feat: build_ics per-team calendars per age group`)

### Task B6: `build_hub.py` (root directory page)

**Files:** Create `build_hub.py`; Test `tests/test_hub.py`.

- [ ] **Step 1: Create `tests/test_hub.py`:**
```python
# -*- coding: utf-8 -*-
import build_hub


def test_hub_lists_groups_and_links_u15_to_live_repo():
    data = {"groups": {
        "u14": {"label": "U14", "teams": [1, 2], "matches": [1],
                "rule": "Classic", "profile": {}},
        "u15": {"label": "U15", "teams": [1], "matches": [1],
                "rule": "Classic", "profile": {}},
    }}
    html = build_hub.render_hub(data)
    assert "U14" in html and 'href="u14/"' in html
    assert build_hub.U15_LIVE_URL in html        # U15 → live-repots URL
    assert "u15/" not in html                     # ingen lokal u15-länk
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Create `build_hub.py`:**
```python
# build_hub.py
# -*- coding: utf-8 -*-
"""Hubbsida på roten: listar alla åldersgrupps-appar. U15 länkar till live-repot."""

import os
import json

import config

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
U15_LIVE_URL = "https://martinwelen.github.io/alingsas-ahus-beach-2026/"

_PAGE = """<!doctype html><html lang="sv"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AHK Åhus Beach – välj lag</title>
<style>body{{font-family:system-ui,sans-serif;background:#f4ecdb;color:#13293d;margin:0;padding:24px}}
h1{{font-size:1.4rem}} ul{{list-style:none;padding:0;display:grid;gap:10px;max-width:480px}}
a.card{{display:block;padding:14px 16px;background:#fff;border-radius:12px;text-decoration:none;
color:inherit;border:1px solid #0001;font-weight:700}} small{{color:#5a6b75;font-weight:500}}</style>
</head><body><h1>Alingsås HK · Åhus Beach Handboll</h1>
<p>Välj din åldersgrupp och lägg till på hemskärmen.</p><ul>{items}</ul></body></html>"""


def render_hub(data):
    groups = data.get("groups", {})
    items = []
    for age_slug in sorted(groups, key=lambda s: int(s[1:])):
        g = groups[age_slug]
        n_teams, n_matches = len(g.get("teams", [])), len(g.get("matches", []))
        meta = f"<small>{n_teams} lag · {n_matches} matcher</small>"
        if age_slug == "u15":
            items.append(f'<li><a class="card" href="{U15_LIVE_URL}">{g["label"]} '
                         f'(P15+F15) {meta}</a></li>')
        else:
            items.append(f'<li><a class="card" href="{age_slug}/">{g["label"]} {meta}</a></li>')
    return _PAGE.format(items="\n".join(items))


def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_hub(data))
    print("Hubb (index.html) genererad")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — expect PASS**
- [ ] **Step 5: Commit** (`feat: build_hub root directory page (U15 → live repo)`)

### Task B7: `build_all.py` orchestration + full live verification

**Files:** Create `build_all.py`.

- [ ] **Step 1: Create `build_all.py`:**
```python
# build_all.py
# -*- coding: utf-8 -*-
"""Kör hela kedjan lokalt/i CI: data → standings → appar → ics → hubb."""

import sys
import fetch_data
import fetch_standings
import build_apps
import build_ics
import build_hub


def main():
    fetch_data.main()
    fetch_standings.main()
    build_apps.main()
    build_ics.main()
    build_hub.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Full live run + verification:**
```bash
cd /home/martin/dev/ahk-beach
python3 build_all.py
echo "--- apps ---"; ls -d u*/ | sort
echo "--- u14 files ---"; ls u14 u14/ics
echo "--- hub links ---"; grep -o 'href="[^"]*"' index.html | head
python3 -m pytest -q
```
Expected: 9 app dirs (u8,u10,u11,u12,u13,u14,u16,u17,u18 — NOT u15), each with index.html/manifest.json/sw.js/ics/; hub lists all + U15→live URL; all unit tests pass.

- [ ] **Step 3: Verify in a browser** (manual, optional): serve and open one app + the hub.
```bash
cd /home/martin/dev/ahk-beach && python3 -m http.server 8742 &
# open http://localhost:8742/ (hub) and http://localhost:8742/u14/ (an app); then: kill %1
```
Confirm: hub lists groups; U14 app shows schema + tabeller/slutspel (if standings present); a Mini app (u8) shows schema only, no results.

- [ ] **Step 4: Commit** (`feat: build_all orchestration; full multi-app build verified`)

---

## Self-Review

**Spec coverage:** standings.json bucketed by age (A1–A3); per-app PWA with unique manifest + cache name (B2); format-aware rendering, Mini hides results/tables (B3, honors `has_results`/`has_tables`); 9 apps built, U15 skipped (B4); per-team iCal (B5); hub linking U15→live (B6); orchestration + live verification (B7). All spec items mapped.

**Placeholder scan:** The two "copy verbatim" tasks (B1 template, the copied helpers in B5) are explicit, well-bounded copy operations from named source files — not vague placeholders. The `if False`/illustrative `dtstamp` line in B5 is flagged with the exact clean replacement. No TBD/TODO.

**Type consistency:** `by_age[age_slug] = {groups, playoffs}` produced in A3 and consumed in B3/B4. `render_app(group, standings, base, updated)` signature consistent across B3/B4. `app_manifest`/`service_worker_js` names consistent B2/B4. Match dict keys consumed in `_js_matches` (B3) and `vevent` (B5) match Plan 1's `normalize_match` output.

**Open risks flagged for execution:** (1) the live `template`'s `renderTables/renderBracket` must read `STANDINGS.groups/.playoffs` — verify when copying (B3 note). (2) Whether `/uXX/` build outputs are committed or gitignored is a Plan 3 decision; default here is committed (like `data.json`). (3) The hub is a plain page, not itself a PWA — intentional (YAGNI).
