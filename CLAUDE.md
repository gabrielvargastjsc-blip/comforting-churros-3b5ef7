# CLAUDE.md

Guidance for AI assistants working in this repository.

## What this is

**RitmoMed** — a single-file, offline-first mobile web app (PWA-ish) for tracking a
personal medication regimen, visualizing an *illustrative* neurochemistry model
(noradrenaline / dopamine / serotonin over 24 h), managing medication stock, and
charting lab-exam history over time.

The entire application — markup, CSS, data and logic — lives in **one HTML file**:

```
ritmomed (17).html      ← the whole app (~2450 lines, ~265 KB)
```

There is nothing else in the repository: no `package.json`, no build system, no
tests, no CI, no config files. The repo was created by a Netlify import
(`Initial commit via Netlify`).

The UI, all identifiers, comments and data are in **Brazilian Portuguese
(pt-BR)**. Keep writing in pt-BR — do not translate existing strings or rename
functions/variables to English.

## Sensitive-content warning

This file contains a real person's **personal medical record**: full name, age,
diagnoses, psychiatric/hormonal medication regimen with doses, and dated lab
results (`SEED_MEDS`, `SEED_PRONT`, `SEED_EXAMS`). Treat it accordingly:

- Do not copy patient data into commit messages, PR descriptions, issue
  comments, or any external service.
- Do not publish the file content to artifacts, gists, or third-party hosts.
- Every screen carries a disclaimer that the curves are **illustrative models,
  not measured plasma levels**. If you touch any pharmacological display, keep
  those disclaimers intact.
- The bicarbonate/lisdexamfetamine regime is explicitly labelled in-app as
  hypothetical/educational, not standard practice. Do not soften that framing.

## Running and "building"

There is no build step and no dependency install.

```bash
# open it directly
xdg-open "ritmomed (17).html"        # or double-click / drag into a browser
# or serve it (needed if you want localStorage to behave like production)
python3 -m http.server 8000          # then http://localhost:8000/
```

Best viewed at a phone width — the layout is capped at `max-width:520px` and
uses `env(safe-area-inset-*)` for iOS notches.

Verification is manual: open the file, exercise the tab you changed, and check
the browser console for errors. There is no test suite to run.

**Netlify note:** the deployed filename is `ritmomed (17).html`, not
`index.html`, so it is not served at the site root. If a task involves the
deployment URL, confirm with the user before renaming the file — the name is
load-bearing for existing links.

## File layout

Line numbers drift as the file is edited; use them as a map, not as anchors.
Prefer searching for the banner comments (`/* ===== SECTION ===== */`).

| Lines | Contents |
|---|---|
| 1–12 | `<head>`: meta, inline data-URI icon + data-URI web app manifest |
| 13–254 | Base `<style>` — CSS custom properties, light/dark themes, component CSS |
| 256–277 | `<body>` skeleton: `#app` (header / `main#view` / `nav.tabs`), `#scrim`, `#sheet`, `#expand` |
| 278– | `<script>` — everything below |
| ~287 | `Store` — localStorage wrapper with in-memory fallback |
| ~304–435 | `SEED_MEDS`, `SEED_PRONT`, `SEED_EXAMS` — seed data |
| ~438–500 | Neurotransmitter constants, testosterone cycle model, `State`, `save()` |
| ~502–590 | Date helpers, dose scheduling, Bateman PK, circadian baseline, stock math |
| ~589–653 | Main neurochemistry SVG chart (`neuroBaseSVG` / `neuroCursorSVG`) |
| 654–997 | **Pré-despertar** and **Sem pré-despertar** tabs (pre-awakening dosing scenarios) |
| 998–1529 | **Bicarbonato + Lisdex** tab: urinary-pH / renal-clearance simulation |
| 1530–1561 | Chrome: header titles, tab bar, icons |
| 1562–1643 | **Cronograma** (home) tab |
| 1644–1724 | **Estoque** and **Prontuário** and **Farmacologia** tabs |
| 1725–1734 | Helpers (`esc`, `fmtNum`, `fmtDM…`) and bottom-sheet modal |
| 1735–2002 | **Exames** tab: series charts, testosterone meter, PDF import |
| 2003–2170 | Settings sheet, `injectCSS()` |
| 2171–2426 | Expanded neurochemistry view (dopamine trough, onset, peak, propranolol, clonidine) |
| 2427–2451 | Router (`rerender`), global listeners, boot |

## Architecture

Vanilla ES2020, `"use strict"`, no framework, no modules, no bundler. Everything
is a top-level function or `const` in one global scope.

### State and persistence

- A single mutable global `State` object holds tab, selected date, cursor
  positions, seeded collections (`meds`, `pront`, `exams`, `attach`), and
  per-tab UI knobs.
- `Store.get/set` wraps `localStorage` with a JSON round-trip and falls back to
  an in-memory object when storage is unavailable (Safari private mode,
  `file://` sandboxes). `Store.available` drives the Settings copy.
- Keys are all `rm_`-prefixed: `rm_ver`, `rm_meds`, `rm_meds_rev`, `rm_pront`,
  `rm_taken`, `rm_variants`, `rm_exams`, `rm_attach`, `rm_symp`, `rm_theme`.
- `save()` persists the whole of `State` that is meant to be durable. Call it
  after **any** mutation the user should keep. Transient UI state (`cursorH`,
  `expSel`, `bicCursor`, `pdfBlobs`) is deliberately not saved.

**Two migration gates — read before changing seed data:**

- `STORE_VERSION` (currently `4`) — bumping it wipes *everything* back to the
  seeds, including the user's taken-dose log and attachments.
- `MEDS_REV` (currently `2`) — bumping it re-seeds **only** `rm_meds` while
  preserving taken doses, exams, attachments, variants and theme.

So: **when you change `SEED_MEDS`, bump `MEDS_REV`.** Only bump `STORE_VERSION`
when the shape of the stored data itself changes incompatibly. Both are cheap to
get wrong and destructive to the user's history.

### Rendering

- Render functions build an HTML string and assign it to
  `document.getElementById("view").innerHTML`, then call a matching `bindX()`
  to re-attach listeners. There is no diffing and no event delegation on
  `#view`, so **every render must be followed by its bind**.
- `rerender()` is the router: it redraws tabs + header, then dispatches on
  `State.tab` to one of `renderCrono | renderPreawake | renderNoPre |
  renderBicarb | renderEstoque | renderExames | renderPront | renderFarma`.
  The tab keys are also the keys of `TITLES`; adding a tab means touching
  `TITLES`, `tabIcon()`, the `order` array in `renderTabs()`, and `rerender()`.
- Charts are **SVG built as template strings**, not DOM-manipulated. Each chart
  family has a geometry constant (`NTGEO`, `PBGEO`, `EXG`, `TM`, `TI`, `BGEO`,
  and the `BW/BPL/BPR/BPT/BPB` group) plus `x()`/`y()` scale functions. Follow
  that pattern rather than introducing a charting library.
- Interactive charts are split into a **static base SVG** plus a **cursor
  overlay SVG** (`neuroBaseSVG` + `neuroCursorSVG`, `preBigBase` +
  `preBigCursor`, `bicHeroSVG` + `bicHeroCursor`). Dragging replaces only the
  overlay via `outerHTML` — keep that split so scrubbing stays cheap.
- Always run user-editable text through `esc()` when interpolating into HTML.

### CSS in two places

Component CSS is split between the static `<style>` block and **runtime
injections**: `injectCSS()` (called at boot), `injectPreCSS()` and
`injectBicCSS()` (called from their tab renderers). Newer classes tend to live
in the injected blocks. Before adding a rule, grep for the selector in both
places — duplicating a selector across the two sources is the usual cause of
"my style has no effect".

### Theming

- Three modes: `auto` (default, follows `prefers-color-scheme`), `light`,
  `dark`, stored in `rm_theme` and applied via `data-theme` on `<html>`.
- Colors are CSS custom properties; **JS reads them back** with
  `cssVar()` / `ntColor()` to paint SVG. Because SVG strings capture the
  resolved color at build time, a theme change requires a full `rerender()` —
  which is why the `matchMedia` listener at the bottom of the file re-renders on
  system-theme change. Any new chart must get its colors from `cssVar()`, never
  from hard-coded hex (the handful of hard-coded hormonal golds like `#C2872E`
  are the existing exception).

### The one external dependency

`pdf.js` 3.11.174 is lazily loaded from cdnjs by `ensurePdfJs()`, only when the
user imports a lab-report PDF in the Exames tab. Everything else works fully
offline. Import parsing is best-effort regex matching (`PATT`) tuned to one
lab's report format (Damiani Koerich) with a manual-entry fallback
(`openManualAdd`). Don't assume it generalizes.

## Domain model

### Medications (`SEED_MEDS`)

Each entry has `id`, `cat` (`psiq` | `horm` | `prn`), and `cadence`:

- `daily` — a `doses[]` array. Each dose is positioned either by `abs`
  (absolute minutes from midnight, e.g. `1320` = 22:00) or by `off` (minutes
  *after the user's chosen start-of-day*), and gated by `days`
  (`all` | `week` | `weekend`). `dosesForDay(date)` resolves this.
- `everyN` — fixed interval via `intervalDays` + `anchorDate`; due-dates come
  from `isDueOn` / `nextDue` / `lastDue`.
- `prn` — as-needed rescue meds; excluded from stock alerts and from the
  schedule.

Optional `efeitos: [{nt, mag, ka, ke}]` feeds the neurochemistry curves —
`nt` is one of `NA`, `DA`, `5HT`; `ka`/`ke` are per-hour absorption/elimination
constants calibrated to documented Tmax values. A med without `efeitos` simply
does not appear in the curves.

`variantIndex` / `VARIANTS` model the "start of medication" time (06:00–11:00 in
30-min steps, default 07:00), stored per-date in `rm_variants`. Shifting it
shifts every `off`-based dose and every downstream curve.

### Pharmacokinetics

- `bateman(tH, t0H, mag, ka, ke)` — one-compartment Bateman function normalized
  so its peak equals `mag`. This is the primitive everything else builds on.
- `ntLevel()` — single-day, single-dose view used by the "Níveis" bars.
- `ntMedSS()` / `ntProj()` — the chart projection: sums `PROJ_KDAYS` (14) days
  of carry-over for steady state and adds a **periodic circadian baseline**
  (`circBase`, shaped by `NTCIRC`). The two models use different y-scales and
  thresholds on purpose: `Y_MAX` / `NA_RISCO_LIMIAR` for single-dose, `Y_MAX_PROJ`
  / `NA_RISCO_PROJ` for the projection. Don't mix them up.
- Testosterone: `tBatemanRaw` / `tCycleSum` / `testoEstimate` / `testoStstAt`
  model cipionate accumulation at steady state, calibrated so the modelled peak
  matches the patient's measured 989 ng/dL at 0.75 ml.
- Bicarbonate tab: a genuinely different model — a small compartmental ODE
  (`bicSim`, forward Euler at `dt=0.025 h`) coupling gut → lymph → plasma with a
  urinary-pH-dependent renal clearance (`bicCLr`, sigmoid in pH). Constants live
  in the `BIC` object; regimens in `BIC_REGS`. `bicEffContrib` /
  `plateauBandDA` are the bridge that feeds this back into the main
  neurochemistry chart for meds flagged `bicModel:true`.

### Exams (`SEED_EXAMS`)

`{id, nome, un, cat, lo, hi, pts:[[isoDate, value], …]}`. `lo`/`hi` may be
`null` for one-sided reference ranges — the chart code checks for that. `pts`
must stay sorted ascending by date; `pushPoint` maintains this.

## Conventions

- **Compact style.** Most functions are one to three dense lines, semicolon-
  separated, with tight spacing. Match the surrounding density rather than
  reformatting to a conventional style — a prettier pass would produce a
  useless diff over the whole file.
- Section banners `/* ==== NAME ==== */` separate the major areas; keep new code
  inside the right section and add a banner if you open a new area.
- Naming: pt-BR domain words (`dose`, `estoque`, `prontuário`, `exame`,
  `neuroquímica`), English for generic plumbing (`render*`, `bind*`, `open*`,
  `fmt*`).
- Numbers are formatted for pt-BR (`fmtNum` uses `toLocaleString("pt-BR")`,
  decimal comma); dates are stored as `YYYY-MM-DD` strings (`ymd`/`parseYmd`)
  and displayed as `dd/mm`.
- Everything is wrapped defensively — `try/catch` around storage, `matchMedia`,
  and PDF handling — because the app is expected to run from `file://`, inside
  in-app browsers, and as an iOS home-screen app. Preserve that tolerance.
- `@media (prefers-reduced-motion: reduce)` disables all transitions; don't add
  animation that bypasses it.

## Common gotchas

1. Editing `SEED_MEDS` without bumping `MEDS_REV` — returning users keep the old
   regimen and your change appears to do nothing.
2. Bumping `STORE_VERSION` casually — silently destroys the user's dose history.
3. Rendering without calling the matching `bind*()` — the screen looks right and
   nothing responds to taps.
4. Hard-coding chart colors — breaks dark mode, since SVG is generated once with
   resolved values.
5. Adding CSS to `<style>` when the same selector already exists in
   `injectCSS()` (or vice versa) — the injected one wins.
6. Assuming `localStorage` works — always go through `Store`.
7. Forgetting `esc()` on prontuário/exam text that the user can type.

## Git workflow

- Default branch: `main`. Feature work goes on the branch named by the task
  (e.g. `claude/claude-md-documentation-oaizai`); push with
  `git push -u origin <branch>`.
- Because the app is one file, every change is a diff in `ritmomed (17).html` —
  keep commits scoped to one concern so the diff stays reviewable, and quote the
  filename (it contains a space and parentheses) in shell commands.
- Do not open a pull request unless explicitly asked.
