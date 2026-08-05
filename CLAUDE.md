# CLAUDE.md

Guidance for AI assistants working in this repository.

## What this is

**RitmoMed** — a single-file, offline-first PWA (in Portuguese, `pt-BR`) that tracks a
psychiatric/hormonal medication regimen and renders **illustrative** pharmacokinetic models of the
resulting neurotransmitter curves, testosterone cycle, lab-exam history, and a urinary-pH /
sodium-bicarbonate model for lisdexamfetamine retention.

The entire application is one file:

```
ritmomed (17).html      # ~2450 lines: HTML + <style> + <script>, no build step
```

There is no `package.json`, no bundler, no test suite, no CI, and no dependency manifest. The repo
was created by a Netlify import (`Initial commit via Netlify [skip ci]`) and is deployed by serving
that HTML file statically.

### Critical context before editing

- **The file name contains a space and parentheses.** Always quote it in shell commands:
  `sed -n '1,50p' "ritmomed (17).html"`. Do not rename it without being asked — the deploy points
  at this path.
- **All code comments, UI strings, and identifiers-in-prose are Portuguese.** Match that. New user
  strings, callouts, headers and comments must be written in pt-BR.
- **The seed data is real personal health information** (patient name, diagnoses, lab results,
  prescriptions). Do not copy it into commit messages, PR bodies, issue comments, or any external
  service. Keep it inside the file.
- **Everything is an illustrative model, never a measurement.** The code says so in several places
  (`disclaimer`, `bintro`, settings sheet). Preserve those disclaimers when refactoring, and keep
  new modelling clearly labelled as hypothetical.

## Running and verifying

There is nothing to install or build.

```bash
# open directly
xdg-open "ritmomed (17).html"

# or serve (needed if you want the PWA manifest / service-worker-ish behaviour to look right)
python3 -m http.server 8000    # then http://localhost:8000/ritmomed%20(17).html
```

Verification is manual, in a browser:

1. Load the page, check the console is clean.
2. Walk the eight tabs (`Hoje`, `Despertar`, `Sem pré`, `Bicarb`, `Estoque`, `Exames`, `Ficha`,
   `Farmácia`) — every tab re-renders `#view` from scratch, so a syntax error in one render function
   shows up as a blank tab.
3. Toggle theme in Ajustes (gear icon) → Automático / Claro / Escuro. SVG colours are read from CSS
   variables at build time, so a theme switch must trigger a full `rerender()`.
4. Resize to a narrow viewport — the app is phone-first (`#app` is capped at `520px`).

The only network dependency at runtime is **pdf.js from cdnjs** (`ensurePdfJs()`, line ~1938), loaded
lazily and only when the user attaches a lab PDF in the Exames tab. Everything else works offline.

## Architecture

The script is one IIFE-free top-level module in `"use strict"`, organised by banner comments
(`/* ====== SECTION ====== */`). Rough map:

| Lines | Section |
| --- | --- |
| 14–254 | `<style>` — design tokens, light/dark themes, base component CSS |
| 256–276 | DOM skeleton: `#app` → `header.hdr`, `main#view`, `nav.tabs`, plus `#scrim`/`#sheet`/`#expand` overlays |
| 288–296 | `Store` — localStorage wrapper with in-memory fallback |
| 304–394 | `SEED_MEDS` — the regimen (the single source of truth for doses, stock, mechanisms) |
| 389–394 | `SEED_PRONT` — patient record |
| 400–436 | `SEED_EXAMS` — lab time series |
| 439–460 | Neurotransmitter constants + testosterone (cypionate) steady-state model |
| 463–500 | `STORE_VERSION` / `MEDS_REV` migrations, `State`, `save()` |
| 503–583 | Date helpers, dose expansion, cycle (`everyN`) helpers, stock/consumption maths |
| 589–652 | Inline hero neuro chart SVG |
| 654–996 | **Pré-despertar** and **Sem pré-despertar** tabs (pre-awakening stimulant dosing scenarios) |
| 998–1495 | **Bicarbonato + Lisdex** tab: pH ↔ renal clearance ↔ dexamphetamine PK model + its charts |
| 1497–1528 | Bridge: the bicarbonate plasma model feeds DA/NA effect units on the main chart |
| 1530–1560 | Chrome: titles, tab bar, icons |
| 1562–1643 | **Cronograma** (`Hoje`) tab |
| 1644–1724 | Estoque, Prontuário, Farmacologia tabs |
| 1726–1733 | `esc()`, number/date formatters, bottom-sheet helpers |
| 1736–2001 | Exames tab: charts, testosterone meter, PDF import + regex lab parser |
| 2004–2018 | Settings sheet (theme, storage status, restore seed data) |
| 2021–2169 | `injectCSS()` — styles for classes added after the initial `<style>` block |
| 2172–2425 | Expanded neurochemistry overlay: vale/onset/peak markers, propranolol & clonidine models |
| 2428–2451 | Router (`rerender()`), tab click delegation, 30 s clock refresh, boot |

### State and persistence

`State` is a plain mutable object. Persisted slices are read through `Store.get` at boot and written
by a single `save()`; ephemeral UI state (cursors, selected tab, dose sliders) lives on `State` but is
not persisted.

localStorage keys, all prefixed `rm_`: `rm_ver`, `rm_meds`, `rm_meds_rev`, `rm_pront`, `rm_taken`,
`rm_variants`, `rm_exams`, `rm_attach`, `rm_symp`, `rm_theme`, `rm_pdf_<attachmentId>`.

Two independent migration counters — **this is the most common way to ship a change that silently
does nothing**:

- `STORE_VERSION` (line 463) — bumping it wipes *everything* back to seed data.
- `MEDS_REV` (line 471) — bumping it re-seeds **only** `rm_meds`, preserving taken-doses, exams,
  attachments, variants and theme.

> **If you change `SEED_MEDS`, bump `MEDS_REV`.** Existing users have a stale copy of the meds array
> in localStorage and will not see the edit otherwise. Prefer `MEDS_REV` over `STORE_VERSION`; the
> latter destroys the user's history.

### Render pattern

Every tab follows the same shape and there is no framework, no virtual DOM, no reactivity:

```js
function renderX(){
  injectXCSS();                                   // idempotent, guarded by element id
  document.getElementById("view").innerHTML = `…`; // full string rebuild
  bindX();                                        // re-attach all listeners
}
```

Consequences to respect:

- **Re-binding is mandatory.** Any handler attached inside a re-rendered subtree is destroyed by the
  next `innerHTML =`. Partial refreshes (`refreshPropra`, `refreshClon`, `bindLevels`) always call
  their `bind*` again.
- Truly global handlers (the tab bar, the `.bann` info-dot delegate at line ~1428, `mouseup` for
  drag) are registered once at top level via delegation on a stable node — keep them there rather
  than re-registering inside a render.
- CSS is added by three injectors that append a `<style>` tag. `injectCSS()` (`#rm-inject`) is called
  exactly once at boot and is **not** guarded; `injectPreCSS()` (`#pre-css`) and `injectBicCSS()`
  (`#bic-css`) are called from their render functions and early-return if their tag already exists.
  New styles for new classes go in the matching injector, not in the top `<style>` block (which holds
  the base design system).
- **Always run user/seed strings through `esc()`** when interpolating into a template literal.

### Charts

All charts are SVG built as strings, never with DOM APIs. Each chart family has its own geometry
constant and `x`/`y` projection pair, e.g.:

- Main neuro chart: `NTGEO` + `ntX()` / `ntY()`; expanded version `BGEO` + `bX()` / `bY()` / `bYP()`.
- Pre-awakening: `PGEO` (inline) and `PBGEO` (expanded) + `pXg()` / `pYg()`.
- Bicarbonate: `BW`/`BPL`/`BPR`/`BPT`/`BPB` + `bicTX()` / `bicPX()` / `bicYV()`.
- Exams: `EXG`; testosterone meter `TM`; interval comparison `TI`.

Two conventions:

1. **Base layer + cursor overlay.** Expensive base paths render once (`neuroBaseSVG`, `preBigBase`,
   `bicHeroSVG`); a second absolutely-positioned SVG (`neuroCursorSVG`, `preBigCursor`,
   `bicHeroCursor`) is swapped via `outerHTML` on every pointer move so dragging stays cheap. Keep
   that split when adding interactive charts.
2. **Colours come from `cssVar('--token')`** through `ntColor()` / `medColor()` / `hexToRgba()`, read
   at string-build time. Never hardcode a hex that must adapt to the theme, and remember that a theme
   change therefore requires a re-render (already wired at line ~2446).

Clickable annotation dots on the bicarbonate tab (`bicMark`, `bicBadge`) carry `data-note="<id>"` and
resolve against `BIC_NOTES`, which stores `{h: heading, b: body, r: reference}`. Every model claim
there cites its source (FDA labels, Huang 2020, Robey & Nesbit 2013, …) or explicitly says
"valor escolhido para visualização". **Preserve that discipline** — if you add a number to a model,
add its provenance to `BIC_NOTES` or `FDA` (line ~2208).

### The dosing/time model

- The user's day does not start at midnight: `VARIANTS` (11 slots from `06:00` to `11:00`) sets the
  medication start time per date, stored in `State.variants[date]` (default index 2 → `07:00`).
  `dayStartMin(date)` is the anchor.
- A dose in `SEED_MEDS.doses[]` is either **relative** (`off:` minutes after day start — moves with
  the variant) or **absolute** (`abs:` minutes from midnight — e.g. the 22:00 night block at
  `abs:1320`). `days` is `"all" | "week" | "weekend"`.
- `dosesForDay(date)` expands only `cadence:"daily"` meds. Interval meds use `cadence:"everyN"` with
  `anchorDate` + `intervalDays` and are surfaced by `isDueOn` / `nextDue` / `hormDueOn`. `cadence:"prn"`
  meds never appear on the schedule.
- Dose keys are `` `${med.id}#${doseIndex}` `` and taken-state lives in `State.taken[date][key]`.
  Toggling a dose also decrements/restores `med.estoque` (or `estoqueMl` for `trackMl` meds), so
  stock and schedule are coupled — see `toggleDose` (line ~1641).

### Pharmacokinetic models

Everything is a normalised Bateman (one-compartment, first-order absorption + elimination) function
of hours, with `ka`/`ke` per hour:

- `bateman(tH, t0H, mag, ka, ke)` — the shared kernel; per-medication `ka/ke/mag` live in
  `SEED_MEDS[].efeitos[]`.
- `ntLevel(date, nt, tH)` — single-day sum; `ntMedSS` + `circBase` → `ntProj` add multi-day carryover
  (`PROJ_KDAYS = 14`) on top of a periodic circadian baseline (`NTCIRC`) for the projected chart.
- `bicSim()` numerically integrates lisdexamfetamine → dexamphetamine with `ke` varying by urinary
  pH, where pH is driven by bicarbonate surges (`bicPH`, `bicSurge`) and clearance follows a sigmoid
  `bicCLr(pH)`.
- `bicEffContrib()` (line ~1520) converts that plasma curve back into the DA/NA "effect units" of the
  main chart, calibrated so 70 mg without bicarbonate reproduces the historical peak (DA 1.00 /
  NA 0.90). Curves are memoised in `_bicCurveCache`. If you change the calibration constants, both
  the Bicarb tab *and* the Cronograma hero chart move.
- Testosterone: `testoEstimate` (fixed 5-day schedule) and `testoStstAt(I, t, ml)` (arbitrary
  interval), calibrated to the patient's measured 989 ng/dL peak at 0.75 ml.

Empirical corrections: `State.sympLog.{onset,peak}` stores user-reported offsets and `effOffset()`
takes the **median** of prediction + logs, so the markers drift toward observed reality.

### Lab PDF import

`bindExames` → file input `#pdf-in` → `ensurePdfJs()` → text extraction → `parseLabText()`, which
scans the `PATT` table (line ~1944) of `[examId, regex]` pairs and `collectDates()` for
"Data de Coleta" stamps, attributing each value to the nearest preceding collection date. Values are
parsed with `brNum()` (Brazilian `1.234,56` format). Parsed points go through `pushPoint()`, which
de-duplicates by date. The raw PDF is kept base64 in `State.pdfBlobs` and persisted only if under
~3.5 MB. To support a new analyte: add it to `SEED_EXAMS`, add a `PATT` entry, bump `STORE_VERSION`
only if existing users must get the new series.

## Conventions

- **Formatting:** dense, compact style — many one-line functions, `;`-terminated, 2-space indent
  inside blocks, no semicolon-less lines. Match the surrounding density rather than reformatting.
- **Naming:** camelCase functions, `SCREAMING_CASE` module constants, `_leadingUnderscore` for
  module-private mutable caches/drag flags (`_preDrag`, `_bicCurveCache`, `_expDrag`).
- **Numbers in UI:** always pt-BR — `fmtNum()` for values (comma decimal separator), `fmtDM()` /
  `fmtDMY()` for dates, `hhmm()` for clock times, and the `.mono` class with tabular numerals for
  anything that should not jitter.
- **Dates** are `YYYY-MM-DD` strings everywhere (`ymd()` / `parseYmd()`), constructed in local time.
  Never use `new Date(string)` for these — it would parse as UTC and shift the day.
- **Defensive coding:** storage, `matchMedia`, `scrollTo` and PDF decoding are all wrapped in
  `try/catch` because the app is expected to run in restricted webviews and preview iframes. Keep new
  platform-touching code equally defensive.

## Git workflow

- Development branch for the current task: `claude/claude-md-documentation-ryayiq`. Commit and push
  there; do not push to `main`.
- Do not open a pull request unless explicitly asked.
- Since there is no test suite, describe manual verification steps in the commit message when the
  change is behavioural.
