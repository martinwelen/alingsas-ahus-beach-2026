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
