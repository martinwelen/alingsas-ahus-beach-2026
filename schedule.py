#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gemensam laddare av matchdata för alla generatorer (Excel, iCal, sida).

Föredrar matches.json (hämtad från cupmanager av fetch_matches.py).
Saknas den används den statiska seed-listan i matches_data.py.

Alla matcher normaliseras till EN form:
  datum 'YYYY-MM-DD', dag, tid 'HH:MM', bana, lag, slug, klass ('P15'/'F15'),
  grupp, hemma, borta, mots, hb ('Hemma'/'Borta'), color, start_ms, start_iso
"""

import os
import json
from datetime import datetime, timezone, timedelta

import matches_data as md

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "matches.json")

# Åhus i juli = CEST = UTC+2 (fast offset; turneringen är två dagar i juli).
CEST = timezone(timedelta(hours=md.UTC_OFFSET_HOURS))
SV_DAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
SV_MONTHS = ["", "januari", "februari", "mars", "april", "maj", "juni",
             "juli", "augusti", "september", "oktober", "november", "december"]

TEAM_BY_SLUG = {t["slug"]: t for t in md.teams}
TEAM_BY_ID = {t["id"]: t for t in md.teams}


def local_to_ms(datum, tid):
    y, mo, d = (int(x) for x in datum.split("-"))
    h, mi = (int(x) for x in tid.split(":"))
    return int(datetime(y, mo, d, h, mi, tzinfo=CEST).timestamp() * 1000)


def parts_from_ms(ms):
    dt = datetime.fromtimestamp(ms / 1000, CEST)
    return dt


def make_match(datum, tid, bana, lag, slug, klass, grupp, hemma, borta, hb):
    """Bygger en normaliserad matchdict (med härledda fält)."""
    start_ms = local_to_ms(datum, tid)
    dt = parts_from_ms(start_ms)
    mots = borta if hb == "Hemma" else hemma
    return {
        "datum": datum, "dag": SV_DAYS[dt.weekday()], "tid": tid, "bana": bana,
        "lag": lag, "slug": slug, "klass": klass, "grupp": grupp,
        "hemma": hemma, "borta": borta, "mots": mots, "hb": hb,
        "color": md.team_colors[lag],
        "start_ms": start_ms,
        "start_iso": dt.isoformat(timespec="minutes"),
        "day_label": f"{SV_DAYS[dt.weekday()]} {dt.day} {SV_MONTHS[dt.month]}",
    }


def _from_static():
    out = []
    for m in md.all_matches():
        out.append(make_match(m["datum"], m["tid"], m["bana"], m["lag"],
                              m["slug"], m["klass"], m["grupp"],
                              m["hemma"], m["borta"], m["hb"]))
    out.sort(key=lambda m: (m["start_ms"], str(m["bana"])))
    return out, {"source": "static (matches_data.py)",
                 "generated": md.LAST_UPDATED, "seq": md.REVISION}


def load_matches():
    """Returnerar (matcher, meta). meta: {source, generated(iso), seq(int)}."""
    if os.path.exists(DATA_JSON):
        try:
            with open(DATA_JSON, encoding="utf-8") as f:
                doc = json.load(f)
            ms = doc.get("matches") or []
            if ms:
                ms.sort(key=lambda m: (m["start_ms"], str(m["bana"])))
                return ms, doc.get("meta", {})
        except Exception as e:  # trasig json → fall tillbaka på statiskt
            print("VARNING: kunde inte läsa matches.json:", e)
    return _from_static()


def by_team(matches):
    """Grupperar matcher per lag-slug i lagordning, sorterade i tid."""
    groups = {t["slug"]: [] for t in md.teams}
    for m in matches:
        groups.setdefault(m["slug"], []).append(m)
    for s in groups:
        groups[s].sort(key=lambda m: m["start_ms"])
    return groups
