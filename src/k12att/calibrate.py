"""Compare generated chronic absenteeism rates with CDE's real statewide file.

Download a Chronic Absenteeism data file (TXT, tab-delimited) from
https://www.cde.ca.gov/Ds/ad/filesabd.asp and pass its path. Column names are matched
loosely (case, spaces and punctuation ignored), because the field names on CDE's file
structure page and the headers inside the files may differ in spacing.

Not yet run against a real CDE file: the workspace this was written in could not reach
cde.ca.gov. The tests use a small fixture in the documented layout.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import duckdb

SPANS = ("GRTKKN", "GR13", "GR46", "GR78", "GR912", "TA")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


@dataclass(frozen=True)
class Comparison:
    category: str
    state_rate_pct: float | None
    generated_rate_pct: float | None

    @property
    def gap_pts(self) -> float | None:
        if self.state_rate_pct is None or self.generated_rate_pct is None:
            return None
        return round(self.generated_rate_pct - self.state_rate_pct, 1)


def read_state_rates(path: Path) -> dict[str, float]:
    """State-level ('T'), all-charter, all-DASS rates by reporting category."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        reader = csv.DictReader(fh, dialect=dialect)
        cols = {_norm(c): c for c in reader.fieldnames or []}

        def col(*options: str) -> str | None:
            return next((cols[o] for o in options if o in cols), None)

        level = col("aggregatelevel")
        category = col("reportingcategory")
        rate = col("chronicabsenteeismrate")
        charter = col("charteryn", "charterallyn", "charter")
        dass = col("dassyn", "dassallyn", "dass")
        if not (level and category and rate):
            raise ValueError(f"unrecognized CDE file layout: {reader.fieldnames}")
        out: dict[str, float] = {}
        for row in reader:
            if row[level].strip() != "T":
                continue
            if charter and row[charter].strip().upper() not in ("ALL", ""):
                continue
            if dass and row[dass].strip().upper() not in ("ALL", ""):
                continue
            value = row[rate].strip().rstrip("%")
            if value in ("", "*"):
                continue
            out[row[category].strip()] = float(value)
        return out


def compare(db_path: Path, cde_file: Path) -> list[Comparison]:
    state = read_state_rates(cde_file)
    con = duckdb.connect(str(db_path))
    try:
        gen = dict(
            con.execute(
                "select reporting_category, chronic_rate_pct from mart_chronic_absenteeism "
                "where aggregate_level = 'D'"
            ).fetchall()
        )
    finally:
        con.close()
    return [Comparison(c, state.get(c), gen.get(c)) for c in SPANS]
