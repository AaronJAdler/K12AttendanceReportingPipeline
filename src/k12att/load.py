"""Land, parse and validate one submission batch into DuckDB.

Loading is idempotent per batch: every row for the batch is deleted and re-inserted in
one transaction, so loading the same batch twice gives the same tables as loading it
once, and a corrected resubmission under the same batch ID replaces the old one.
"""

from __future__ import annotations

import csv
import hashlib
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

from k12att.constants import DELIMITER
from k12att.rules import BATCH_RULE, BATCH_TOLERANCE, PARSE_RULE, RULES
from k12att.schema import DATE_FIELDS, FILE_NAMES, INT_FIELDS, LAYOUTS

TABLES = {rt: rt.lower() for rt in LAYOUTS}


def _col_type(name: str) -> str:
    if name in INT_FIELDS:
        return "INTEGER"
    if name in DATE_FIELDS:
        return "DATE"
    return "VARCHAR"


def init_db(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        create table if not exists batches (
            batch_id varchar primary key, status varchar not null, reason varchar,
            loaded_at timestamp not null default current_timestamp)
        """
    )
    con.execute(
        """
        create table if not exists raw_files (
            batch_id varchar, record_type varchar, file_name varchar,
            sha256 varchar, line_count integer)
        """
    )
    con.execute(
        """
        create table if not exists validation_results (
            batch_id varchar, record_type varchar, line_no integer, rule_id varchar,
            severity varchar, ssid varchar, school_code varchar, detail varchar)
        """
    )
    for rt, fields in LAYOUTS.items():
        cols = ", ".join(f"{f} {_col_type(f)}" for f in fields[1:])
        con.execute(
            f"create table if not exists {TABLES[rt]} (batch_id varchar, line_no integer, {cols})"
        )


@dataclass
class ParseFailure:
    record_type: str
    line_no: int
    ssid: str
    school_code: str
    detail: str


def _convert(field: str, value: str) -> object:
    if value == "":
        return None
    if field in INT_FIELDS:
        n = int(value)
        if n < 0:
            raise ValueError(f"{field} is negative")
        return n
    if field in DATE_FIELDS:
        return date.fromisoformat(value)
    return value


def parse_file(record_type: str, text: str) -> tuple[list[tuple[object, ...]], list[ParseFailure]]:
    """Return (rows, failures). A bad line is never dropped silently."""
    fields = LAYOUTS[record_type]
    rows: list[tuple[object, ...]] = []
    failures: list[ParseFailure] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split(DELIMITER)
        ssid = parts[3] if len(parts) > 3 else ""
        school = parts[2] if len(parts) > 2 else ""
        if len(parts) != len(fields):
            failures.append(
                ParseFailure(
                    record_type,
                    line_no,
                    ssid,
                    school,
                    f"expected {len(fields)} fields, found {len(parts)}",
                )
            )
            continue
        if parts[0] != record_type:
            failures.append(
                ParseFailure(record_type, line_no, ssid, school, f"record type {parts[0]!r}")
            )
            continue
        try:
            values = tuple(_convert(f, v) for f, v in zip(fields[1:], parts[1:], strict=True))
        except ValueError as exc:
            failures.append(ParseFailure(record_type, line_no, ssid, school, str(exc)))
            continue
        rows.append((line_no, *values))
    return rows, failures


def _bulk_insert(
    con: duckdb.DuckDBPyConnection, rt: str, batch_id: str, rows: list[tuple[object, ...]]
) -> None:
    """Insert parsed rows through a temporary CSV; executemany is ~50x slower here."""
    cols = ("line_no", *LAYOUTS[rt][1:])
    types = {c: ("INTEGER" if c == "line_no" else _col_type(c)) for c in cols}
    with tempfile.NamedTemporaryFile("w", suffix=".csv", newline="", delete=False) as fh:
        writer = csv.writer(fh)
        for r in rows:
            writer.writerow(["" if v is None else str(v) for v in r])
        tmp = fh.name
    try:
        con.execute(
            f"insert into {TABLES[rt]} select $batch, * from read_csv($path, header = false, "
            f"columns = {types!r}, nullstr = '', quote = '\"')",
            {"batch": batch_id, "path": tmp},
        )
    finally:
        Path(tmp).unlink()


@dataclass
class LoadResult:
    batch_id: str
    status: str
    reason: str | None
    fatal: int
    warnings: int


def _previous_accepted(con: duckdb.DuckDBPyConnection, batch_id: str) -> str | None:
    row = con.execute(
        "select max(batch_id) from batches where status = 'accepted' and batch_id < ?",
        [batch_id],
    ).fetchone()
    return row[0] if row else None


def load_batch(
    con: duckdb.DuckDBPyConnection, batch_dir: Path, batch_id: str | None = None
) -> LoadResult:
    batch_id = batch_id or batch_dir.name
    init_db(con)
    con.execute("begin transaction")
    try:
        for table in [*TABLES.values(), "raw_files", "validation_results", "batches"]:
            con.execute(f"delete from {table} where batch_id = ?", [batch_id])

        for rt, file_name in FILE_NAMES.items():
            raw = (batch_dir / file_name).read_bytes()
            text = raw.decode("utf-8")
            con.execute(
                "insert into raw_files values (?, ?, ?, ?, ?)",
                [batch_id, rt, file_name, hashlib.sha256(raw).hexdigest(), len(text.splitlines())],
            )
            rows, failures = parse_file(rt, text)
            if rows:
                _bulk_insert(con, rt, batch_id, rows)
            if failures:
                con.executemany(
                    "insert into validation_results values (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            batch_id,
                            f.record_type,
                            f.line_no,
                            PARSE_RULE.rule_id,
                            PARSE_RULE.severity,
                            f.ssid,
                            f.school_code,
                            f.detail,
                        )
                        for f in failures
                    ],
                )

        for rule in RULES:
            con.execute(
                f"""
                insert into validation_results
                select $batch, '{rule.record_type}', line_no, '{rule.rule_id}',
                       '{rule.severity}', ssid, school_code, d
                from ({rule.sql}) as t(line_no, ssid, school_code, d)
                """,
                {"batch": batch_id},
            )

        status, reason = "accepted", None
        prev = _previous_accepted(con, batch_id)
        if prev is not None:
            moved = con.execute(
                """
                with cur as (select school_code, count(*) n from senr
                             where batch_id = $cur group by 1),
                     prev as (select school_code, count(*) n from senr
                              where batch_id = $prev group by 1)
                select p.school_code, p.n, coalesce(c.n, 0)
                from prev p left join cur c using (school_code)
                where abs(coalesce(c.n, 0) - p.n) > $tol * p.n
                order by 1
                """,
                {"cur": batch_id, "prev": prev, "tol": BATCH_TOLERANCE},
            ).fetchall()
            if moved:
                status = "rejected"
                reason = "; ".join(f"school {s}: {p} -> {c} SENR rows" for s, p, c in moved)
                con.executemany(
                    "insert into validation_results values (?, 'SENR', null, ?, ?, null, ?, ?)",
                    [
                        (
                            batch_id,
                            BATCH_RULE.rule_id,
                            BATCH_RULE.severity,
                            s,
                            f"{p} rows in batch {prev}, {c} now",
                        )
                        for s, p, c in moved
                    ],
                )

        con.execute(
            "insert into batches (batch_id, status, reason) values (?, ?, ?)",
            [batch_id, status, reason],
        )
        counts = con.execute(
            "select count(*) filter (where severity = 'Fatal'), "
            "count(*) filter (where severity = 'Warning') "
            "from validation_results where batch_id = ?",
            [batch_id],
        ).fetchone()
        con.execute("commit")
    except BaseException:
        con.execute("rollback")
        raise
    assert counts is not None
    return LoadResult(batch_id, status, reason, int(counts[0]), int(counts[1]))
