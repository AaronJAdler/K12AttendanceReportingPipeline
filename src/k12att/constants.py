"""Definitions taken from CDE, kept in one place so a change is one edit.

Source for the absenteeism and suppression rules: CDE "File Structure for Chronic
Absenteeism Data", https://www.cde.ca.gov/Ds/ad/fsabd.asp (read 2026-11-07).
"""

from typing import Final

# A student is chronically absent when absent on 10% or more of expected days.
CHRONIC_THRESHOLD: Final = 0.10
# A student is eligible only when expected to attend at least 31 days at the entity.
MIN_EXPECTED_DAYS: Final = 31
# Cells whose eligible enrollment is 10 or fewer are published as "*".
SUPPRESSION_MAX: Final = 10
SUPPRESSED: Final = "*"

# Assumption, not verified against the CALPADS File Specifications: submission files
# are caret-delimited text with no header row.
DELIMITER: Final = "^"

ACADEMIC_YEAR: Final = "2025-2026"
DISTRICT_CODE: Final = "99999"  # fictional
DISTRICT_NAME: Final = "Riverbend Unified (fictional)"
SCHOOL_DAYS: Final = 180

# CDE grade-span reporting categories (2021-22 onward).
GRADE_SPANS: Final[dict[str, tuple[str, ...]]] = {
    "GRTKKN": ("TK", "KN"),
    "GR13": ("01", "02", "03"),
    "GR46": ("04", "05", "06"),
    "GR78": ("07", "08"),
    "GR912": ("09", "10", "11", "12"),
}
VALID_GRADES: Final = frozenset(g for grades in GRADE_SPANS.values() for g in grades)


def grade_span(grade: str) -> str:
    for span, grades in GRADE_SPANS.items():
        if grade in grades:
            return span
    raise ValueError(f"unknown grade {grade!r}")
