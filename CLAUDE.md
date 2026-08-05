# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## What this is

**RitmoMed** — a single-file, offline-first PWA (Portuguese/pt-BR) for tracking a
personal psychiatric + hormonal medication regimen. It combines:

- a daily dosing schedule with per-day start-time variants and taken/not-taken logging,
- illustrative **pharmacokinetic models** of neurotransmitter levels (NA / DA / 5-HT)
  rendered as hand-built SVG charts,
- lab-exam history with trends, PDF import, and a testosterone-cycle estimator,
- stock/inventory tracking with refill alerts,
- a patient record ("Prontuário") and a drug-reference tab ("Farmacologia").

The whole app is **one HTML file**: `ritmomed (17).html` (~2450 lines).
Note the space and parentheses in the filename — always quote it in shell commands:

```bash
wc -l "ritmomed (17).html"
```

## Repository layout

```
.
└── ritmomed (17).html    # the entire application (HTML + CSS + JS, no imports)
```

There is no `package.json`, no build step, no test suite, no linter config, and no
CI. The repo was created by a Netlify deploy ("Initial commit via Netlify"), so the
HTML file is both the source and the deployed artifact.

### File anatomy (line numbers approximate; re-grep before editing)

| Lines | Contents |
|---|---|
| 1–12 | `<head>`: PWA meta, inline data-URI manifest and apple-touch-icon, `<title>` |
| 13–254 | Base `<style>`: CSS custom properties (light + dark), layout, components |
| 256–276 | `<body>` shell: `#app`, `#hdr`, `#view`, `#tabs`, `#scrim`, `#sheet`, `#expand` |
| 278–2451 | The single `<script>` (`"use strict"`) — everything below |

Within the script, sections are separated by banner comments
(`/* ==== SECTION ==== */`). Grep for those banners to navigate:
`MEDICAÇÕES`, `EXAMES`, `PRÉ-DESPERTAR`, `BICARBONATO + LISDEX`,
`PONTE BICARBONATO -> NEUROQUÍMICA`, `CHROME`, `CRONOGRAMA`, `ESTOQUE`,
`PRONTUÁRIO`, `FARMACOLOGIA`, `HELPERS`, `SHEET`, `SETTINGS`,
`CSS INJETADO`, `VALE DOPAMINÉRGICO`, `ROTEADOR + BOOT`.

## Architecture

Data flows in one direction, and there is no framework:

```
Store (localStorage + in-memory fallback)
  ↓  seeded / version-gated
SEED_MEDS, SEED_PRONT, SEED_EXAMS
  ↓
State (single mutable global object)
  ↓  pure model functions (bateman, ntLevel, ntProj, bicSim, testoStstAt, …)
render*()   → writes innerHTML into #view / #sheet-body / #exp-body
  ↓
bind*()     → attaches event handlers to the freshly written DOM
```

`rerender()` at the bottom of the file is the router: it reads `State.tab` and
dispatches to one `render*` function. Boot is the last three statements:
`injectCSS(); applyTheme(); rerender();`

### Persistence and the version gates — read before touching seed data

`Store` wraps `localStorage` with a try/catch feature test and an in-memory
fallback (so the app still runs from `file://` or in a sandboxed preview).

Keys: `rm_ver`, `rm_meds`, `rm_meds_rev`, `rm_pront`, `rm_taken`, `rm_variants`,
`rm_exams`, `rm_attach`, `rm_symp`, `rm_theme`.

Two independent version gates run at load time:

- **`STORE_VERSION`** (currently `4`) — bumping it **resets everything**: meds,
  record, taken log, variants, exams, attachments.
- **`MEDS_REV`** (currently `2`) — bumping it re-seeds **only** `rm_meds` from
  `SEED_MEDS`, deliberately preserving taken log, exams, attachments, day
  variants, and theme.

**Consequence:** editing `SEED_MEDS` alone has *no effect* on anyone who already
has data stored — their `rm_meds` wins. If you change the regimen, you must bump
`MEDS_REV`, and that discards the user's manual stock/dose edits. Choose the
narrower gate (`MEDS_REV`) unless the exam or record schema also changed.

`save()` writes the whole state back; call it after any mutation that should
persist, then re-render.

### Data schemas

**Medication** (`SEED_MEDS` entries):

```js
{ id, cat:"psiq"|"horm"|"prn", cadence:"daily"|"everyN"|"prn",
  nome, classe, forma, dose, cor,           // cor is a CSS var() string or hex
  doses:[ {off|abs, units, days:"all"|"week"|"weekend", lbl?, mult?} ],
  estoque, estoqueCheio,                     // unit-based stock
  efeitos:[ {nt:"NA"|"DA"|"5HT", mag, ka, ke} ],   // Bateman params, per hour
  mecanismo, pico, declinio, risco, obs, quando }
```

- `off` = minutes **after the day's start time**; `abs` = absolute minutes from
  midnight (used for fixed 22:00 night doses). One or the other, not both.
- `cadence:"everyN"` uses `intervalDays` + `anchorDate` (YYYY-MM-DD) instead of
  `doses`; `trackMl`/`mlPorDose`/`estoqueMl` handle the injectable.
- `bicModel:true` routes a med's NT contribution through the bicarbonate
  pharmacokinetic model instead of plain Bateman (see `bicEffContrib`).
- Dose identity key is `` `${med.id}#${doseIndex}` `` — this is what
  `State.taken[date]` maps to booleans. Reordering a `doses` array silently
  invalidates existing taken logs.

**Exam** (`SEED_EXAMS` entries):

```js
{ id, nome, un, cat, lo, hi, pts:[[ "YYYY-MM-DD", value ], …] }
```

`lo`/`hi` may be `null` for one-sided reference ranges. `pts` are kept sorted by
date; use `pushPoint()` to insert.

### The pharmacokinetic layer

All curves are **illustrative models, not measurements** — the file says so in its
header comment and in the Settings sheet. Keep that framing in any user-facing
text you add.

- `bateman(tH, t0H, mag, ka, ke)` — normalized one-compartment absorption/
  elimination curve, peak scaled to `mag`. The workhorse.
- `ntLevel(date, nt, tH)` — same-day sum of dose contributions.
- `ntProj(date, nt, tH)` = `circBase(nt, tH)` + `ntMedSS(…)` — the chart-facing
  projection: a periodic circadian baseline (`NTCIRC`) plus a **steady-state**
  sum over `PROJ_KDAYS` (14) days of carryover, so 00:00–wake reflects yesterday's
  doses and the 24 h cycle closes.
- Bicarbonate model (`BIC`, `bicSim`, `bicPH`, `bicCLr`) — urinary-pH-dependent
  renal clearance of dexamphetamine, simulated on a fixed time grid; bridged into
  the neurochemistry charts by `bicNeuroCurve` / `bicEffContrib` with a memo cache
  (`_bicCurveCache`, `_bicRef`).
- Testosterone (`testoStstAt`, `testoEstimate`) — steady-state cypionate accumulation
  calibrated to one measured peak (0.75 ml → 989 ng/dL).
- Propranolol (`PROPRA`) and clonidine (`CLON`) are counterfactual overlays on the
  NA curve, driven by `State.propraTime/propraDose` and `State.clonTime/clonDose`.

Thresholds and axis limits are named constants near their models
(`NA_RISCO_LIMIAR`, `NA_RISCO_PROJ`, `Y_MAX`, `Y_MAX_PROJ`, `CRASH_HI`, …). Change
the constant, not the call sites.

### Charts

Every chart is a template-literal SVG string built by hand. The convention is a
geometry constant plus two mapper functions:

```js
const NTGEO = {W:720,H:300,padL:8,padR:8,padT:34,padB:26};
function ntX(h){ … }   // hours → x
function ntY(v){ … }   // level → y
```

Geometry objects in use: `NTGEO` (inline day chart), `BGEO` (expanded overlay),
`PGEO`/`PBGEO` (pre-awakening, inline/big), `EXG` (exam history), `TM`/`TI`
(testosterone meter/interval), and the `BW/BPL/BPR/BPT/BPB` set for bicarbonate.

**Base + cursor split:** interactive charts render a static base SVG once
(`neuroBaseSVG`, `preBigBase`, `bicHeroSVG`) and a separate absolutely-positioned
overlay for the draggable cursor (`neuroCursorSVG`, `preBigCursor`,
`bicHeroCursor`). Drag handlers replace **only the overlay** via `outerHTML`, never
the base. Preserve this split — re-rendering the base on every pointermove is
visibly janky on mobile.

Colors always come from CSS variables through `cssVar('--da')` / `ntColor(k)`, read
at render time so theme switches produce correct SVG fills. Never hardcode a hex in
chart code except the two hormonal accents (`#C2872E`, `#B07A1F`) that already are.

### Theming

Three-way theme (`auto` | `light` | `dark`) stored in `rm_theme`. `applyTheme()`
sets or removes `data-theme` on `<html>`; the base stylesheet defines the palette
three times — `:root`, `@media (prefers-color-scheme: dark)` scoped to
`:root:not([data-theme="light"])`, and `[data-theme="dark"]`. A change to a dark
color must be made in **both** dark blocks. A `matchMedia` listener re-renders when
the OS theme flips and the app is on `auto`.

### CSS injection

Base CSS lives in the `<style>` block. Later-added component CSS is injected at
runtime by `injectCSS()` (called at boot) and the lazy, idempotent
`injectPreCSS()` / `injectBicCSS()` (guarded by `document.getElementById(id)`,
called from their tab renderers). New styling for an existing area belongs in the
same place as its neighbors — don't move rules between the static block and the
injected ones just for tidiness.

## Conventions

- **Vanilla ES2020**, no modules, no framework, no dependencies. The only external
  resource is **pdf.js**, lazily `<script>`-injected from cdnjs by `ensurePdfJs()`
  when the user imports a lab PDF. Everything else works offline.
- **Dense one-line function bodies** are the house style for model and helper code;
  render functions are multi-line. Match the surrounding density rather than
  reformatting.
- **HTML is built with template literals** and assigned via `innerHTML`. Always run
  user/parsed data through `esc()`.
- **Render then bind.** After writing `innerHTML`, call the matching `bind*()` to
  reattach handlers — nothing is delegated except the tab bar click listener.
- **Portuguese throughout** — identifiers (`estoque`, `dosesForDay`, `renderCrono`),
  comments, and all UI copy. Keep writing in pt-BR, including numbers
  (`toLocaleString("pt-BR")`, comma decimal separator via `fmtNum`/`bicF`).
- **Dates are `YYYY-MM-DD` strings**, not `Date` objects, everywhere in state.
  Convert with `ymd()` / `parseYmd()`; arithmetic goes through `addDays()` /
  `dayDiff()`. Times are minutes-from-midnight (`hhmm()`, `timeToMin()`) in
  scheduling code and **decimal hours** in pharmacokinetic code — don't mix them.
- **Mobile-first**: `#app` is capped at 520 px, safe-area insets are respected, and
  drag handlers bind both mouse and touch events. Test at phone width.

## Tabs

`State.tab` ∈ `crono` | `preawake` | `nopre` | `bicarb` | `estoque` | `exames` |
`pront` | `farma`. Adding a tab means touching four places: the `TITLES` map, the
`tabIcon()` SVG map, the `order` array in `renderTabs()`, and the dispatch chain in
`rerender()`.

The expanded neurochemistry overlay (`#expand`) has its own sub-tabs in `ETABS`
(`vale`, `onset`, `peak`, `explorar`, `propra`, `clonidina`, `na`, `dopa`),
dispatched by `renderExpand()` with callouts from `calloutHTML()`.

## Development workflow

There is nothing to install or build.

```bash
# preview
python3 -m http.server 8000    # then open http://localhost:8000/ritmomed%20(17).html
# or just open the file directly in a browser (localStorage falls back to memory
# on some file:// configurations — Settings shows which mode is active)
```

Verification is manual. After a change, at minimum:

1. Load the page and confirm no console errors.
2. Exercise the tab you touched, in **both** light and dark themes.
3. If you touched state/persistence, reload and confirm data survives; if you
   bumped a version gate, confirm the intended data is (and isn't) reset.
4. Check chart drag/cursor behaviour on a narrow viewport.

### Git

Work on the branch designated for the session, commit with descriptive messages,
and push with `git push -u origin <branch>`. Default branch is `main`. Do not open
a pull request unless explicitly asked.

## Cautions

- **This file contains real personal health data** — a named patient, diagnoses,
  medication doses, and dated lab results. Do not copy that data into commit
  messages, PR descriptions, issue comments, or any external service. Keep it in
  the file.
- **This is not medical software.** The neurotransmitter curves, crash zones, and
  hormone estimates are illustrative models with hand-calibrated constants. The app
  states this in its header comment and Settings sheet; preserve those disclaimers
  and don't add language that implies measurement, diagnosis, or dosing advice.
- Some tabs (`bicarb`, `preawake`, `nopre`) explore explicitly hypothetical /
  educational regimens. Their copy already says so — keep it.
- The single-file constraint is intentional (installable PWA, works offline, one
  artifact to deploy). Don't split the app into modules or add a build step
  without being asked.
