# Alingsås HK – Åhus Beach Handboll 2026

Live-uppdaterat matchschema för Alingsås HK:s sex lag (3× P15 + 3× F15),
samt prenumererbara kalendrar (iCal) och ett Excel-dokument.

**Schemasida (öppna / lägg till på hemskärmen):**
https://martinwelen.github.io/alingsas-ahus-beach-2026/

Sidan uppdateras **automatiskt** av en robot i GitHubs moln – ingen dator behöver
köra något. Roboten hämtar från cupmanager, bygger om allt och publicerar.

## Kalendrar att prenumerera på

Bas: `https://martinwelen.github.io/alingsas-ahus-beach-2026/ics/`

| Kalender | Fil |
|----------|-----|
| Alla sex lag | `alingsas-alla.ics` |
| P15 Blå / Orange / Vit | `alingsas-p15-bla.ics` · `-p15-orange.ics` · `-p15-vit.ics` |
| F15 Blå / Gul / Vit | `alingsas-f15-bla.ics` · `-f15-gul.ics` · `-f15-vit.ics` |

> **Prenumerera på URL:en – importera inte filen** (importerade filer uppdateras aldrig).
> Android/Outlook: lägg till via outlook.com i en webbläsare. iPhone: Inställningar →
> Kalender → Lägg till prenumererad kalender.

## Så fungerar automatiken

```
fetch_matches.py   → hämtar via cupmanagers API (filtrerar på de 6 lagens id)
                     och skriver matches.json (bara om datan ändrats)
schedule.py        → gemensam laddare (matches.json, annars seed i matches_data.py)
build_site.py      → index.html (live-schema) + manifest.json + favicon.svg
build_ics.py       → ics/*.ics (7 kalendrar, stabila UID, SEQUENCE = ändringstid)
build_excel.py     → Alingsas_HK_Ahus_Beach_2026.xlsx
.github/workflows/update.yml → cron var 30:e min + manuell knapp; committar vid ändring
```

Eftersom filtreringen sker på lagens **id** plockas slutspelsmatcher upp
automatiskt så fort Alingsås lottats in i dem – inget handpåläggande.

## Köra manuellt (om man vill)

```bash
pip install openpyxl
python fetch_matches.py     # uppdaterar matches.json från cupmanager
python build_ics.py && python build_excel.py && python build_site.py
```

Eller starta molnroboten direkt: repo → **Actions → Uppdatera schema → Run workflow**.

Matchtid: 2×5 min + 60 s paus. Speldagar fre 17/7 + lör 18/7 2026.
Källa: ahusbeachhandboll.cupmanager.net
