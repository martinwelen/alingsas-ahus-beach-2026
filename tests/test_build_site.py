# -*- coding: utf-8 -*-
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build():
    """Kör build_site.py och returnerar genererad index.html som sträng."""
    subprocess.run([sys.executable, "build_site.py"], cwd=ROOT, check=True)
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


def test_tables_render_function_uses_filter_and_tiers():
    html = _build()
    assert "function renderTables()" in html
    assert "tier-row" in html          # CSS-klass för A/B/C-avdelarrad
    assert "groupsForFilter" in html   # hjälpare som väljer grupper enligt filter


def test_bracket_render_present():
    html = _build()
    assert "function renderBracket()" in html
    assert "bracket-scroll" in html     # pan-container
    assert "pointerdown" in html        # dra-med-finger
    assert "bm-win" in html             # vinnar-accentklass
    assert "bm-lose" in html            # förlorar-strike-through-klass


def test_graceful_without_standings():
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
        assert 'id="tab-tabeller"' in html        # markup finns men startar hidden
    finally:
        if had:
            os.rename(bak, src)
