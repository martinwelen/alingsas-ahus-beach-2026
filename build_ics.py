#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genererar iCalendar-filer (.ics) för Alingsås HK:s matcher.

  ics/alingsas-<lag>.ics   (en per lag)
  ics/alingsas-alla.ics    (alla sex lag)

Data via schedule.load_matches() (matches.json om den finns, annars seed).
Prenumeration: stabilt UID per match → uppdateringar ändrar matchen i stället
för att skapa dubbletter. SEQUENCE/DTSTAMP drivs av meta (seq/generated) så
ändringar plockas upp av kalenderappar. Tider skrivs i UTC.
"""

import os
from datetime import datetime, timezone, timedelta

import matches_data as md
import schedule as sch

OUT_DIR = os.path.join(sch.ROOT, "ics")
PRODID = "-//Alingsas HK//Ahus Beach Handboll 2026//SV"
SOURCE_NOTE = "Källa: ahusbeachhandboll.cupmanager.net"
DURATION_MS = md.MATCH_DURATION_MIN * 60 * 1000


def ms_to_utc(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso_to_utc_compact(iso):
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slug_ascii(s):
    import unicodedata, re
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def uid_for(m):
    base = f"{m['slug']}-vs-{slug_ascii(m['mots'])}-{slug_ascii(str(m['grupp']))}"
    return f"{base}@ahusbeach2026.cupmanager.net"


def esc(t):
    return (t.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, start, limit = [], 0, 75
    while start < len(raw):
        end = min(start + limit, len(raw))
        while end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        parts.append(raw[start:end]); start = end; limit = 74
    return parts[0].decode("utf-8") + "".join("\r\n " + p.decode("utf-8") for p in parts[1:])


def vevent(m, seq, dtstamp):
    dtstart = ms_to_utc(m["start_ms"])
    dtend = ms_to_utc(m["start_ms"] + DURATION_MS)
    summary = f"{m['lag']}: {m['hemma']} – {m['borta']}"
    location = f"Bana {m['bana']}, Åhus Beach Handboll, Åhus"
    desc = (f"{sch.TEAM_BY_SLUG[m['slug']]['klass']}\\n{m['grupp']}\\n"
            f"Alingsås spelar {m['hb'].lower()}lag mot {m['mots']}.\\n"
            f"Avspark {m['tid']} (lokal tid). Matchtid 2×5 min + 60 s paus.\\n{SOURCE_NOTE}")
    return [
        "BEGIN:VEVENT", f"UID:{uid_for(m)}", f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}", f"DTEND:{dtend}",
        f"SUMMARY:{esc(summary)}", f"LOCATION:{esc(location)}",
        f"DESCRIPTION:{desc}", f"SEQUENCE:{seq}", f"LAST-MODIFIED:{dtstamp}",
        "STATUS:CONFIRMED", "TRANSP:OPAQUE", "END:VEVENT",
    ]


def build_calendar(rows, cal_name, cal_desc, seq, dtstamp):
    rows = sorted(rows, key=lambda m: (m["start_ms"], str(m["bana"])))
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(cal_name)}", "X-WR-TIMEZONE:Europe/Stockholm",
        f"X-WR-CALDESC:{esc(cal_desc)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H",
    ]
    for m in rows:
        lines += vevent(m, seq, dtstamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    matches, meta = sch.load_matches()
    seq = int(meta.get("seq", md.REVISION))
    dtstamp = iso_to_utc_compact(meta.get("generated", md.LAST_UPDATED))
    groups = sch.by_team(matches)

    def write(fn, rows, name, desc):
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8", newline="") as f:
            f.write(build_calendar(rows, name, desc, seq, dtstamp))
        print(f"  {fn:28s} {len(rows)} matcher")

    write("alingsas-alla.ics", matches,
          "Alingsås HK (alla lag) – Åhus Beach 2026",
          f"Alla sex lag (3× P15 + 3× F15). {SOURCE_NOTE}")
    for t in md.teams:
        write(f"alingsas-{t['slug']}.ics", groups.get(t["slug"], []),
              f"{t['fullnamn']} – Åhus Beach 2026",
              f"{t['klass']} • {t['grupp']}. {SOURCE_NOTE}")
    print(f"källa={meta.get('source')} seq={seq}")


if __name__ == "__main__":
    main()
