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
