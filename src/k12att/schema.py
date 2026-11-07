"""Simplified CALPADS-shaped record layouts.

Field names follow the CALPADS File Specifications in spirit; the set is reduced to what
the reports need and the field order is this project's own. Codes for gender and
race/ethnicity use CDE's public reporting categories so the output lines up with the
CDE downloadable files.
"""

from typing import Final

LAYOUTS: Final[dict[str, tuple[str, ...]]] = {
    "SENR": (
        "record_type",
        "academic_year",
        "school_code",
        "ssid",
        "local_id",
        "grade_level",
        "enrollment_status",  # 10 = Primary, 30 = Short-term, 20 = Secondary
        "start_date",
        "exit_date",
    ),
    "SINF": (
        "record_type",
        "effective_date",
        "school_code",
        "ssid",
        "local_id",
        "first_name",
        "last_name",
        "gender",  # GM, GF, GX, GZ
        "race_ethnicity",  # RB, RI, RA, RF, RH, RD, RP, RT, RW
    ),
    "STAS": (
        "record_type",
        "academic_year",
        "school_code",
        "ssid",
        "local_id",
        "exemption_indicator",  # Y or empty
        "expected_days",
        "days_attended",
        "days_absent_excused",
        "days_absent_unexcused",
        "days_absent_oss",
    ),
    "SINC": (
        "record_type",
        "academic_year",
        "school_code",
        "incident_id",
        "ssid",
        "incident_date",
    ),
}

FILE_NAMES: Final = {rt: f"{rt}.txt" for rt in LAYOUTS}
RECORD_TYPES: Final = tuple(LAYOUTS)
INT_FIELDS: Final = frozenset(
    {
        "expected_days",
        "days_attended",
        "days_absent_excused",
        "days_absent_unexcused",
        "days_absent_oss",
    }
)
DATE_FIELDS: Final = frozenset({"start_date", "exit_date", "effective_date", "incident_date"})
ATTENDING_STATUSES: Final = frozenset({"10", "30"})
GENDERS: Final = ("GM", "GF", "GX", "GZ")
RACES: Final = ("RB", "RI", "RA", "RF", "RH", "RD", "RP", "RT", "RW")
