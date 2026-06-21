# Alingsås HK – Åhus Beach Handboll 2026

Prenumererbara matchkalendrar (iCal/.ics) för Alingsås HK:s sex lag
(3× P15 + 3× F15) under Åhus Beach Handboll 2026, samt ett Excel-dokument.

**Landningssida med prenumerationslänkar:**
https://martinwelen.github.io/alingsas-ahus-beach-2026/

## Kalendrar

| Kalender | Prenumerera (webcal) |
|----------|----------------------|
| Alla sex lag | `webcal://martinwelen.github.io/alingsas-ahus-beach-2026/ics/alingsas-alla.ics` |
| P15 Blå | `.../ics/alingsas-p15-bla.ics` |
| P15 Orange | `.../ics/alingsas-p15-orange.ics` |
| P15 Vit | `.../ics/alingsas-p15-vit.ics` |
| F15 Blå | `.../ics/alingsas-f15-bla.ics` |
| F15 Gul | `.../ics/alingsas-f15-gul.ics` |
| F15 Vit | `.../ics/alingsas-f15-vit.ics` |

Innehåller gruppspelets 51 matcher (fre 17/7 + lör 18/7 2026).
Matchtid: 2×5 min + 60 s paus. Slutspelet (lör em) avgörs av resultaten
och läggs till när lottningen är klar.

## Innehåll i repot

- `matches_data.py` – **enda sanningskällan** för matchdatan (alla sex lag).
- `build_ics.py` – genererar `ics/*.ics` + `index.html`.
- `build_excel.py` – genererar `Alingsas_HK_Ahus_Beach_2026.xlsx`.
- `ics/` – de publicerade kalenderfilerna.
- `index.html` – landningssida (GitHub Pages).

## Uppdatera efter kontroll mot cupsidan

1. Kör en kontroll mot https://ahusbeachhandboll.cupmanager.net/2026,sv/result/
   (lagsidorna) och se om någon tid/bana/motståndare ändrats, eller om
   slutspelsmatcher blivit fastställda.
2. Ändra i `matches_data.py`. **Bumpa `REVISION` (+1) och sätt nytt
   `LAST_UPDATED`** så prenumeranternas kalenderappar plockar upp ändringen.
3. Generera om och publicera:
   ```bash
   python3 build_ics.py && python3 build_excel.py
   git commit -am "Uppdatera schema (rev N)" && git push
   ```

Stabila UID per match (lag + motståndare) gör att ändrade tider/banor
**uppdaterar** befintliga kalenderposter i stället för att skapa dubbletter.

Källa: ahusbeachhandboll.cupmanager.net (lagsidorna).
