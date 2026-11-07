# 5. Small-cell and complementary suppression

Status: accepted

## Context
CDE suppresses any cell with 10 or fewer eligible students. It also suppresses race "Not reported" whenever another race group is suppressed. Within one dimension the categories add up to the total, so a single hidden cell can be worked out by subtraction.

## Decision
Apply both CDE rules. Also apply complementary suppression: if exactly one cell in a dimension is hidden, hide the next-smallest one as well. Suppression runs in Python at publish time, so the marts keep exact counts.

## Consequences
- Some school pages hide more than CDE's published rule requires. CDE's page does not describe complementary suppression; it is this project's own choice.
- Property-based tests check that no published cell has 10 or fewer students and that no dimension has exactly one hidden cell.
