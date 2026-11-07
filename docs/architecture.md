# Architecture

A batch pipeline in five layers. One command (`k12att demo`) runs all of them locally; CI
runs the same command and deploys the dashboard to GitHub Pages.

```mermaid
flowchart LR
    G["generate.py<br/>seeded synthetic files<br/>+ defect manifest"] --> R["raw/&lt;batch&gt;/<br/>SENR SINF STAS SINC<br/>caret-delimited"]
    R --> P["load.py<br/>parse, typed insert,<br/>sha256 per file"]
    P --> V["rules.py<br/>single-file and<br/>cross-file rules"]
    V -->|Fatal| Q[("validation_results<br/>rule, line, severity")]
    V --> B{"RB-BATCH-01<br/>row counts vs<br/>last accepted batch"}
    B -->|rejected| H[("batches<br/>status, reason")]
    B -->|accepted| H
    H --> S["dbt staging<br/>newest accepted batch,<br/>Fatal lines removed"]
    Q --> S
    S --> M["dbt marts<br/>student-school-year,<br/>district, chronic,<br/>reason, Report 14.1"]
    M --> U["suppression.py<br/>n &le; 10 and<br/>complementary"]
    U --> W["site/<br/>static HTML, SVG,<br/>no JavaScript"]
    Q --> E["private/<br/>error report CSV<br/>with local IDs"]
```

## Layers

| Layer | Code | Store | Notes |
| --- | --- | --- | --- |
| Generate | `src/k12att/generate.py` | `data/raw/<batch>/` | Seeded. Writes `manifest.json` listing every injected defect. |
| Land and parse | `src/k12att/load.py` | DuckDB `raw_files`, `senr`, `sinf`, `stas`, `sinc` | One transaction per batch; delete then insert, so reloads are idempotent. |
| Validate | `src/k12att/rules.py` | DuckDB `validation_results`, `batches` | Rules are data: ID, severity, SQL. |
| Model | `dbt/models/` | DuckDB tables | Definitions passed in from `constants.py` as dbt vars. |
| Publish | `src/k12att/publish.py`, `suppression.py` | `site/`, `private/` | Only suppressed aggregates are public. |

## Demo batches

| Batch | What it simulates | Result |
| --- | --- | --- |
| 2026-06-15 | First end-of-year submission with injected defects | Accepted; Fatal rows quarantined |
| 2026-06-22 | Corrected resubmission | Accepted; becomes the reported batch |
| 2026-06-29 | Partial extract: Grove High lost 60% of its rows | Rejected by RB-BATCH-01; reports stay on 2026-06-22 |

## Decisions

See `docs/adr/`.
