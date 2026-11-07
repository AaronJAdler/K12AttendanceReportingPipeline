# K12 Attendance Reporting Pipeline

[![CI](https://github.com/AaronJAdler/K12AttendanceReportingPipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/AaronJAdler/K12AttendanceReportingPipeline/actions/workflows/ci.yml)

**Live dashboard:** https://aaronjadler.github.io/K12AttendanceReportingPipeline/

A batch pipeline that turns CALPADS-shaped enrollment and attendance files into validated chronic-absenteeism reports and an accessible static dashboard.

**All student data here is synthetic.** "Riverbend Unified" is a fictional district, and every record is generated from a fixed seed. The only real data the project uses is CDE's public chronic-absenteeism file, for comparison.

## What it shows

- **Validation the way district data teams know it.** Rules have Fatal and Warning severities, modeled on CALPADS. Three of them follow published CALPADS cross-file checks (STAS0706, SENR0718, STAS0744). A Fatal row is quarantined with its rule ID and source line number, never dropped silently.
- **Exact test oracle.** The generator writes a manifest of every defect it injects. The tests require the pipeline to find exactly those defects, no more and no fewer.
- **Bad batches don't reach the reports.** If a school's row count moves more than 20% from the last accepted batch, the whole batch is rejected. In the demo, a partial extract that lost 60% of Grove High's rows is rejected, and the reports stay on the previous batch.
- **Idempotent reloads.** Each batch loads in one transaction (delete, then insert). Loading a batch twice gives the same tables as loading it once. A corrected resubmission replaces the old rows.
- **CDE definitions.** A student is chronically absent when absent on 10% or more of expected days, and eligible only with at least 31 expected days and no exemption ([CDE file structure](https://www.cde.ca.gov/Ds/ad/fsabd.asp)). A student who changes schools is counted once at district level, with days combined.
- **Privacy.** Cells with 10 or fewer students are hidden, as CDE does. "Not reported" race is hidden whenever another race group is, also as CDE does. Complementary suppression is added so no hidden value can be worked out from the total. Student-level findings stay in `private/` and are never deployed.
- **ArcGIS map.** `map.html` plots the schools with the ArcGIS Maps SDK for JavaScript 5.1 on an OpenStreetMap basemap. Circle size shows eligible students, and color plus a label show the rate. The points are also published as `schools.geojson`, and the school locations are invented.
- **Accessibility.** Every page except the map is static HTML with no JavaScript, and the map page repeats its data in a table. Every chart has a data table beside it, and CI runs axe-core on every page.

## Run it

Windows (PowerShell), with [uv](https://docs.astral.sh/uv/) and Node 22 installed:

```powershell
git clone https://github.com/AaronJAdler/K12AttendanceReportingPipeline
cd K12AttendanceReportingPipeline
uv sync
uv run k12att demo              # generate 3 batches, load, dbt build, publish
start site\index.html           # open the dashboard
uv run pytest                   # 26 tests, about 11 s

# Accessibility check (one-time setup for the browser)
npm ci
uv run playwright install chromium
uv run python scripts/check_a11y.py site
```

To compare with real CDE data, download a chronic-absenteeism TXT file from [CDE](https://www.cde.ca.gov/Ds/ad/filesabd.asp) and run `uv run k12att calibrate path\to\file.txt`.

## Demo output (9,000 generated students, seed 42)

| Batch | Simulates | Result |
| --- | --- | --- |
| 2026-06-15 | First end-of-year submission | Accepted. 232 Fatal findings from 205 injected defects (each conflicting-SINF defect flags 2 rows), 26 Warnings |
| 2026-06-22 | Corrected resubmission | Accepted, 0 Fatal, 26 Warnings. This is the reported batch |
| 2026-06-29 | Partial extract | Rejected: Grove High went from 1,364 to 545 SENR rows |

District result: 21.4% of eligible students were chronically absent (1,893 of 8,844). The generator was tuned toward placeholder rates that are not from CDE, so treat this number as a property of the fake data only.

## Verification

Each row says what ran, where it ran, and the result. Nothing is listed as passed unless it ran.

| Check | Where | Result |
| --- | --- | --- |
| pytest, 26 tests (defect recall, idempotency, rejection, rollback, suppression properties, hand-built definition cases, HTML structure, no IDs on public pages) | Local, Linux, Python 3.12.13, 2026-11-07 | 26 passed |
| dbt build: 11 models, 9 dbt tests | Local, inside `k12att demo` and pytest | All passed |
| ruff check, ruff format --check, mypy --strict | Local | Clean |
| axe-core 4.14.0 (WCAG 2.0/2.1 A and AA tags) on all 11 pages | Local, Google Chrome headless via Playwright | 0 violations locally (map page without the ArcGIS SDK, which could not load there) and in CI (SDK reachable; the map may not have finished rendering when axe ran) |
| Visual check of `index.html` | Local screenshot | Rendered as intended |
| GitHub Actions CI: lint and types, 25 tests, demo + axe-core (0 violations on 10 pages) | GitHub Actions, [run 42413724416](https://github.com/AaronJAdler/K12AttendanceReportingPipeline/actions/runs/42413724416), 2026-11-07 | All 3 jobs passed |
| GitHub Pages deploy | GitHub Actions, same run (deploy re-run after Pages was enabled) | Passed; deployed to https://aaronjadler.github.io/K12AttendanceReportingPipeline/ |
| Live site opened in a browser: overview, readiness, map (8 points drawn, popup opens) | Claude desktop app's built-in browser, 2026-11-07 | Works as intended |
| `k12att calibrate` against a real CDE file | Not yet run | Tested only on a hand-made fixture in CDE's documented layout; cde.ca.gov was not reachable from the build environment |
| Manual keyboard and screen-reader pass | Not yet done | |
| Mermaid diagram in `docs/architecture.md` | Local, mermaid-cli 11 | Rendered without errors |

## Assumptions to check

- **File format:** the files are caret-delimited (`^`) with no header row, and the field set is simplified. This was not checked against the CALPADS File Specifications. The layouts are in `src/k12att/schema.py`.
- **Grade spans and category codes** follow CDE's public file: GRTKKN, GR13, GR46, GR78, GR912; gender GM, GF, GX, GZ; race RB, RI, RA, RF, RH, RD, RP, RT, RW.
- **Generator target rates** in `generate.py` are rough placeholders.
- **No Spanish version yet.** All page text lives in `src/k12att/strings.py`, so a translation can be added there.

## Layout

```
src/k12att/   generate, load, rules, build (dbt), suppression, publish, calibrate, cli
dbt/          staging views and marts, dbt tests
tests/        pytest suite
scripts/      check_a11y.py (Playwright + axe-core)
docs/         architecture.md, adr/0001-0007
```

See [docs/architecture.md](docs/architecture.md) for the diagram, and [docs/adr](docs/adr) for the decisions.
