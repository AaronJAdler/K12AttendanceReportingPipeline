# 2. Fatal and Warning severities, with quarantine

Status: accepted

## Context
CALPADS sorts validation findings into Fatal errors, which block certification, and Warnings, which do not. District data coordinators already think in these terms.

## Decision
Use the same two severities. A Fatal finding keeps the row out of the marts. The row stays in the warehouse with its rule ID and source line number. A Warning flags the row and lets it through.

Cross-file existence rules check against every parsed record, including rows that failed other rules, so one defect produces one finding instead of a chain of them.

## Consequences
- Excluding Fatal rows makes the reported rate slightly wrong for those students until a corrected batch arrives. The readiness page shows how many rows are affected.
- All rule IDs use the `RB` prefix so nobody mistakes them for official CALPADS rules.
