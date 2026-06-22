#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hämtar Alingsås HK:s matcher från cupmanagers publika API och skriver
matches.json. Körs av GitHub Action (cron) – ingen lokal dator behövs.

Filtrerar på de sex lagens cupmanager-id (robust även när klubben har lag i
andra åldersklasser, och plockar automatiskt upp slutspelsmatcher när
Alingsås lottats in i dem).

Skriver bara om matches.json när matchdatan FAKTISKT ändrats (jämför hash),
så cron-roboten inte committar i onödan. Vid hämtningsfel lämnas filen orörd.
"""

import os
import re
import sys
import json
import time
import hashlib
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import matches_data as md
import schedule as sch

API = ("https://ahusbeachhandboll.cupmanager.net/rest/results_api/call"
       "?call={call}&lang=sv&tournamentId=" + md.TOURNAMENT_ID)
QUERY = ("MatchWindow({{limit:{limit},offset:{offset},tournamentId:" + md.TOURNAMENT_ID + "}})"
         "{{matches:[{{... on Match:{{arena:{{}},away:{{team:{{}}}},"
         "division:{{category:{{}},name:{{}}}},home:{{team:{{}}}},result:{{}}}}}}]}}")
PAGE = 300


def call(query, retries=4):
    url = API.format(call=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={
        "accept": "application/json", "user-agent": "alingsas-ahus-bot/1.0"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(2 + 2 * i)
    raise last


def fetch_store():
    """Hämtar alla matchfönster och returnerar entitets-store {key: entity}."""
    store = {}
    offset = 0
    while True:
        resp = call(QUERY.format(limit=PAGE, offset=offset)).get("responses", {})
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


def name_of(entity):
    n = entity.get("name") if isinstance(entity, dict) else None
    if isinstance(n, dict):
        return n.get("sv") or n.get("en") or ""
    return n or ""


def ref_id(node):
    if isinstance(node, dict):
        m = re.search(r"id:(\d+)", node.get("href", ""))
        if m:
            return int(m.group(1))
    return None


def team_id(actor):
    return ref_id(actor.get("team")) if isinstance(actor, dict) else None


def bana_num(field):
    m = re.search(r"(\d+)", field or "")
    return int(m.group(1)) if m else (field or "")


def extract_result(res):
    """Returnerar {'hg','ag'} för en avgjord match, annars None."""
    if not res or not res.get("finished"):
        return None
    hg, ag = res.get("homeGoals"), res.get("awayGoals")
    if hg is None or ag is None:
        return None
    return {"hg": hg, "ag": ag}


def build_matches(store):
    def get(ref):
        return store.get(ref.get("href") if isinstance(ref, dict) else ref, {})

    rows = []
    for e in store.values():
        if e.get("__typename") != "Match":
            continue
        home_a, away_a = get(e.get("home", {})), get(e.get("away", {}))
        hid, aid = team_id(home_a), team_id(away_a)
        team = sch.TEAM_BY_ID.get(hid) or sch.TEAM_BY_ID.get(aid)
        if not team:
            continue
        div = get(e.get("division", {}))
        grupp = name_of(div) or team["grupp"]           # divisionens namn = gruppen
        klass = md.short_klass(team["klass"])
        bana = bana_num(get(e.get("arena", {})).get("fieldName", ""))
        hb = "Hemma" if hid in sch.TEAM_BY_ID else "Borta"
        dt = sch.parts_from_ms(e["start"])
        result = extract_result(get(e.get("result", {})))
        rows.append(sch.make_match(
            datum=f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}",
            tid=f"{dt.hour:02d}:{dt.minute:02d}",
            bana=bana, lag=team["lag"], slug=team["slug"], klass=klass,
            grupp=grupp, hemma=name_of(home_a), borta=name_of(away_a), hb=hb,
            result=result))
    rows.sort(key=lambda m: (m["start_ms"], str(m["bana"])))
    return rows


def data_hash(rows):
    key = [(m["slug"], m["start_ms"], m["bana"], m["hemma"], m["borta"], m["grupp"], m.get("result"))
           for m in rows]
    return hashlib.sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()


def main():
    try:
        store = fetch_store()
        rows = build_matches(store)
    except Exception as e:
        print("FEL vid hämtning:", e, "- lämnar matches.json orörd")
        return 0  # låt bygget köra på befintlig data; ingen commit görs

    if not rows:
        print("0 matcher hittades - lämnar matches.json orörd")
        return 0

    h = data_hash(rows)
    if os.path.exists(sch.DATA_JSON):
        try:
            with open(sch.DATA_JSON, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("meta", {}).get("data_hash") == h:
                print(f"Ingen förändring ({len(rows)} matcher). Skriver inte om.")
                return 0
        except Exception:
            pass

    now = datetime.now(timezone.utc)
    meta = {
        "source": "cupmanager API (MatchWindow, tournamentId %s)" % md.TOURNAMENT_ID,
        "generated": now.isoformat(timespec="seconds"),
        "seq": int(now.timestamp()),     # ständigt växande → driver iCal SEQUENCE
        "data_hash": h,
        "count": len(rows),
    }
    with open(sch.DATA_JSON, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "matches": rows}, f, ensure_ascii=False, indent=1)

    from collections import Counter
    print(f"Skrev {len(rows)} matcher till matches.json")
    print("  per lag:", dict(Counter(m["lag"] for m in rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
