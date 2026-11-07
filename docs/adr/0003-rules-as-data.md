# 3. Validation rules stored as data

Status: accepted

## Context
Rules change every year with the CALPADS File Specifications, and reviewers who are not Python developers need to be able to read them.

## Decision
Each rule is a `Rule` record (ID, severity, record type, description, CALPADS rule it is modeled on, SQL). The loader runs each rule's SQL against the batch and writes the results to `validation_results`.

## Consequences
- To add a rule you add one record, and the readiness page lists it automatically.
- Parsing and batch-volume checks need procedural code. They are still listed in `ALL_RULES`, so the catalog stays complete.
