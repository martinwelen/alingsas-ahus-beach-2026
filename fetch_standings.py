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


# ---- Nätverkslager + orchestrering ------------------------------------------

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
    """Returnerar entiteten för frågans egen nyckel (annars första entiteten)."""
    resp = fmx.call(query).get("responses", {})
    if query in resp and isinstance(resp[query], dict):
        return resp[query].get("entity")
    for v in resp.values():
        if isinstance(v, dict) and "entity" in v:
            return v["entity"]
    return None


def _store(query):
    """Returnerar {key: entity} för en fråga som drar in flera entiteter."""
    resp = fmx.call(query).get("responses", {})
    return {k: v["entity"] for k, v in resp.items()
            if isinstance(v, dict) and isinstance(v.get("entity"), dict)}


def _category_id(division_entity):
    cat = division_entity.get("category") if isinstance(division_entity, dict) else None
    href = cat.get("href", "") if isinstance(cat, dict) else ""
    m = re.search(r"categoryId:(\d+)", href)
    return m.group(1) if m else None


def discover_divisions(store):
    """Hittar {division_id: {'klass','name','category'}} för Alingsås-grupperna."""
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
        out[did] = {"klass": md.short_klass(team["klass"]),
                    "name": fmx.name_of(dent),
                    "category": _category_id(dent)}
    return out


def category_playoffs(cat_id, sample_division_id):
    """[(stage_id, playoff_division_id, tier_namn)] för en kategori.

    Läser slutspels-stage-id ur en grupps targetStage-href:ar och resolvar varje
    stage → dess Playoff-division (A/B/C-Slutspel)."""
    table = _resolve(f"Division({{id:{sample_division_id}}})$table") or {}
    stage_ids = []
    for r in table.get("rows", []):
        sid = _stage_id((r.get("targetStage") or {}).get("href", ""))
        if sid and sid not in stage_ids:
            stage_ids.append(sid)
    out = []
    for sid in stage_ids:
        ent = _resolve(f"Stage({{categoryId:{cat_id},stageId:{sid},"
                       f"tournamentId:{md.TOURNAMENT_ID}}})$divisions")
        if isinstance(ent, list):
            for dref in ent:
                pid = fmx.ref_id(dref)
                pe = _resolve(f"Division({{id:{pid}}})")
                out.append((sid, pid, fmx.name_of(pe)))
    return out


def build():
    store = fmx.fetch_store()
    divisions = discover_divisions(store)

    # Slutspelsinfo per kategori (beräknas en gång, delas av grupper i samma klass).
    cat_play = {}
    cat_klass = {}
    for did, info in divisions.items():
        cat = info["category"]
        cat_klass.setdefault(cat, info["klass"])
        if cat not in cat_play:
            cat_play[cat] = category_playoffs(cat, did)

    # Grupptabeller.
    groups = []
    for did, info in divisions.items():
        tier_by_stage = {sid: name for (sid, _pid, name) in cat_play.get(info["category"], [])}
        table = _resolve(f"Division({{id:{did}}})$table") or {}
        rows = [table_row(r, ALINGSAS_IDS, tier_by_stage) for r in table.get("rows", [])]
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        if rows and not is_descending_points(rows):
            print(f"VARNING: grupp {info['name']} ({did}) är inte poäng-sorterad "
                  f"från API:t – kontrollera mot officiella tabellen.")
        groups.append({"klass": info["klass"], "division_id": did,
                       "name": info["name"], "tiers": tier_spans(rows), "rows": rows})
    groups.sort(key=lambda g: (g["klass"], g["name"]))

    # Slutspelsträd per åldersklass.
    playoffs = []
    for cat, plist in cat_play.items():
        tiers = []
        for (_sid, pid, name) in plist:
            q = (f"Division({{id:{pid}}}){{matches:[{{... on Match:"
                 f"{{home:{{}},away:{{}},arena:{{}},round:{{}},result:{{}}}}}}]}}")
            st = _store(q)
            ms = [bracket_match(e, st, ALINGSAS_IDS)
                  for e in st.values() if e.get("__typename") == "Match"]
            tiers.append({"tier": name, "division_id": pid, "rounds": group_rounds(ms)})
        playoffs.append({"klass": cat_klass.get(cat), "tiers": tiers})
    playoffs.sort(key=lambda p: p["klass"] or "")

    return groups, playoffs


def _hash(groups, playoffs):
    key = json.dumps({"g": groups, "p": playoffs}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()


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
