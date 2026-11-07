from __future__ import annotations

from pathlib import Path

from k12att.calibrate import compare, read_state_rates

HEADER = [
    "Academic Year",
    "Aggregate Level",
    "County Code",
    "District Code",
    "School Code",
    "County Name",
    "District Name",
    "School Name",
    "Charter (Y/N)",
    "DASS (Y/N)",
    "Reporting Category",
    "Chronic Absenteeism Eligible Cumulative Enrollment",
    "Chronic Absenteeism Count",
    "Chronic Absenteeism Rate",
]


def _fixture(path: Path) -> Path:
    """A hand-made file in the layout CDE documents. Values are invented."""
    rows = [
        [
            "2024-25",
            "T",
            "00",
            "00000",
            "0000000",
            "State",
            "",
            "",
            "All",
            "All",
            "TA",
            "5000000",
            "1000000",
            "20.0",
        ],
        [
            "2024-25",
            "T",
            "00",
            "00000",
            "0000000",
            "State",
            "",
            "",
            "All",
            "All",
            "GR912",
            "1800000",
            "450000",
            "25.0",
        ],
        [
            "2024-25",
            "T",
            "00",
            "00000",
            "0000000",
            "State",
            "",
            "",
            "Y",
            "All",
            "TA",
            "1",
            "1",
            "99.0",
        ],
        [
            "2024-25",
            "D",
            "34",
            "12345",
            "0000000",
            "X",
            "Y",
            "",
            "All",
            "All",
            "TA",
            "1",
            "1",
            "88.0",
        ],
        [
            "2024-25",
            "T",
            "00",
            "00000",
            "0000000",
            "State",
            "",
            "",
            "All",
            "All",
            "GR78",
            "5",
            "*",
            "*",
        ],
    ]
    path.write_text("\n".join("\t".join(r) for r in [HEADER, *rows]) + "\n")
    return path


def test_reads_only_state_all_rows(tmp_path: Path) -> None:
    assert read_state_rates(_fixture(tmp_path / "cde.txt")) == {"TA": 20.0, "GR912": 25.0}


def test_compare_reports_gap(pipeline: Path, tmp_path: Path) -> None:
    out = {
        c.category: c for c in compare(pipeline / "warehouse.duckdb", _fixture(tmp_path / "c.txt"))
    }
    assert out["TA"].state_rate_pct == 20.0
    assert out["TA"].generated_rate_pct is not None
    assert out["GR78"].state_rate_pct is None and out["GR78"].gap_pts is None
