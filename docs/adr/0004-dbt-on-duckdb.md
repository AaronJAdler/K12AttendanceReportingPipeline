# 4. dbt on DuckDB for the marts

Status: accepted

## Context
Many agency data teams use SQL views or dbt. Project 1 already shows marts written in plain SQL.

## Decision
Build the marts with dbt-core and dbt-duckdb, and run dbt tests in `dbt build`. The Python runner passes the CDE definitions (10% threshold, 31-day minimum) from `constants.py` to dbt as vars, so they are defined in one place.

## Consequences
- dbt adds about 6 seconds and a large dependency tree.
- dbt keeps its DuckDB connection open in the same process, so later connections must use the same mode (not `read_only`).
