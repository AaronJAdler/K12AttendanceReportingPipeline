"""Small-cell suppression for published tables.

Two rules:

1. Primary (CDE): a cell whose eligible enrollment is 10 or fewer is shown as ``*``.
   CDE also suppresses race/ethnicity "Not Reported" (RD) whenever another race group
   in the same selection is suppressed; that rule is applied too.
2. Complementary (this project's choice): the categories in one dimension (gender,
   race/ethnicity, grade span) add up to the total. If exactly one is hidden, it can be
   worked out by subtraction, so the next-smallest category is hidden as well.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace

from k12att.constants import SUPPRESSION_MAX


@dataclass(frozen=True)
class Cell:
    entity: str  # "district" or a school code
    dimension: str  # "total", "gender", "race", "grade_span"
    category: str  # CDE reporting category code
    eligible: int
    chronic: int
    suppressed: bool = False

    @property
    def rate_pct(self) -> float | None:
        return round(100.0 * self.chronic / self.eligible, 1) if self.eligible else None


def suppress(cells: list[Cell]) -> list[Cell]:
    out = [replace(c, suppressed=c.eligible <= SUPPRESSION_MAX) for c in cells]
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, c in enumerate(out):
        if c.dimension != "total":
            groups[(c.entity, c.dimension)].append(i)

    for (_, dimension), idx in groups.items():
        if dimension == "race" and any(out[i].suppressed and out[i].category != "RD" for i in idx):
            for i in idx:
                if out[i].category == "RD":
                    out[i] = replace(out[i], suppressed=True)
        hidden = [i for i in idx if out[i].suppressed]
        if len(hidden) == 1:
            visible = sorted(
                (i for i in idx if not out[i].suppressed), key=lambda i: out[i].eligible
            )
            if visible:
                out[visible[0]] = replace(out[visible[0]], suppressed=True)
    return out
