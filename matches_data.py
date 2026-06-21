#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gemensam källa för matchdata – Alingsås HK på Åhus Beach Handboll 2026.

ENDA sanningskällan. Både build_excel.py och build_ics.py importerar härifrån,
så Excel och iCal hålls i synk. Uppdatera matcherna här efter att du kört
kontroller mot cupmanager.net, och bumpa REVISION + LAST_UPDATED.

Varje match: (datum 'YYYY-MM-DD', dag, tid 'HH:MM', bana(int), hemma, borta)
"""

# Bumpa dessa vid varje uppdatering så prenumeranternas kalenderappar
# uppfattar att events ändrats (SEQUENCE) och när (DTSTAMP/LAST-MODIFIED).
REVISION = 1
LAST_UPDATED = "2026-06-21T12:00:00Z"   # UTC, ISO 8601

# Speltidens längd i kalendern. Matchtid = 2 × 5 min med 60 sek paus = 11 min
# (enligt arrangören). Starttiden är avspark.
MATCH_DURATION_MIN = 11

# Tidszon: alla matcher spelas i Åhus (Europe/Stockholm). I juli = CEST = UTC+2.
UTC_OFFSET_HOURS = 2

# GitHub Pages-bas där allt hostas (delas av iCal- och sidgenereringen).
PAGES_HOST = "martinwelen.github.io"
PAGES_PATH = "/alingsas-ahus-beach-2026"
PAGES_BASE = f"https://{PAGES_HOST}{PAGES_PATH}"

teams = [
    {
        "lag": "P15 Blå",
        "fullnamn": "Alingsås HK P15 Classic (f. 2011) Blå",
        "klass": "Pojkar 15 år Classic (födda 2011)",
        "grupp": "Grupp 2",
        "namn_i_schema": "Alingsås HK Blå",
        "slug": "p15-bla",
        "matcher": [
            ("2026-07-17", "Fredag", "13:45", 11, "Lugi HF 3", "Alingsås HK Blå"),
            ("2026-07-17", "Fredag", "15:30", 11, "Staffanstorps HK", "Alingsås HK Blå"),
            ("2026-07-17", "Fredag", "17:30", 8,  "Alingsås HK Blå", "IF Hallby HK Blå"),
            ("2026-07-17", "Fredag", "19:00", 17, "Alingsås HK Blå", "IFK Tumba HK 1"),
            ("2026-07-17", "Fredag", "21:00", 2,  "Alingsås HK Blå", "Ystads IF HF"),
            ("2026-07-18", "Lördag", "10:45", 7,  "Alingsås HK Blå", "H43 Lund HF 2"),
            ("2026-07-18", "Lördag", "11:45", 16, "Alingsås HK Blå", "Malmslätts HF"),
            ("2026-07-18", "Lördag", "13:00", 15, "HF Karlskrona Svart", "Alingsås HK Blå"),
            ("2026-07-18", "Lördag", "14:30", 1,  "IFK Kristianstad 2", "Alingsås HK Blå"),
        ],
    },
    {
        "lag": "P15 Orange",
        "fullnamn": "Alingsås HK P15 Classic (f. 2011) Orange",
        "klass": "Pojkar 15 år Classic (födda 2011)",
        "grupp": "Grupp 4",
        "namn_i_schema": "Alingsås HK Orange",
        "slug": "p15-orange",
        "matcher": [
            ("2026-07-17", "Fredag", "14:15", 8,  "IFK Kristianstad 1", "Alingsås HK Orange"),
            ("2026-07-17", "Fredag", "15:45", 12, "Alingsås HK Orange", "H43 Lund HF 3"),
            ("2026-07-17", "Fredag", "17:45", 9,  "Alingsås HK Orange", "Spånga HK Vit"),
            ("2026-07-17", "Fredag", "19:30", 9,  "Eslövs HK Svart", "Alingsås HK Orange"),
            ("2026-07-17", "Fredag", "21:00", 14, "Alingsås HK Orange", "Lugi HF 4"),
            ("2026-07-18", "Lördag", "10:45", 15, "Alingsås HK Orange", "Täby HBK"),
            ("2026-07-18", "Lördag", "12:00", 7,  "Dalby GIF 1", "Alingsås HK Orange"),
            ("2026-07-18", "Lördag", "13:15", 13, "IF Hallby HK Svart", "Alingsås HK Orange"),
            ("2026-07-18", "Lördag", "14:30", 12, "Lödde Vikings HK", "Alingsås HK Orange"),
        ],
    },
    {
        "lag": "P15 Vit",
        "fullnamn": "Alingsås HK P15 Classic (f. 2011) VIT",
        "klass": "Pojkar 15 år Classic (födda 2011)",
        "grupp": "Grupp 1",
        "namn_i_schema": "Alingsås HK VIT",
        "slug": "p15-vit",
        "matcher": [
            ("2026-07-17", "Fredag", "13:45", 7,  "Alingsås HK VIT", "IFK Malmö HF"),
            ("2026-07-17", "Fredag", "15:30", 4,  "IFK Tumba HK 2", "Alingsås HK VIT"),
            ("2026-07-17", "Fredag", "17:15", 12, "IF Hallby HK Vit", "Alingsås HK VIT"),
            ("2026-07-17", "Fredag", "19:00", 12, "Lugi HF 2", "Alingsås HK VIT"),
            ("2026-07-17", "Fredag", "20:45", 11, "Alingsås HK VIT", "HK Halmstad Röd"),
            ("2026-07-18", "Lördag", "10:45", 3,  "Höörs HK H 65 vit", "Alingsås HK VIT"),
            ("2026-07-18", "Lördag", "11:45", 8,  "Alingsås HK VIT", "IFK Kristianstad 3"),
            ("2026-07-18", "Lördag", "13:00", 8,  "H43 Lund HF 1", "Alingsås HK VIT"),
            ("2026-07-18", "Lördag", "14:15", 13, "Alingsås HK VIT", "HF Karlskrona Blå"),
        ],
    },
    {
        "lag": "F15 Blå",
        "fullnamn": "Alingsås HK F15 Classic (f. 2011) Blå",
        "klass": "Flickor 15 år Classic (födda 2011)",
        "grupp": "Grupp 1",
        "namn_i_schema": "Alingsås HK Blå",
        "slug": "f15-bla",
        "matcher": [
            ("2026-07-17", "Fredag", "12:45", 12, "Alingsås HK Blå", "H 78 Sölvesborg"),
            ("2026-07-17", "Fredag", "14:30", 12, "Alingsås HK Blå", "HK Björnen"),
            ("2026-07-17", "Fredag", "16:15", 17, "Eslövs HK 2", "Alingsås HK Blå"),
            ("2026-07-17", "Fredag", "18:00", 17, "IFK Bankeryd Blå", "Alingsås HK Blå"),
            ("2026-07-17", "Fredag", "20:00", 12, "Uppsala HK Svart", "Alingsås HK Blå"),
            ("2026-07-18", "Lördag", "10:15", 11, "Alingsås HK Blå", "IFK Kristianstad 2"),
            ("2026-07-18", "Lördag", "12:45", 2,  "Lödde Vikings HK Svart", "Alingsås HK Blå"),
            ("2026-07-18", "Lördag", "14:00", 3,  "Alingsås HK Blå", "Huddinge HK 1"),
        ],
    },
    {
        "lag": "F15 Gul",
        "fullnamn": "Alingsås HK F15 Classic (f. 2011) Gul",
        "klass": "Flickor 15 år Classic (födda 2011)",
        "grupp": "Grupp 3",
        "namn_i_schema": "Alingsås HK Gul",
        "slug": "f15-gul",
        "matcher": [
            ("2026-07-17", "Fredag", "14:45", 9,  "Höörs HK H 65 1", "Alingsås HK Gul"),
            ("2026-07-17", "Fredag", "16:45", 8,  "Alingsås HK Gul", "H43 Lund HF 2"),
            ("2026-07-17", "Fredag", "18:15", 17, "Alingsås HK Gul", "Lugi HF 3"),
            ("2026-07-17", "Fredag", "20:15", 8,  "Alingsås HK Gul", "IFK Bankeryd Vit"),
            ("2026-07-18", "Lördag", "10:30", 1,  "IFK Kristianstad 1", "Alingsås HK Gul"),
            ("2026-07-18", "Lördag", "11:30", 10, "IFK Malmö HF Vit", "Alingsås HK Gul"),
            ("2026-07-18", "Lördag", "12:45", 8,  "Önnereds HK 1", "Alingsås HK Gul"),
            ("2026-07-18", "Lördag", "14:00", 13, "IFK Tumba HK Vit", "Alingsås HK Gul"),
        ],
    },
    {
        "lag": "F15 Vit",
        "fullnamn": "Alingsås HK F15 Classic (f. 2011) Vit",
        "klass": "Flickor 15 år Classic (födda 2011)",
        "grupp": "Grupp 4",
        "namn_i_schema": "Alingsås HK Vit",
        "slug": "f15-vit",
        "matcher": [
            ("2026-07-17", "Fredag", "13:15", 4,  "Skara HF 2", "Alingsås HK Vit"),
            ("2026-07-17", "Fredag", "15:00", 7,  "Alingsås HK Vit", "Stavsten HK 2"),
            ("2026-07-17", "Fredag", "16:45", 11, "Gustavsbergs IF HK", "Alingsås HK Vit"),
            ("2026-07-17", "Fredag", "18:30", 14, "Alingsås HK Vit", "Åhus Handboll 1"),
            ("2026-07-18", "Lördag", "10:30", 3,  "IFK Malmö HF Gul", "Alingsås HK Vit"),
            ("2026-07-18", "Lördag", "11:30", 13, "Alingsås HK Vit", "Lödde Vikings HK Röd"),
            ("2026-07-18", "Lördag", "12:45", 13, "Alingsås HK Vit", "Ystads IF HF 1"),
            ("2026-07-18", "Lördag", "14:00", 17, "Alingsås HK Vit", "Huddinge HK 2"),
        ],
    },
]

# Turnerings-id på cupmanager (för API-hämtning).
TOURNAMENT_ID = "70944382"

# Lagens id på cupmanager – används för robust filtrering vid API-hämtning
# (klubben har lag i ~alla åldersklasser, så namn räcker inte).
team_ids = {
    "P15 Blå": 74904162, "P15 Orange": 76280580, "P15 Vit": 74904168,
    "F15 Blå": 74294026, "F15 Gul": 76514811, "F15 Vit": 74294028,
}
for _t in teams:
    _t["id"] = team_ids[_t["lag"]]

# Färg per lag (hex, utan #) – används i Excel och som info.
team_colors = {
    "P15 Blå":    "2E5C8A",
    "P15 Orange": "C0622A",
    "P15 Vit":    "7A7A7A",
    "F15 Blå":    "3A78C2",
    "F15 Gul":    "B8961F",
    "F15 Vit":    "9C5A8C",
}


def short_klass(klass):
    return "P15" if klass.startswith("Pojkar") else "F15"


def iter_matches(team):
    """Ger dict per match med härledd hemma/borta-info för Alingsås."""
    nm = team["namn_i_schema"]
    for (datum, dag, tid, bana, hemma, borta) in team["matcher"]:
        hb = "Hemma" if hemma == nm else "Borta"
        mots = borta if hemma == nm else hemma
        yield {
            "datum": datum, "dag": dag, "tid": tid, "bana": bana,
            "lag": team["lag"], "klass": short_klass(team["klass"]),
            "klass_full": team["klass"], "grupp": team["grupp"],
            "hemma": hemma, "borta": borta, "mots": mots, "hb": hb,
            "slug": team["slug"],
        }


def all_matches():
    rows = []
    for t in teams:
        rows.extend(iter_matches(t))
    return rows
