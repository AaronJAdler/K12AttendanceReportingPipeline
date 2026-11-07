"""Hand-computed fixture: each student is built to sit on one side of a definition edge."""

from __future__ import annotations

from pathlib import Path

import duckdb

from k12att.build import run_dbt
from k12att.load import load_batch

Y = "2025-2026"
A, B, H = "9000011", "9000012", "9000031"
STUDENTS = [
    # ssid, school, grade, expected, absent, exempt, expectation
    ("0000000001", A, "02", 180, 18, "", "chronic: exactly 10%"),
    ("0000000002", A, "02", 180, 17, "", "not chronic: 9.4%"),
    ("0000000003", A, "KN", 30, 10, "", "ineligible: 30 days"),
    ("0000000004", A, "KN", 31, 4, "", "eligible at 31 days; chronic 12.9%"),
    ("0000000005", A, "03", 0, 0, "Y", "ineligible: exempt"),
    ("0000000006", H, "10", 180, 40, "", "chronic"),
]
# A transfer: 20 days at A (ineligible there, 3 absent), 100 at B (9 absent, not chronic).
# District: 120 days, 12 absent = 10% -> chronic, counted once.
TRANSFER = [("0000000007", A, "04", 20, 3), ("0000000007", B, "04", 100, 9)]


def _write(batch: Path) -> None:
    batch.mkdir(parents=True)
    senr, stas, sinf = [], [], []
    rows = [(s, sch, g, e, ab, ex) for s, sch, g, e, ab, ex, _ in STUDENTS]
    rows += [(s, sch, g, e, ab, "") for s, sch, g, e, ab in TRANSFER]
    for ssid, sch, grade, exp, absent, ex in rows:
        senr.append(f"SENR^{Y}^{sch}^{ssid}^L{ssid[-2:]}^{grade}^10^2025-08-18^")
        stas.append(f"STAS^{Y}^{sch}^{ssid}^L{ssid[-2:]}^{ex}^{exp}^{exp - absent}^{absent}^0^0")
    for ssid in sorted({r[0] for r in rows}):
        sinf.append(f"SINF^2025-08-18^{A}^{ssid}^L{ssid[-2:]}^Test^Student^GF^RH")
    for name, lines in (("SENR", senr), ("STAS", stas), ("SINF", sinf), ("SINC", [])):
        (batch / f"{name}.txt").write_text("".join(x + "\n" for x in lines))


def test_definitions_on_hand_built_students(tmp_path: Path) -> None:
    _write(tmp_path / "2026-06-15")
    db = tmp_path / "w.duckdb"
    con = duckdb.connect(str(db))
    assert load_batch(con, tmp_path / "2026-06-15").fatal == 0
    con.close()
    run_dbt(db)

    con = duckdb.connect(str(db))
    flags = dict(
        con.execute(
            "select ssid || '@' || school_code, (eligible, chronically_absent) "
            "from fct_student_school_year"
        ).fetchall()
    )
    assert flags[f"0000000001@{A}"] == (True, True)
    assert flags[f"0000000002@{A}"] == (True, False)
    assert flags[f"0000000003@{A}"] == (False, False)
    assert flags[f"0000000004@{A}"] == (True, True)
    assert flags[f"0000000005@{A}"] == (False, False)
    assert flags[f"0000000007@{A}"] == (False, False)
    assert flags[f"0000000007@{B}"] == (True, False)

    totals = dict(
        con.execute(
            "select coalesce(school_code, 'D'), (eligible_enrollment, chronic_count) "
            "from mart_chronic_absenteeism where reporting_category = 'TA'"
        ).fetchall()
    )
    con.close()
    assert totals[A] == (3, 2)  # students 1, 2, 4
    assert totals[B] == (1, 0)
    assert totals[H] == (1, 1)
    assert totals["D"] == (5, 4)  # 1, 2, 4, 6, 7 eligible; 1, 4, 6, 7 chronic
