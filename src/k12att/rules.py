"""Validation rule catalog.

Rules are data: an ID, a severity, the record type flagged, a description and one SQL
query that returns the failing rows for a batch. Three rules are modeled on published
CALPADS validations (named in ``modeled_on``); the rest are this project's own. Every
ID uses the ``RB`` prefix so none is mistaken for an official CALPADS rule.

Cross-file rules check existence against every parsed record, including records that
fail other rules. That way each defect produces exactly one finding instead of a
cascade (an invalid grade does not also report "STAS with no enrollment").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from k12att.constants import VALID_GRADES

Severity = Literal["Fatal", "Warning"]

_GRADES_SQL = ", ".join(f"'{g}'" for g in sorted(VALID_GRADES))


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: Severity
    record_type: str
    description: str
    modeled_on: str | None
    sql: str  # returns line_no, ssid, school_code, detail; parameter $batch


RULES: Final[tuple[Rule, ...]] = (
    Rule(
        "RB-STAS-01",
        "Fatal",
        "STAS",
        "STAS record has no Primary or Short-term SENR at the same school and year",
        "CALPADS STAS0706",
        """
        select s.line_no, s.ssid, s.school_code, 'no attending enrollment at this school'
        from stas s
        where s.batch_id = $batch and not exists (
            select 1 from senr e
            where e.batch_id = s.batch_id and e.ssid = s.ssid
              and e.school_code = s.school_code and e.academic_year = s.academic_year
              and e.enrollment_status in ('10', '30'))
        """,
    ),
    Rule(
        "RB-SENR-01",
        "Fatal",
        "SENR",
        "Primary or Short-term TK-12 enrollment has no STAS record for the same school and year",
        "CALPADS SENR0718",
        f"""
        select e.line_no, e.ssid, e.school_code, 'no STAS record for this enrollment'
        from senr e
        where e.batch_id = $batch and e.enrollment_status in ('10', '30')
          and e.grade_level in ({_GRADES_SQL})
          and not exists (
            select 1 from stas s
            where s.batch_id = e.batch_id and s.ssid = e.ssid
              and s.school_code = e.school_code and s.academic_year = e.academic_year)
        """,
    ),
    Rule(
        "RB-STAS-02",
        "Warning",
        "STAS",
        "Out-of-school suspension days reported with no incident for the student in the LEA",
        "CALPADS STAS0744",
        """
        select s.line_no, s.ssid, s.school_code,
               s.days_absent_oss || ' suspension days, no SINC record'
        from stas s
        where s.batch_id = $batch and s.days_absent_oss > 0 and not exists (
            select 1 from sinc i where i.batch_id = s.batch_id and i.ssid = s.ssid)
        """,
    ),
    Rule(
        "RB-STAS-03",
        "Fatal",
        "STAS",
        "Days attended plus days absent exceed expected attendance days",
        None,
        """
        select line_no, ssid, school_code,
               (days_attended + days_absent_excused + days_absent_unexcused + days_absent_oss)
               || ' attended+absent > ' || expected_days || ' expected'
        from stas
        where batch_id = $batch
          and days_attended + days_absent_excused + days_absent_unexcused + days_absent_oss
              > expected_days
        """,
    ),
    Rule(
        "RB-SENR-02",
        "Fatal",
        "SENR",
        "Grade level is not a valid code (TK, KN, 01-12)",
        None,
        f"""
        select line_no, ssid, school_code, 'grade level ' || grade_level
        from senr where batch_id = $batch and grade_level not in ({_GRADES_SQL})
        """,
    ),
    Rule(
        "RB-SENR-03",
        "Fatal",
        "SENR",
        "Exit date precedes start date",
        None,
        """
        select line_no, ssid, school_code, 'exit ' || exit_date || ' before start ' || start_date
        from senr where batch_id = $batch and exit_date < start_date
        """,
    ),
    Rule(
        "RB-SINF-01",
        "Fatal",
        "SINF",
        "More than one SINF record for a student, with conflicting values",
        None,
        """
        select line_no, ssid, school_code, 'conflicting SINF records for this SSID'
        from sinf
        where batch_id = $batch and ssid in (
            select ssid from sinf where batch_id = $batch
            group by ssid
            having count(distinct (first_name, last_name, gender, race_ethnicity)) > 1)
        """,
    ),
)

# Rules applied outside SQL, listed here so the catalog is complete.
PARSE_RULE: Final = Rule(
    "RB-PARSE-01",
    "Fatal",
    "*",
    "Line has the wrong number of fields or a value of the wrong type",
    None,
    "",
)
BATCH_RULE: Final = Rule(
    "RB-BATCH-01",
    "Fatal",
    "SENR",
    "A school's SENR row count moved more than 20% from the last accepted batch",
    None,
    "",
)
BATCH_TOLERANCE: Final = 0.20

ALL_RULES: Final = (PARSE_RULE, *RULES, BATCH_RULE)
