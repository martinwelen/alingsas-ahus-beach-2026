#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spelartrupper per Alingsås-lag på Åhus Beach Handboll 2026.

Statisk källa (cupmanager har ingen spelardata). Keyad på lagets `slug`,
samma slugs som i matches_data.teams. build_site.py bäddar in detta i sidan.

Per spelare:
  namn  (krav)         hela namnet
  nr    (valfritt)     tröjnummer (int)
  pos   (valfritt)     "MV" (målvakt) eller "UT" (utespelare)
  smek  (valfritt)     smeknamn

Lägg till spelare här och kör build_site.py (eller låt molnroboten bygga om).
Inga tränare/ledare, inget födelseår. Lag utan publicerad trupp: tom lista.
"""

rosters = {
    "p15-bla": [
        {"namn": "Oskar Viklund", "pos": "UT"},
        {"namn": "Alfred Lindblad", "pos": "MV", "smek": "Affe"},
        {"namn": "Theodor Kangas", "pos": "UT"},
        {"namn": "Maurits Fridberg", "pos": "UT", "smek": "Marre"},
        {"namn": "Filip Holmgren", "pos": "UT"},
        {"namn": "Terje Hegge", "pos": "UT"},
    ],
    "p15-orange": [
        {"namn": "Olle Laas", "pos": "MV"},
        {"namn": "Hjalmar Oscarsson", "pos": "UT", "smek": "Hjalle"},
        {"namn": "Alexander Westberg", "pos": "UT"},
        {"namn": "Theodor Herou", "pos": "UT"},
        {"namn": "Fabian Mattsson", "pos": "UT", "smek": "Fabbe"},
        {"namn": "Frank Jannerland", "pos": "UT"},
    ],
    "p15-vit": [
        {"namn": "Samuel Welén", "pos": "MV"},
        {"namn": "Filip Landström", "pos": "UT"},
        {"namn": "Sixten Herbertsson", "pos": "UT"},
        {"namn": "Filip Larsson", "pos": "UT"},
        {"namn": "Liam Bergaoui", "pos": "UT"},
        {"namn": "Love Jönsson", "pos": "UT"},
    ],
    "f15-bla": [],
    "f15-gul": [],
    "f15-vit": [],
}
