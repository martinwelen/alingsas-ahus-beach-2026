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
