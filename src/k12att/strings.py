"""All dashboard text in one place, so a translation can be added as a second dict."""

from typing import Final

EN: Final[dict[str, str]] = {
    "site_title": "Riverbend Unified attendance reporting",
    "synthetic_banner": (
        "Synthetic data. Riverbend Unified is a fictional district and every student "
        "record here was generated. No real students are included."
    ),
    "nav_overview": "District overview",
    "nav_readiness": "Certification readiness",
    "overview_heading": "Chronic absenteeism, {year}",
    "overview_lead": (
        "{rate}% of eligible students ({count} of {eligible}) were chronically absent: "
        "absent on 10% or more of the days they were expected to attend."
    ),
    "batch_note": "Reported from batch {batch}, the latest accepted submission.",
    "by_grade_span": "By grade span",
    "by_gender": "By gender",
    "by_race": "By race or ethnicity",
    "by_school": "By school",
    "by_reason": "Absence days by reason",
    "col_category": "Group",
    "col_school": "School",
    "col_eligible": "Eligible students",
    "col_chronic": "Chronically absent",
    "col_rate": "Rate (%)",
    "col_avg_days": "Average days absent",
    "col_excused": "Excused (%)",
    "col_unexcused": "Unexcused (%)",
    "col_oss": "Suspension (%)",
    "suppression_note": (
        "* Hidden to protect student privacy: the group has 10 or fewer eligible students, "
        "or hiding it is needed so another hidden value cannot be worked out from the total."
    ),
    "definition_note": (
        "Definitions follow CDE: eligible students were expected to attend at least 31 days "
        "and are not exempt; chronically absent means absent on 10% or more of expected days."
    ),
    "readiness_heading": "Certification readiness",
    "readiness_lead_ok": "Batch {batch} was accepted with {fatal} Fatal findings.",
    "readiness_lead_rejected": (
        "Batch {batch} was rejected: {reason}. Reports still use batch {current}."
    ),
    "col_batch": "Batch",
    "col_status": "Status",
    "col_fatal": "Fatal findings",
    "col_warning": "Warnings",
    "col_rule": "Rule",
    "col_severity": "Severity",
    "col_count": "Findings",
    "col_description": "What it checks",
    "history_heading": "Submission history",
    "findings_heading": "Findings in batch {batch} by school",
    "rules_heading": "Findings in batch {batch} by rule",
    "school_heading": "{school}",
    "chart_desc_prefix": (
        "Bar chart of chronic absenteeism rate by group. The same values are in the table below."
    ),
}

CATEGORY_LABELS: Final[dict[str, str]] = {
    "TA": "All students",
    "GM": "Male",
    "GF": "Female",
    "GX": "Non-binary",
    "GZ": "Missing gender",
    "RB": "African American",
    "RI": "American Indian or Alaska Native",
    "RA": "Asian",
    "RF": "Filipino",
    "RH": "Hispanic or Latino",
    "RD": "Not reported",
    "RP": "Pacific Islander",
    "RT": "Two or more races",
    "RW": "White",
    "GRTKKN": "TK and kindergarten",
    "GR13": "Grades 1-3",
    "GR46": "Grades 4-6",
    "GR78": "Grades 7-8",
    "GR912": "Grades 9-12",
}
