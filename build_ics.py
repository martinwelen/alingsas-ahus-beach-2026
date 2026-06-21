#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genererar iCalendar-filer (.ics) för Alingsås HK:s matcher på
Åhus Beach Handboll 2026.

Skapar:
  ics/alingsas-<lag>.ics   (en per lag, 6 st)
  ics/alingsas-alla.ics    (alla sex lag i en kalender)

Designval för prenumeration:
  • Stabilt UID per match (lag + motståndare) → uppdateringar ÄNDRAR matchen
    istället för att skapa dubbletter, även om tid/bana flyttas.
  • SEQUENCE = REVISION och DTSTAMP/LAST-MODIFIED = LAST_UPDATED → bumpa dessa
    i matches_data.py vid uppdatering så kalenderappar plockar upp ändringar.
  • Tider skrivs i UTC (Z). Juli i Åhus = CEST = UTC+2.
"""

import os
import re
import unicodedata

from matches_data import (
    teams, team_colors, all_matches, iter_matches,
    REVISION, LAST_UPDATED, MATCH_DURATION_MIN, UTC_OFFSET_HOURS,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "ics")
PRODID = "-//Alingsas HK//Ahus Beach Handboll 2026//SV"
SOURCE_NOTE = "Källa: ahusbeachhandboll.cupmanager.net"

# GitHub Pages-bas där filerna hostas (för prenumerationslänkar).
PAGES_HOST = "martinwelen.github.io"
PAGES_PATH = "/alingsas-ahus-beach-2026"
PAGES_BASE = f"https://{PAGES_HOST}{PAGES_PATH}"


# ---------------------------------------------------------------------------
# Hjälpare
# ---------------------------------------------------------------------------
def dtstamp_compact(iso_utc):
    """'2026-06-21T12:00:00Z' -> '20260621T120000Z'."""
    return re.sub(r"[-:]", "", iso_utc)


def to_utc_stamp(datum, tid):
    """('2026-07-17','13:45') lokal CEST -> UTC-stämpel '20260717T114500Z'."""
    y, mo, d = (int(x) for x in datum.split("-"))
    hh, mm = (int(x) for x in tid.split(":"))
    # subtrahera offset för att gå från lokal tid till UTC
    total_min = hh * 60 + mm - UTC_OFFSET_HOURS * 60
    # alla matcher är mitt på dagen → ingen dygnsövergång, men hantera ändå
    day_shift, total_min = divmod(total_min, 24 * 60)
    hh, mm = divmod(total_min, 60)
    d += day_shift
    return f"{y:04d}{mo:02d}{d:02d}T{hh:02d}{mm:02d}00Z"


def add_minutes_stamp(stamp, minutes):
    """Lägg till minuter på en UTC-stämpel 'YYYYMMDDThhmmssZ'."""
    y = int(stamp[0:4]); mo = int(stamp[4:6]); d = int(stamp[6:8])
    hh = int(stamp[9:11]); mm = int(stamp[11:13])
    total = hh * 60 + mm + minutes
    day_shift, total = divmod(total, 24 * 60)
    hh, mm = divmod(total, 60)
    d += day_shift
    return f"{y:04d}{mo:02d}{d:02d}T{hh:02d}{mm:02d}00Z"


def slugify_ascii(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def uid_for(m):
    """Stabilt UID: bygger på lag + motståndare (varje lag möter varje
    motståndare en gång i gruppspelet). Tål ändrad tid/bana."""
    base = f"{m['slug']}-vs-{slugify_ascii(m['mots'])}-{slugify_ascii(m['grupp'])}"
    return f"{base}@ahusbeach2026.cupmanager.net"


def esc(text):
    """Escapa TEXT-värde enligt RFC 5545."""
    return (text.replace("\\", "\\\\")
                .replace(";", "\\;")
                .replace(",", "\\,")
                .replace("\n", "\\n"))


def fold(line):
    """Vik rader till <=75 oktetter (RFC 5545), utan att klippa mitt i ett
    UTF-8-tecken. Fortsättningsrader inleds med ett mellanslag."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts = []
    start = 0
    limit = 75
    while start < len(raw):
        end = min(start + limit, len(raw))
        # backa så vi inte delar ett multibyte-tecken
        while end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        parts.append(raw[start:end])
        start = end
        limit = 74  # fortsättningsrader får ett inledande mellanslag
    out = parts[0].decode("utf-8")
    for p in parts[1:]:
        out += "\r\n " + p.decode("utf-8")
    return out


def vevent(m):
    dtstart = to_utc_stamp(m["datum"], m["tid"])
    dtend = add_minutes_stamp(dtstart, MATCH_DURATION_MIN)
    summary = f"{m['lag']}: {m['hemma']} – {m['borta']}"
    location = f"Bana {m['bana']}, Åhus Beach Handboll, Åhus"
    desc = (f"{m['klass_full']}\\n{m['grupp']} – Gruppspel\\n"
            f"Alingsås spelar {m['hb'].lower()}lag mot {m['mots']}.\\n"
            f"Avspark {m['tid']} (lokal tid). Matchtid 2×5 min + 60 s paus.\\n{SOURCE_NOTE}")
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid_for(m)}",
        f"DTSTAMP:{dtstamp_compact(LAST_UPDATED)}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{esc(summary)}",
        f"LOCATION:{esc(location)}",
        f"DESCRIPTION:{desc}",  # redan escapad där det behövs (\\n)
        f"SEQUENCE:{REVISION}",
        f"LAST-MODIFIED:{dtstamp_compact(LAST_UPDATED)}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "END:VEVENT",
    ]
    return lines


def build_calendar(rows, cal_name, cal_desc):
    rows = sorted(rows, key=lambda m: (m["datum"], m["tid"], m["bana"]))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(cal_name)}",
        "X-WR-TIMEZONE:Europe/Stockholm",
        f"X-WR-CALDESC:{esc(cal_desc)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for m in rows:
        lines.extend(vevent(m))
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def build_index_html(catalog):
    """catalog: lista av (titel, undertitel, ics-filnamn, antal, färg)."""
    def card(titel, under, fn, n, farg, primar=False):
        ics_url = f"{PAGES_BASE}/ics/{fn}"
        webcal = f"webcal://{PAGES_HOST}{PAGES_PATH}/ics/{fn}"
        gcal = "https://calendar.google.com/calendar/r?cid=" + webcal
        cls = "card primary" if primar else "card"
        return f"""      <div class="{cls}" style="--accent:#{farg}">
        <div class="card-head"><span class="dot"></span>
          <div><h3>{titel}</h3><p class="sub">{under} · {n} matcher</p></div>
        </div>
        <div class="actions">
          <a class="btn btn-main" href="{webcal}">Prenumerera</a>
          <a class="btn" href="{gcal}" target="_blank" rel="noopener">Google&nbsp;Calendar</a>
          <a class="btn btn-ghost" href="ics/{fn}" download>Ladda ner .ics</a>
        </div>
        <code class="url">{ics_url}</code>
      </div>"""

    cards = "\n".join(card(*c[:5], primar=c[5]) for c in catalog)
    return f"""<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alingsås HK – Åhus Beach Handboll 2026 · Matchkalendrar</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
         background:#0f1c2e; color:#eaf0f7; line-height:1.5; }}
  .wrap {{ max-width: 760px; margin:0 auto; padding: 32px 20px 64px; }}
  header h1 {{ font-size: clamp(1.5rem,4vw,2.2rem); margin:0 0 6px; }}
  header p {{ margin:0 0 4px; color:#a9bcd4; }}
  .grid {{ display:grid; gap:14px; margin-top:28px; }}
  .card {{ background:#16263d; border:1px solid #243750; border-left:5px solid var(--accent);
          border-radius:12px; padding:16px 18px; }}
  .card.primary {{ background:#1b3150; }}
  .card-head {{ display:flex; align-items:center; gap:12px; }}
  .dot {{ width:14px; height:14px; border-radius:50%; background:var(--accent); flex:0 0 auto; }}
  h3 {{ margin:0; font-size:1.05rem; }}
  .sub {{ margin:2px 0 0; font-size:.85rem; color:#a9bcd4; }}
  .actions {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }}
  .btn {{ display:inline-block; padding:8px 14px; border-radius:8px; font-size:.9rem;
         font-weight:600; text-decoration:none; background:#27405f; color:#eaf0f7;
         border:1px solid #36527a; }}
  .btn-main {{ background:var(--accent); color:#fff; border-color:transparent; }}
  .btn-ghost {{ background:transparent; }}
  .btn:hover {{ filter:brightness(1.12); }}
  .url {{ display:block; margin-top:12px; font-size:.72rem; color:#7e93ad; word-break:break-all; }}
  .info {{ margin-top:36px; background:#16263d; border:1px solid #243750; border-radius:12px; padding:18px 20px; }}
  .info h2 {{ margin:0 0 10px; font-size:1.1rem; }}
  .info li {{ margin:4px 0; }}
  footer {{ margin-top:32px; font-size:.8rem; color:#7e93ad; }}
  a {{ color:#7db3ff; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Alingsås HK – Åhus Beach Handboll 2026</h1>
    <p>Matchkalendrar att prenumerera på. Uppdateras löpande – ändrade tider/banor
       slår igenom automatiskt i din kalender.</p>
    <p>Speldagar: <strong>fredag 17 juli</strong> &amp; <strong>lördag 18 juli 2026</strong>.</p>
  </header>

  <div class="grid">
{cards}
  </div>

  <div class="info">
    <h2>Så prenumererar du</h2>
    <ul>
      <li><strong>iPhone/iPad &amp; Mac:</strong> tryck på <em>Prenumerera</em> – kalendern öppnas och du bekräftar.</li>
      <li><strong>Google Kalender:</strong> tryck på <em>Google Calendar</em> (funkar bäst på dator) eller lägg till URL:en under
          ”Andra kalendrar → Från URL”.</li>
      <li><strong>Outlook:</strong> Lägg till kalender → Prenumerera från webben → klistra in .ics-URL:en.</li>
    </ul>
    <p style="font-size:.85rem;color:#a9bcd4;margin-bottom:0">
      Obs: gruppspelet (51 matcher). Slutspelet på lördag em avgörs av resultaten och läggs till när lottningen är klar.
      Matchtid: 2×5 min + 60 s paus. Tider kan ändras av arrangören.</p>
  </div>

  <footer>
    Källa: ahusbeachhandboll.cupmanager.net · Senast uppdaterad {LAST_UPDATED}
  </footer>
</div>
</body>
</html>
"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    written = []
    catalog = []

    # Samlad – läggs först i listan (primärt kort)
    rows = all_matches()
    fn = "alingsas-alla.ics"
    cal = build_calendar(
        rows,
        cal_name="Alingsås HK (alla lag) – Åhus Beach 2026",
        cal_desc=f"Alla sex lag (3× P15 + 3× F15), gruppspel. {SOURCE_NOTE}",
    )
    with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8", newline="") as f:
        f.write(cal)
    written.append((fn, len(rows)))
    catalog.append(("Alla sex lag", "P15 + F15 – hela klubben", fn, len(rows), "1F3864", True))

    # En per lag
    for t in teams:
        rows = list(iter_matches(t))
        fn = f"alingsas-{t['slug']}.ics"
        cal = build_calendar(
            rows,
            cal_name=f"{t['fullnamn']} – Åhus Beach 2026",
            cal_desc=f"{t['klass']} • {t['grupp']}. {SOURCE_NOTE}",
        )
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8", newline="") as f:
            f.write(cal)
        written.append((fn, len(rows)))
        catalog.append((t["fullnamn"], f"{t['klass']} · {t['grupp']}",
                        fn, len(rows), team_colors[t["lag"]], False))

    # Landningssida
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index_html(catalog))

    print(f"REVISION={REVISION}  LAST_UPDATED={LAST_UPDATED}")
    for fn, n in written:
        print(f"  {fn:28s} {n} matcher")
    print("  index.html genererad")


if __name__ == "__main__":
    main()
