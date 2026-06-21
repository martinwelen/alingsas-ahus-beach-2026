#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genererar den live-uppdaterade schemasidan (index.html) + manifest + favicon.

Designidé: "sun-bleached sporty editorial" – ljust sandtema med hög kontrast
(läses utomhus i solen på plats), djup havsblå text, korall-accent för nu/härnäst,
kondenserad display-typografi (Anton). Lagfärgskodat, filter, live-nedräkning.

Data via schedule.load_matches() (matches.json om den finns, annars seed).
"""

import os
import json
from datetime import datetime

import matches_data as md
import schedule as sch

DUR_MIN = md.MATCH_DURATION_MIN
SV_MONTHS = sch.SV_MONTHS


def human_updated(meta):
    iso = meta.get("generated", md.LAST_UPDATED)
    try:
        dt = datetime.fromisoformat(iso).astimezone(sch.CEST)
        return f"{dt.day} {SV_MONTHS[dt.month]} {dt.year}, {dt:%H:%M}"
    except Exception:
        return iso


def cal_section():
    """Liten 'lägg till i kalender'-sektion (sekundär, valfri)."""
    base = md.PAGES_BASE
    rows = [("Alla sex lag", "alingsas-alla.ics", "1F3864")]
    for t in md.teams:
        rows.append((t["fullnamn"], f"alingsas-{t['slug']}.ics", md.team_colors[t["lag"]]))
    items = []
    for namn, fn, col in rows:
        url = f"{base}/ics/{fn}"
        items.append(
            f'<li><span class="cdot" style="background:#{col}"></span>'
            f'<span class="cname">{namn}</span>'
            f'<button class="copy mini" data-url="{url}">Kopiera länk</button></li>')
    return "\n".join(items)


TEMPLATE = r"""<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Alingsås HK · Åhus Beach Handboll 2026</title>
<meta name="theme-color" content="#13293d">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Alingsås Åhus">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="manifest.json">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Hanken+Grotesk:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --sand:#f4ecdb; --paper:#fffaf0; --ink:#13293d; --ink-soft:#6a7c8b;
  --sun:#ef5a2b; --sun-2:#f7a23a; --sea:#1583ad; --line:#e7dabf;
  --shadow:0 6px 22px rgba(20,40,60,.10);
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  font-family:"Hanken Grotesk",system-ui,sans-serif; color:var(--ink);
  background:
    radial-gradient(900px 460px at 108% -8%, rgba(247,162,58,.55), rgba(247,162,58,0) 60%),
    radial-gradient(700px 380px at -10% 0%, rgba(21,131,173,.20), rgba(21,131,173,0) 55%),
    var(--sand);
  background-attachment:fixed;
  -webkit-text-size-adjust:100%; line-height:1.45;
}
body::before{ /* korn/grynighet */
  content:""; position:fixed; inset:0; pointer-events:none; opacity:.5; z-index:0;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2'/><feColorMatrix type='saturate' values='0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='.045'/></svg>");
}
.wrap{position:relative; z-index:1; max-width:720px; margin:0 auto; padding:0 16px 72px}
header{padding:26px 0 8px}
.kicker{font-size:.74rem; letter-spacing:.22em; text-transform:uppercase; color:var(--sea); font-weight:700}
h1{font-family:"Anton",sans-serif; font-weight:400; line-height:.94; letter-spacing:.01em;
   font-size:clamp(2.3rem,9vw,3.4rem); margin:.18em 0 .1em; text-transform:uppercase}
h1 .em{color:var(--sun)}
.dates{color:var(--ink-soft); font-weight:600; font-size:.96rem}
.sea-rule{height:5px; border-radius:5px; margin:14px 0 0;
  background:linear-gradient(90deg,var(--sea),var(--sun-2),var(--sun))}

/* filter */
.filters{position:sticky; top:0; z-index:5; margin:0 -16px; padding:12px 16px;
  display:flex; gap:8px; overflow-x:auto; scrollbar-width:none;
  background:linear-gradient(var(--sand),rgba(244,236,219,.86)); backdrop-filter:blur(6px);
  border-bottom:1px solid var(--line)}
.filters::-webkit-scrollbar{display:none}
.pill{flex:0 0 auto; border:1.5px solid var(--ink); background:transparent; color:var(--ink);
  padding:7px 13px; border-radius:999px; font-weight:700; font-size:.85rem; cursor:pointer;
  display:flex; align-items:center; gap:7px; white-space:nowrap; font-family:inherit;
  transition:all .15s}
.pill .d{width:9px; height:9px; border-radius:50%}
.pill[aria-pressed=true]{background:var(--ink); color:#fff}
.pill.sun[aria-pressed=true]{background:var(--sun); border-color:var(--sun)}

/* hero – härnäst */
.hero{margin-top:18px; border-radius:18px; padding:18px 20px; color:#fff; box-shadow:var(--shadow);
  background:linear-gradient(135deg,#16324a,#1b4a64); position:relative; overflow:hidden}
.hero.live{background:linear-gradient(135deg,var(--sun),var(--sun-2))}
.hero .lbl{font-size:.74rem; letter-spacing:.2em; text-transform:uppercase; font-weight:800; opacity:.92}
.hero .mt{font-family:"Anton",sans-serif; font-size:clamp(1.4rem,5.4vw,2rem); line-height:1.04; margin:.28em 0 .15em; text-transform:uppercase}
.hero .sub{font-weight:600; opacity:.92; font-size:.92rem}
.hero .cd{margin-top:12px; font-family:"Anton",sans-serif; font-size:1.5rem; letter-spacing:.02em}
.hero .tag{position:absolute; top:14px; right:16px; font-weight:800; font-size:.8rem;
  background:rgba(255,255,255,.18); padding:5px 10px; border-radius:999px}
.hero.live .pulse{display:inline-block; width:9px; height:9px; border-radius:50%; background:#fff; margin-right:6px; animation:pulse 1.1s infinite}
@keyframes pulse{0%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.7)}100%{opacity:1;transform:scale(1)}}

/* dagar + matcher */
.day{position:sticky; top:53px; z-index:3; margin:26px 0 10px; padding:6px 2px;
  font-family:"Anton",sans-serif; font-size:1.15rem; text-transform:uppercase; letter-spacing:.04em;
  background:linear-gradient(var(--sand),var(--sand)); }
.day::after{content:""; display:block; height:3px; width:46px; background:var(--sun); margin-top:5px; border-radius:3px}
.match{display:grid; grid-template-columns:56px 1fr auto; gap:13px; align-items:center;
  background:var(--paper); border:1px solid var(--line); border-left:6px solid var(--c,#999);
  border-radius:14px; padding:12px 13px; margin-bottom:9px; box-shadow:var(--shadow);
  animation:rise .4s both}
@keyframes rise{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
.match.past{opacity:.46}
.match.live{border-color:var(--sun); box-shadow:0 0 0 2px var(--sun), var(--shadow)}
.match .t{font-family:"Anton",sans-serif; font-size:1.42rem; line-height:1; text-align:center}
.match .t small{display:block; font-family:"Hanken Grotesk"; font-size:.62rem; font-weight:700;
  color:var(--ink-soft); letter-spacing:.08em; margin-top:3px}
.chips{display:flex; gap:6px; align-items:center; margin-bottom:4px; flex-wrap:wrap}
.lagchip{font-size:.66rem; font-weight:800; color:#fff; padding:2px 8px; border-radius:999px; letter-spacing:.02em}
.grp{font-size:.7rem; color:var(--ink-soft); font-weight:600}
.vs{font-weight:600; font-size:.98rem}
.vs .ali{font-weight:800}
.vs .ali::after{content:""}
.bana{text-align:center; min-width:46px}
.bana b{font-family:"Anton",sans-serif; font-size:1.3rem; display:block; line-height:1}
.bana small{font-size:.6rem; font-weight:800; letter-spacing:.1em; color:var(--ink-soft)}
.nowtag{font-size:.6rem; font-weight:800; color:var(--sun); letter-spacing:.08em}
.empty{padding:30px 4px; color:var(--ink-soft); text-align:center; font-weight:600}

/* kalender-sektion */
details.cal{margin-top:30px; background:var(--paper); border:1px solid var(--line); border-radius:14px; padding:4px 16px; box-shadow:var(--shadow)}
details.cal summary{cursor:pointer; font-weight:800; padding:13px 0; list-style:none}
details.cal summary::-webkit-details-marker{display:none}
details.cal summary::before{content:"📅  "}
.cal ul{list-style:none; padding:0; margin:6px 0 12px}
.cal li{display:flex; align-items:center; gap:10px; padding:7px 0; border-top:1px solid var(--line)}
.cdot{width:12px;height:12px;border-radius:50%;flex:0 0 auto}
.cname{flex:1; font-size:.9rem; font-weight:600}
.copy{border:1.5px solid var(--ink); background:transparent; color:var(--ink); border-radius:8px;
  padding:6px 11px; font-weight:700; font-size:.8rem; cursor:pointer; font-family:inherit}
.copy.mini{padding:5px 9px; font-size:.74rem}
.copy.ok{background:#1f8a4c; color:#fff; border-color:transparent}
.note{font-size:.82rem; color:var(--ink-soft); margin:6px 0 12px}

/* lägg till på hemskärmen */
.install{margin-top:14px; display:inline-flex; gap:8px; align-items:center; background:var(--sun); color:#fff;
  border:none; border-radius:999px; padding:10px 17px; font-weight:800; font-size:.9rem; cursor:pointer;
  font-family:inherit; box-shadow:var(--shadow)}
.install:active{transform:scale(.97)}
.sheet{position:fixed; inset:0; z-index:20; background:rgba(10,20,30,.5);
  display:flex; align-items:flex-end; justify-content:center}
.sheet[hidden]{display:none}
.sheet-card{position:relative; background:var(--paper); color:var(--ink); width:100%; max-width:480px;
  border-radius:20px 20px 0 0; padding:22px 20px calc(22px + env(safe-area-inset-bottom));
  box-shadow:0 -12px 44px rgba(0,0,0,.32); animation:up .26s}
@keyframes up{from{transform:translateY(101%)}to{transform:none}}
.sheet-card h3{margin:0 0 12px; font-family:"Anton",sans-serif; text-transform:uppercase; letter-spacing:.03em; font-weight:400}
.sheet-x{position:absolute; top:14px; right:14px; border:none; background:var(--sand); color:var(--ink);
  width:34px; height:34px; border-radius:50%; font-size:1rem; cursor:pointer}
.step{display:flex; gap:11px; align-items:flex-start; margin:11px 0; font-size:.96rem; line-height:1.45}
.step .n{flex:0 0 auto; width:24px; height:24px; border-radius:50%; background:var(--ink); color:#fff;
  font-weight:800; font-size:.8rem; display:flex; align-items:center; justify-content:center}
.step b{color:var(--sun)}
.shareicon{display:inline-block; transform:translateY(2px)}
footer{margin-top:26px; font-size:.78rem; color:var(--ink-soft); text-align:center; line-height:1.7}
footer a{color:var(--sea)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">Åhus Beach Handboll 2026</div>
    <h1>Alingsås&nbsp;HK<br><span class="em">matchschema</span></h1>
    <div class="dates">Fre 17 juli &amp; Lör 18 juli · 6 lag · <span id="count"></span> matcher</div>
    <button id="install" class="install" hidden>📲 Lägg till på hemskärmen</button>
    <div class="sea-rule"></div>
  </header>

  <nav class="filters" id="filters" aria-label="Filtrera lag"></nav>

  <section id="hero"></section>
  <main id="list"></main>

  <details class="cal">
    <summary>Lägg till i din kalender (valfritt)</summary>
    <p class="note">För dig som hellre vill ha matcherna i din kalenderapp. <strong>Prenumerera på länken</strong>
      – importera inte filen (då uppdateras den inte). På Android/Outlook görs det via outlook.com i webbläsare;
      på iPhone via Inställningar → Kalender → Lägg till prenumererad kalender.</p>
    <ul>
__CAL_ITEMS__
    </ul>
  </details>

  <div id="sheet" class="sheet" hidden>
    <div class="sheet-card">
      <button class="sheet-x" id="sheetx" aria-label="Stäng">✕</button>
      <h3>Lägg till på hemskärmen</h3>
      <div id="sheetbody"></div>
    </div>
  </div>

  <footer>
    Live-schema · uppdateras automatiskt · senast: __UPDATED__<br>
    Källa: <a href="https://ahusbeachhandboll.cupmanager.net/2026,sv/result/" target="_blank" rel="noopener">cupmanager.net</a>
    · Matchtid 2×5 min + 60 s paus · Tider kan ändras av arrangören<br>
    <span style="opacity:.8">Tips: lägg till sidan på hemskärmen för snabb åtkomst på plats.</span>
  </footer>
</div>

<script>
const MATCHES = __DATA__;
const TEAMS = __TEAMS__;
const DUR = __DUR_MIN__ * 60000;
let filter = "all";

const $ = s => document.querySelector(s);
document.getElementById("count").textContent = MATCHES.length;

// bygg filterpiller
const fwrap = document.getElementById("filters");
function pill(id, label, color, sun){
  const b = document.createElement("button");
  b.className = "pill" + (sun ? " sun" : "");
  b.setAttribute("aria-pressed", id === filter);
  b.dataset.id = id;
  b.innerHTML = (color ? `<span class="d" style="background:${color}"></span>` : "") + label;
  b.onclick = () => { filter = id; render(); for(const p of fwrap.children) p.setAttribute("aria-pressed", p.dataset.id===id); };
  return b;
}
fwrap.appendChild(pill("all","Alla",null,true));
fwrap.appendChild(pill("P15","Pojkar 15",null,false));
fwrap.appendChild(pill("F15","Flickor 15",null,false));
TEAMS.forEach(t => fwrap.appendChild(pill(t.slug, t.lag, "#"+t.color, false)));

function matchPass(m){
  if(filter==="all") return true;
  if(filter==="P15"||filter==="F15") return m.klass===filter;
  return m.slug===filter;
}
function state(m, now){
  if(now >= m.ms && now < m.ms+DUR) return "live";
  if(m.ms > now) return "up";
  return "past";
}
function esc(s){ return (s+"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function fmtCountdown(ms){
  if(ms<=0) return "";
  const min=Math.floor(ms/60000), d=Math.floor(min/1440), h=Math.floor((min%1440)/60), mi=min%60;
  if(d>0) return `om ${d} d ${h} tim`;
  if(h>0) return `om ${h} tim ${mi} min`;
  return `om ${mi} min`;
}

function render(){
  const now = Date.now();
  const rows = MATCHES.filter(matchPass).sort((a,b)=>a.ms-b.ms);
  // hero: pågående annars nästa
  const live = rows.find(m=>state(m,now)==="live");
  const next = rows.find(m=>state(m,now)==="up");
  const hero = $("#hero");
  const hm = live || next;
  if(hm){
    const isLive = !!live;
    hero.innerHTML =
      `<div class="hero ${isLive?"live":""}">
        <div class="tag">Bana ${esc(hm.bana)}</div>
        <div class="lbl">${isLive?'<span class="pulse"></span>Pågår nu':"Härnäst"}</div>
        <div class="mt">${esc(hm.home)} <span style="opacity:.7">vs</span> ${esc(hm.away)}</div>
        <div class="sub">${esc(hm.lag)} · ${esc(hm.grp)} · ${hm.t} · ${esc(hm.day)}</div>
        <div class="cd" data-ms="${hm.ms}">${isLive?"Spelas nu":fmtCountdown(hm.ms-now)}</div>
      </div>`;
  } else {
    hero.innerHTML = rows.length
      ? `<div class="hero"><div class="lbl">Klart</div><div class="mt">Alla matcher spelade</div></div>` : "";
  }
  // lista grupperad per dag
  const list = $("#list");
  if(!rows.length){ list.innerHTML = '<div class="empty">Inga matcher för det här filtret.</div>'; return; }
  let html = "", curDay = null;
  for(const m of rows){
    if(m.day !== curDay){ curDay = m.day; html += `<div class="day">${esc(m.day)}</div>`; }
    const st = state(m, now);
    const homeAli = m.hb==="Hemma";
    html +=
      `<article class="match ${st}" style="--c:#${m.color}">
        <div class="t">${m.t}${st==="live"?'<small class="nowtag">NU</small>':""}</div>
        <div>
          <div class="chips"><span class="lagchip" style="background:#${m.color}">${esc(m.lag)}</span>
            <span class="grp">${esc(m.grp)}</span></div>
          <div class="vs"><span class="${homeAli?"ali":""}">${esc(m.home)}</span> – <span class="${homeAli?"":"ali"}">${esc(m.away)}</span></div>
        </div>
        <div class="bana"><small>BANA</small><b>${esc(m.bana)}</b></div>
      </article>`;
  }
  list.innerHTML = html;
  // scrolla till nu/härnäst om turneringen pågår (det finns spelade matcher)
  if(!render._scrolled && rows.some(m=>state(m,now)==="past") && hm){
    render._scrolled = true;
    setTimeout(()=>{ const el=document.querySelector(".match.live")||document.querySelector(".match.up"); }, 50);
  }
}

// nedräkning varje sekund, full omritning ibland
setInterval(()=>{ const cd=document.querySelector(".hero .cd"); if(cd&&cd.dataset.ms){
  const left=+cd.dataset.ms-Date.now(); cd.textContent = left>0?fmtCountdown(left):"Spelas nu"; }}, 1000);
setInterval(render, 30000);
render();

// kopiera-knappar
document.addEventListener("click", async e=>{
  const b = e.target.closest(".copy"); if(!b) return;
  try{ await navigator.clipboard.writeText(b.dataset.url); }catch(_){}
  const o=b.textContent; b.textContent="✓ Kopierad!"; b.classList.add("ok");
  setTimeout(()=>{ b.textContent=o; b.classList.remove("ok"); }, 1600);
});

// ---- Lägg till på hemskärmen (Android-prompt + iOS/övrigt-instruktioner) ----
if("serviceWorker" in navigator){ navigator.serviceWorker.register("sw.js").catch(()=>{}); }
const installBtn = document.getElementById("install");
const sheet = document.getElementById("sheet");
const sheetBody = document.getElementById("sheetbody");
let deferredPrompt = null;
const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
const ua = navigator.userAgent || "";
const isIOS = /iphone|ipad|ipod/i.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
const isAndroid = /android/i.test(ua);

window.addEventListener("beforeinstallprompt", e=>{ e.preventDefault(); deferredPrompt = e; });
if(!standalone){ installBtn.hidden = false; }

function step(n, html){ return `<div class="step"><span class="n">${n}</span><div>${html}</div></div>`; }
function showSheet(){
  let body;
  if(isIOS){
    body = step(1, 'Öppna sidan i <b>Safari</b> (inte Chrome/Edge).')
         + step(2, 'Tryck på <b>Dela</b>-ikonen <span class="shareicon">⎙</span> längst ned (rutan med en pil uppåt).')
         + step(3, 'Välj <b>Lägg till på hemskärmen</b> och tryck <b>Lägg till</b>.');
  } else if(isAndroid){
    body = step(1, 'Tryck på <b>⋮</b>-menyn uppe till höger i webbläsaren.')
         + step(2, 'Välj <b>Lägg till på startskärmen</b> (eller <b>Installera app</b>).')
         + step(3, 'Bekräfta – ikonen hamnar bland dina appar.');
  } else {
    body = step(1, 'Klicka på <b>installationsikonen</b> i adressfältet,')
         + step(2, 'eller meny → <b>Installera</b> / <b>Skapa genväg</b>.');
  }
  sheetBody.innerHTML = body;
  sheet.hidden = false;
}
installBtn.addEventListener("click", async ()=>{
  if(deferredPrompt){
    deferredPrompt.prompt();
    const r = await deferredPrompt.userChoice; deferredPrompt = null;
    if(r && r.outcome === "accepted") installBtn.hidden = true;
    return;
  }
  showSheet();
});
document.getElementById("sheetx").addEventListener("click", ()=> sheet.hidden = true);
sheet.addEventListener("click", e=>{ if(e.target === sheet) sheet.hidden = true; });
window.addEventListener("appinstalled", ()=>{ installBtn.hidden = true; sheet.hidden = true; });
</script>
</body>
</html>
"""

MANIFEST = {
    "name": "Alingsås HK · Åhus Beach 2026",
    "short_name": "Alingsås Åhus",
    "description": "Matchschema för Alingsås HK på Åhus Beach Handboll 2026",
    "start_url": ".",
    "display": "standalone",
    "background_color": "#f4ecdb",
    "theme_color": "#13293d",
    "scope": "./",
    "icons": [
        {"src": "favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
        {"src": "favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
    ],
}

# Service worker: nätverk-först (färsk data online) med cache-fallback (offline på plats).
SERVICE_WORKER = """const C = "ahus-schema-v1";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  e.respondWith(
    fetch(req).then(res => {
      const copy = res.clone();
      caches.open(C).then(c => c.put(req, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match(req))
  );
});
"""

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#13293d"/>
<circle cx="44" cy="20" r="9" fill="#f7a23a"/>
<circle cx="28" cy="40" r="16" fill="#f4ecdb"/>
<path d="M28 24v32M14 33l28 14M42 33L14 47" stroke="#ef5a2b" stroke-width="2.4"/>
<circle cx="28" cy="40" r="16" fill="none" stroke="#13293d" stroke-width="2"/>
</svg>
"""


def js_matches(matches):
    out = []
    for m in matches:
        out.append({
            "ms": m["start_ms"], "t": m["tid"], "bana": m["bana"],
            "lag": m["lag"], "slug": m["slug"], "klass": m["klass"],
            "grp": m["grupp"], "home": m["hemma"], "away": m["borta"],
            "hb": m["hb"], "day": m["day_label"], "color": m["color"],
        })
    out.sort(key=lambda x: x["ms"])
    return out


def main():
    matches, meta = sch.load_matches()
    teams_js = [{"lag": t["lag"], "slug": t["slug"], "klass": md.short_klass(t["klass"]),
                 "color": md.team_colors[t["lag"]]} for t in md.teams]
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(js_matches(matches), ensure_ascii=False))
            .replace("__TEAMS__", json.dumps(teams_js, ensure_ascii=False))
            .replace("__DUR_MIN__", str(DUR_MIN))
            .replace("__CAL_ITEMS__", cal_section())
            .replace("__UPDATED__", human_updated(meta)))
    with open(os.path.join(sch.ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(sch.ROOT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2)
    with open(os.path.join(sch.ROOT, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON)
    with open(os.path.join(sch.ROOT, "sw.js"), "w", encoding="utf-8") as f:
        f.write(SERVICE_WORKER)
    print(f"index.html ({len(matches)} matcher), manifest.json, favicon.svg, sw.js — källa: {meta.get('source')}")


if __name__ == "__main__":
    main()
