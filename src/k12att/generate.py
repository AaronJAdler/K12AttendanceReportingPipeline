"""Seeded generator for synthetic CALPADS-shaped submission files.

Every record this module writes is generated. No real student data is used. The
generator also writes ``manifest.json``: the exact list of defects it injected, which
the tests use as the oracle for the validation rules.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from k12att.constants import ACADEMIC_YEAR, DELIMITER, SCHOOL_DAYS, grade_span
from k12att.schema import FILE_NAMES, GENDERS, LAYOUTS, RACES

Mode = Literal["initial", "corrected", "truncated"]

# Placeholder target rates by CDE grade span. These are rough guesses, NOT taken from
# the CDE file; `k12att calibrate` compares generated output with the real file.
TARGET_CHRONIC_RATE: dict[str, float] = {
    "GRTKKN": 0.30,
    "GR13": 0.18,
    "GR46": 0.16,
    "GR78": 0.20,
    "GR912": 0.25,
}

SCHOOLS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("9000011", "Alder Elementary", ("TK", "KN", "01", "02", "03", "04", "05")),
    ("9000012", "Birch Elementary", ("TK", "KN", "01", "02", "03", "04", "05")),
    ("9000013", "Cedar Elementary", ("TK", "KN", "01", "02", "03", "04", "05")),
    ("9000014", "Dogwood Elementary", ("TK", "KN", "01", "02", "03", "04", "05")),
    ("9000021", "Elm Middle", ("06", "07", "08")),
    ("9000022", "Fir Middle", ("06", "07", "08")),
    ("9000031", "Grove High", ("09", "10", "11", "12")),
    ("9000032", "Harbor High", ("09", "10", "11", "12")),
)
SCHOOL_NAMES = {code: name for code, name, _ in SCHOOLS}
GRADES = ("TK", "KN", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12")

FIRST_NAMES = ("Ava", "Mateo", "Lin", "Noah", "Priya", "Sofia", "Kai", "Amara", "Leo", "Maya")
LAST_NAMES = ("Garcia", "Nguyen", "Smith", "Patel", "Lopez", "Kim", "Brown", "Singh", "Diaz")

# Fatal-defect rates, as a share of eligible records.
DEFECT_RATES: dict[str, float] = {
    "RB-STAS-01": 0.005,
    "RB-SENR-01": 0.005,
    "RB-STAS-03": 0.003,
    "RB-SENR-02": 0.002,
    "RB-SENR-03": 0.002,
    "RB-SINF-01": 0.003,
    "RB-PARSE-01": 0.002,
}
WARNING_RATE = 0.10  # share of suspended students whose incident record is missing


def school_calendar() -> list[date]:
    """180 weekdays from 2025-08-18, skipping three breaks (a simplified calendar)."""
    breaks = [
        (date(2025, 11, 24), date(2025, 11, 28)),
        (date(2025, 12, 22), date(2026, 1, 2)),
        (date(2026, 3, 30), date(2026, 4, 3)),
    ]
    days: list[date] = []
    d = date(2025, 8, 18)
    while len(days) < SCHOOL_DAYS:
        if d.weekday() < 5 and not any(a <= d <= b for a, b in breaks):
            days.append(d)
        d += timedelta(days=1)
    return days


CALENDAR = school_calendar()


def expected_days(start: date, exit_: date | None) -> int:
    end = exit_ or CALENDAR[-1]
    return sum(1 for d in CALENDAR if start <= d <= end)


@dataclass
class Dataset:
    rows: dict[str, list[list[str]]] = field(default_factory=lambda: {rt: [] for rt in LAYOUTS})
    defects: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)


def _clean(seed: int, n_students: int) -> Dataset:
    rng = random.Random(seed)
    ds = Dataset()
    by_grade: dict[str, list[str]] = {
        g: [code for code, _, grades in SCHOOLS if g in grades] for g in GRADES
    }
    incident_seq = 0
    for i in range(n_students):
        ssid = f"{4000000000 + i:010d}"
        local_id = f"L{100000 + i}"
        grade = GRADES[i % len(GRADES)]
        school = rng.choice(by_grade[grade])
        span = grade_span(grade)

        # Enrollment spells: most students stay all year; some transfer; some enroll late.
        spells: list[tuple[str, date, date | None]] = []
        r = rng.random()
        if r < 0.05:
            cut = rng.randrange(30, 150)
            other = rng.choice([s for s in by_grade[grade] if s != school])
            spells.append((school, CALENDAR[0], CALENDAR[cut - 1]))
            spells.append((other, CALENDAR[cut], None))
        elif r < 0.08:
            spells.append((school, CALENDAR[rng.randrange(120, 175)], None))
        else:
            spells.append((school, CALENDAR[0], None))

        exempt = rng.random() < 0.005
        chronic_target = rng.random() < TARGET_CHRONIC_RATE[span]
        absence_rate = rng.uniform(0.11, 0.35) if chronic_target else rng.uniform(0.0, 0.09)
        suspended = rng.random() < 0.03

        ds.rows["SINF"].append(
            [
                "SINF",
                spells[0][1].isoformat(),
                spells[0][0],
                ssid,
                local_id,
                rng.choice(FIRST_NAMES),
                rng.choice(LAST_NAMES),
                rng.choices(GENDERS, weights=(49, 49, 1, 1))[0],
                rng.choices(RACES, weights=(5, 1, 12, 3, 55, 2, 1, 4, 17))[0],
            ]
        )
        for k, (sch, start, exit_) in enumerate(spells):
            ds.rows["SENR"].append(
                [
                    "SENR",
                    ACADEMIC_YEAR,
                    sch,
                    ssid,
                    local_id,
                    grade,
                    "10",
                    start.isoformat(),
                    exit_.isoformat() if exit_ else "",
                ]
            )
            exp = 0 if exempt else expected_days(start, exit_)
            absent = round(exp * absence_rate)
            oss = min(absent, rng.randint(1, 3)) if suspended and k == 0 and absent else 0
            unexcused = round((absent - oss) * 0.4)
            excused = absent - oss - unexcused
            ds.rows["STAS"].append(
                [
                    "STAS",
                    ACADEMIC_YEAR,
                    sch,
                    ssid,
                    local_id,
                    "Y" if exempt else "",
                    str(exp),
                    str(exp - absent),
                    str(excused),
                    str(unexcused),
                    str(oss),
                ]
            )
            if oss:
                incident_seq += 1
                ds.rows["SINC"].append(
                    [
                        "SINC",
                        ACADEMIC_YEAR,
                        sch,
                        f"INC{incident_seq:06d}",
                        ssid,
                        CALENDAR[rng.randrange(0, 60)].isoformat(),
                    ]
                )
    return ds


def _inject(ds: Dataset, rng: random.Random) -> None:
    """Inject each defect type into distinct students and record it in the manifest."""
    used: set[str] = set()

    def pick(
        rt: str, rate: float, pred: Callable[[list[str]], bool] = lambda _: True
    ) -> list[list[str]]:
        pool = [r for r in ds.rows[rt] if r[3] not in used and pred(r)]
        k = max(1, round(len(pool) * rate))
        chosen = rng.sample(pool, k)
        for r in chosen:
            used.add(r[3])
        return chosen

    def log(rule: str, rt: str, row: list[str]) -> None:
        ds.defects.append({"rule_id": rule, "record_type": rt, "ssid": row[3], "school": row[2]})

    # STAS for a school the student never enrolled at (added row).
    enrolled: dict[str, set[str]] = {}
    for e in ds.rows["SENR"]:
        enrolled.setdefault(e[3], set()).add(e[2])
    for r in pick("STAS", DEFECT_RATES["RB-STAS-01"], lambda r: r[5] != "Y"):
        wrong = next(s for s, _, _ in SCHOOLS if s not in enrolled[r[3]])
        extra = [*r]
        extra[2] = wrong
        ds.rows["STAS"].append(extra)
        log("RB-STAS-01", "STAS", extra)

    # Enrollment with its STAS record missing.
    for r in pick("SENR", DEFECT_RATES["RB-SENR-01"]):
        ds.rows["STAS"] = [s for s in ds.rows["STAS"] if not (s[3] == r[3] and s[2] == r[2])]
        log("RB-SENR-01", "SENR", r)

    # Attended + absent exceeds expected days.
    for r in pick("STAS", DEFECT_RATES["RB-STAS-03"], lambda r: r[5] != "Y"):
        r[7] = str(int(r[7]) + rng.randint(1, 5))
        log("RB-STAS-03", "STAS", r)

    # Invalid grade level.
    for r in pick("SENR", DEFECT_RATES["RB-SENR-02"]):
        r[5] = rng.choice(("13", "K1", "00"))
        log("RB-SENR-02", "SENR", r)

    # Exit date before start date.
    for r in pick("SENR", DEFECT_RATES["RB-SENR-03"]):
        r[8] = (date.fromisoformat(r[7]) - timedelta(days=10)).isoformat()
        log("RB-SENR-03", "SENR", r)

    # Conflicting duplicate SINF: both rows are quarantined.
    for r in pick("SINF", DEFECT_RATES["RB-SINF-01"]):
        dup = [*r]
        dup[7] = "GF" if r[7] != "GF" else "GM"
        ds.rows["SINF"].append(dup)
        log("RB-SINF-01", "SINF", r)

    # Malformed line (a field missing). Kept to SINF so it causes no cross-file finding.
    for r in pick("SINF", DEFECT_RATES["RB-PARSE-01"]):
        r.pop()
        log("RB-PARSE-01", "SINF", r)


def _inject_warnings(ds: Dataset, rng: random.Random) -> None:
    flagged = {d["ssid"] for d in ds.defects}
    suspended = [r for r in ds.rows["SINC"] if r[4] not in flagged]
    for inc in rng.sample(suspended, max(1, round(len(suspended) * WARNING_RATE))):
        ds.rows["SINC"].remove(inc)
        ds.warnings.append(
            {"rule_id": "RB-STAS-02", "record_type": "STAS", "ssid": inc[4], "school": inc[2]}
        )


def _truncate(ds: Dataset, school: str, keep: float) -> None:
    for rt in ("SENR", "STAS"):
        rows = [r for r in ds.rows[rt] if r[2] == school]
        drop = {id(r) for r in rows[int(len(rows) * keep) :]}
        ds.rows[rt] = [r for r in ds.rows[rt] if id(r) not in drop]
    keep_ids = {(r[3], r[2]) for r in ds.rows["SENR"]}
    ds.rows["STAS"] = [r for r in ds.rows["STAS"] if (r[3], r[2]) in keep_ids]


def generate(
    out_dir: Path, *, seed: int = 42, n_students: int = 9000, mode: Mode = "initial"
) -> Dataset:
    """Write one batch of submission files plus manifest.json to ``out_dir``."""
    ds = _clean(seed, n_students)
    rng = random.Random(seed + 1)
    if mode == "initial":
        _inject(ds, rng)
    _inject_warnings(ds, rng)
    if mode == "truncated":
        _truncate(ds, "9000031", keep=0.4)
        remaining = {r[3] for r in ds.rows["STAS"]}
        ds.warnings = [w for w in ds.warnings if w["ssid"] in remaining]

    out_dir.mkdir(parents=True, exist_ok=True)
    for rt, rows in ds.rows.items():
        text = "".join(DELIMITER.join(r) + "\n" for r in rows)
        (out_dir / FILE_NAMES[rt]).write_text(text, encoding="utf-8")
    manifest = {
        "generated": True,
        "note": "Synthetic data. No real students.",
        "seed": seed,
        "mode": mode,
        "n_students": n_students,
        "fatal_defects": ds.defects,
        "warnings": ds.warnings,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return ds
