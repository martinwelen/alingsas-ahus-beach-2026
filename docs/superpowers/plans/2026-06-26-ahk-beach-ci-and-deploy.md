# AHK Beach – CI & Deploy Implementation Plan (Plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.
>
> ⚠️ **This plan contains OUTWARD-FACING actions** (creating a GitHub repo, pushing, enabling Pages). Those are NOT performed autonomously — they require the user's explicit go-ahead in chat, and the user runs the auth-bound commands (or confirms each). Do the local, reversible tasks (1–2) first; pause for confirmation before tasks 3–5.

**Goal:** Put the `ahk-beach` repo online: a GitHub Actions cron that re-fetches and rebuilds on change, the repo pushed to GitHub, and GitHub Pages serving the hub + per-age-group apps.

**Architecture:** Mirrors the proven `alingsas-ahus-beach-2026` CI: a scheduled workflow fetches `data.json` + `standings.json`, and only when those change rebuilds all apps/ics/hub and commits. A `.nojekyll` guard stops GitHub Pages from Jekyll-processing the repo (the same trap the live repo hit). Build outputs (`/uXX/`, `data.json`, `standings.json`, `index.html`) are committed artifacts.

**Tech Stack:** GitHub Actions (YAML), `gh` CLI, GitHub Pages. No new Python.

**Prerequisite:** Plans 1 & 2 complete — `build_all.py` runs locally and produces the hub + 9 app dirs; all tests pass.

**Reference:** `/home/martin/dev/ahusbeach/.github/workflows/update.yml` (the workflow to adapt). Memory `pages-nojekyll-gotcha` — keep `.nojekyll`.

---

## File Structure

In `~/dev/ahk-beach/`:
- Create: `.github/workflows/update.yml` — scheduled fetch + conditional rebuild + commit/push.
- Create: `.nojekyll` — empty file; stops Jekyll processing on Pages.
- (No code changes; build outputs already produced by Plan 2 are committed.)

---

## Task 1: Add `.nojekyll` and confirm build outputs are tracked

**Files:** Create `.nojekyll`.

*(Local, reversible — no authorization needed.)*

- [ ] **Step 1: Create the Jekyll guard**
```bash
cd ~/dev/ahk-beach
touch .nojekyll
```

- [ ] **Step 2: Confirm build artifacts are NOT gitignored** (they must be committed so Pages serves them)
```bash
cd ~/dev/ahk-beach
cat .gitignore         # must NOT list data.json, standings.json, index.html, or u*/
git status --short     # after a build, u*/, data.json, standings.json, index.html should be addable
```
Expected: `.gitignore` only lists `__pycache__/`, `*.pyc`, `.pytest_cache/`. If any build output is ignored, remove that line.

- [ ] **Step 3: Stage and commit current build outputs + guard**
```bash
cd ~/dev/ahk-beach
python3 build_all.py
git add -A
git commit -q -m "chore: add .nojekyll guard; commit built apps, hub, data, standings"
git log --oneline -1
```

---

## Task 2: Add the GitHub Actions workflow

**Files:** Create `.github/workflows/update.yml`.

*(Local file — no authorization needed to create; it only runs after the repo is on GitHub.)*

- [ ] **Step 1: Create `~/dev/ahk-beach/.github/workflows/update.yml`:**
```yaml
name: Uppdatera schema

# Kör i GitHubs moln – ingen lokal dator behövs.
on:
  schedule:
    - cron: "*/30 * * * *"          # normalt: var 30:e minut (no-op om inget ändrats)
    - cron: "*/10 * 9-18 7 *"       # turneringsveckan 9–18 juli: var 10:e minut
  workflow_dispatch:                 # + manuell "Run workflow"-knapp

concurrency:
  group: update-schema
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Hämta matcher (klubbkod) från cupmanager
        run: python fetch_data.py

      - name: Hämta tabeller & slutspel från cupmanager
        run: python fetch_standings.py

      - name: Avgör om datan ändrats
        id: changed
        run: |
          if git diff --quiet -- data.json standings.json; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            echo "data.json + standings.json oförändrade – hoppar över bygge/commit."
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Bygg om appar, kalendrar och hubb
        if: steps.changed.outputs.changed == 'true'
        run: |
          python build_apps.py
          python build_ics.py
          python build_hub.py

      - name: Committa och publicera
        if: steps.changed.outputs.changed == 'true'
        run: |
          git config user.name "ahk-beach-bot"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -m "Auto-uppdatering ($(date -u '+%Y-%m-%d %H:%M UTC'))"
          git push
          echo "Ändringar publicerade."
```
> Notes: no `pip install` step (stdlib only — no Excel/openpyxl in this repo). The frequent cron covers the whole tournament window (9–18 July), not just one weekend, because the club's age groups play across all those days.

- [ ] **Step 2: Validate the YAML parses**
```bash
cd ~/dev/ahk-beach
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/update.yml')); print('yaml ok')" 2>/dev/null \
  || python3 -c "print('yaml module not present; skip — GitHub will validate on push')"
```

- [ ] **Step 3: Commit**
```bash
cd ~/dev/ahk-beach
git add .github/workflows/update.yml
git commit -q -m "ci: scheduled fetch + conditional rebuild workflow"
```

---

## ⏸ CONFIRMATION GATE

Tasks 3–5 create a public GitHub repo, push code, and enable Pages — outward-facing and not easily reversible. **Stop here and get the user's explicit go-ahead.** Present: the repo name (`ahk-beach`), that it will be **public**, the resulting URL (`https://martinwelen.github.io/ahk-beach/`), and that the live U15 repo is untouched. The user runs the `gh`/push commands themselves (or confirms each), since they are auth-bound. Do not proceed autonomously.

---

## Task 3: Create the GitHub repo and push (USER-AUTHORIZED)

- [ ] **Step 1: User confirms** repo name `ahk-beach`, visibility **public**, account `martinwelen`.

- [ ] **Step 2: Create + push** (user runs this, or confirms running it):
```bash
cd ~/dev/ahk-beach
gh repo create martinwelen/ahk-beach --public --source=. --remote=origin --push
```
Expected: repo created, all commits pushed, `origin` set. If `gh` is not authenticated, the user runs `gh auth login` first (interactive — suggest the user type `! gh auth login`).

- [ ] **Step 3: Verify**
```bash
cd ~/dev/ahk-beach
git remote -v
gh repo view martinwelen/ahk-beach --web   # opens the repo
```

---

## Task 4: Enable GitHub Pages (USER-AUTHORIZED)

- [ ] **Step 1: Enable Pages** from branch `main`, folder `/ (root)`. Either via the web UI (Settings → Pages → Source: Deploy from a branch → `main` / `root` → Save) or via `gh`:
```bash
gh api -X POST repos/martinwelen/ahk-beach/pages \
  -f "source[branch]=main" -f "source[path]=/" 2>/dev/null \
  || echo "If this errors, enable Pages via Settings → Pages in the browser."
```

- [ ] **Step 2: Wait for the first Pages deploy** (~1–2 min), then verify the URLs respond:
```bash
sleep 90
for u in "" "u14/" "u8/"; do
  echo -n "https://martinwelen.github.io/ahk-beach/$u → "
  curl -s -o /dev/null -w "%{http_code}\n" "https://martinwelen.github.io/ahk-beach/$u"
done
```
Expected: `200` for the hub (root), `u14/` (a Classic app), and `u8/` (a Mini app).

---

## Task 5: Trigger one workflow run and verify the loop

- [ ] **Step 1: Manually dispatch the workflow** (proves the cron path end-to-end):
```bash
cd ~/dev/ahk-beach
gh workflow run "Uppdatera schema"
sleep 20
gh run list --workflow "Uppdatera schema" --limit 1
```

- [ ] **Step 2: Watch it complete and confirm no-op behavior** (data unchanged since the local build → it should skip commit):
```bash
gh run watch "$(gh run list --workflow 'Uppdatera schema' --limit 1 --json databaseId -q '.[0].databaseId')"
```
Expected: green run; logs show "oförändrade – hoppar över bygge/commit" (since nothing changed since the committed build). This proves the hash-guard prevents no-op commits.

- [ ] **Step 3: Final manual check in a browser**: open the hub, install one app to the home screen, confirm a Mini app shows schedule-only and a Classic app shows tables/bracket. Confirm the U15 card links to the live repo's URL.

---

## Self-Review

**Spec coverage:** scheduled cloud fetch + conditional rebuild + commit (Task 2, mirrors the proven live workflow); `.nojekyll` guard (Task 1, per the known Pages/Jekyll trap); repo creation + push + Pages (Tasks 3–4, user-authorized); end-to-end loop verification incl. no-op hash-guard (Task 5). The live U15 repo is never touched — `ahk-beach` is a separate origin.

**Placeholder scan:** No TBD/TODO. Commands are concrete. The `gh api` Pages call has an explicit browser fallback.

**Safety:** Outward-facing steps (3–5) are gated behind an explicit confirmation section and run by the user with their own auth. Local/reversible steps (1–2) run freely.

**Open decision (resolved):** build outputs are committed artifacts (consistent with `data.json` from Plan 1 and the live repo). If the committed-build noise is later unwanted, a future change could move building into the Pages deploy step instead — out of scope here.
