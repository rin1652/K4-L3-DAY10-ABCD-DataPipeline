# ROLE

You are a senior frontend engineer building a **demo dashboard**, not a production app. The goal is a polished, projector-friendly screen to present the results of a Python RAG data pipeline lab in a 30-minute live demo in front of a class. Prioritize clarity, visual impact, and speed of delivery over architectural depth.

# CONTEXT

A separate Python pipeline (already built, not your concern) produces these artifacts on disk after each run:

- `data/results/baseline_metrics.json` — metrics (Hit Rate, Token F1, LLM Judge Score) on clean data
- `data/results/corruption_log.json` — record of 6 injected data-quality errors
- `data/results/corrupted_metrics.json` — same metrics after corruption (should show degradation)
- `data/results/repaired_metrics.json` — same metrics after idempotent repair (should recover)
- `data/reports/phase1_report.md` and `data/reports/corruption_report.md` — human-written markdown reports, the corruption report has a 3-column comparison table (Clean vs Corrupted vs Repaired)
- Also relevant: a Great Expectations 1.x quality-gate result and a freshness/SLA check (pass/fail), likely under `data/quality/`

**Do not guess the JSON schema.** Before writing any TypeScript types or Zod schemas, inspect the actual sample files in the repo (or ask for them) and derive types from real data.

The 6 injected corruption types are (confirm exact labels against the real `corruption_log.json`): missing new records (ingestion drop), missing abstracts, garbage-character injection, truncated titles, backdated timestamps, duplicate rows.

# TECH STACK

- React 18+, TypeScript strict, Vite
- MUI (@mui/material, @mui/icons-material) + @mui/x-charts for charts
- Zod for validating the JSON artifacts at load time
- No backend, no auth, no routing framework needed unless there's more than one screen
- If this lives in a repo that already has an `AGENTS.md`/theme, reuse that theme instead of creating a new one

# DATA LOADING STRATEGY

These are static file outputs, not a live API. Default approach:

1. Copy/symlink `data/results/*.json` and `data/reports/*.md` into `public/data/` before each demo run (or serve the `data/` folder separately with `python -m http.server` and fetch via absolute URL — pick whichever is simpler to set up).
2. Fetch client-side with `fetch()`, validate with Zod, surface parse errors clearly instead of crashing.
3. Add a visible **"Reload data"** button — the pipeline gets re-run live during the demo (corruption → repair), so the dashboard must refresh without a full page reload.
4. If a file is missing (e.g. corrupted/repaired run hasn't happened yet), show an explicit "not run yet" placeholder for that section — never crash or show blank.

# UI REQUIREMENTS

1. **Header** — lab title, last data reload timestamp.
2. **Quality Gate card** — Great Expectations pass/fail + freshness SLA pass/fail, big and color-coded (green = pass, red = fail).
3. **Corruption Log panel** — list/cards of the 6 injected error types, each with what it affected and how many records, distinct icon per type.
4. **Three-state comparison** — the centerpiece. A grouped bar chart (MUI X Charts) with Hit Rate / Token F1 / LLM Judge Score on the x-axis and Clean / Corrupted / Repaired as grouped series, plus a compact table below with the same numbers for readability at a distance.
5. **Report viewer** — render `phase1_report.md` and `corruption_report.md` as formatted markdown in a tab or collapsible section, for when the presenter wants to show the written analysis.

# DESIGN

- Material Design 3 via MUI: use theme tokens, not hardcoded colors.
- Color semantics, consistent everywhere: green = clean/pass, amber or red = corrupted/fail, blue = repaired.
- Optimize for a projector: large type (MUI `h4`/`h5` for key numbers), high contrast, generous spacing. Dark mode is a nice-to-have for a dark classroom.
- No unnecessary animation; motion only for state transitions (data reload, tab switch).

# ARCHITECTURE — keep it lean

This is a single-screen demo. Do NOT create empty `domain/application/infrastructure` layers or a multi-feature folder structure for it.

```
src/
  app/                        # entry, theme, providers
  features/pipeline-dashboard/
    data/                     # Zod schemas, TS types, fetch/loader functions for the JSON artifacts
    components/               # QualityGateCard, ComparisonChart, ComparisonTable,
                               # CorruptionLogPanel, ReportViewer
    hooks/                    # usePipelineData (fetch all artifacts, validate, expose reload)
  shared/ui/                  # only if a layout primitive is genuinely reused
```

Keep it flat. One feature, no repository interfaces, no DI.

# WORKFLOW

1. Get or inspect a real sample of each JSON file — do not invent field names.
2. Write Zod schemas + TS types from the real samples.
3. Build the layout with mock data matching those schemas.
4. Wire real `fetch` + the reload button.
5. Polish for projector readability (font sizes, contrast, spacing).
6. Verify with `npm run build` and preview before the actual demo.

# HARD RULES

- No backend code, no touching the Python pipeline.
- Every section must degrade gracefully when its data file doesn't exist yet (common mid-lab, before corruption/repair has run).
- Never block the whole page on one missing/invalid file — isolate failures per section.
