"""The generator's defect manifest is the oracle: exactly the injected defects are found."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

Key = tuple[str, str, str, str]


def _manifest(root: Path, batch: str, key: str) -> set[Key]:
    m = json.loads((root / "raw" / batch / "manifest.json").read_text())
    return {(d["rule_id"], d["record_type"], d["ssid"], d["school"]) for d in m[key]}


def _found(root: Path, batch: str, severity: str) -> set[Key]:
    con = duckdb.connect(str(root / "warehouse.duckdb"))
    try:
        rows = con.execute(
            "select rule_id, record_type, ssid, school_code from validation_results "
            "where batch_id = ? and severity = ? and rule_id <> 'RB-BATCH-01'",
            [batch, severity],
        ).fetchall()
    finally:
        con.close()
    return {(str(a), str(b), str(c), str(d)) for a, b, c, d in rows}


def test_every_injected_fatal_defect_found_and_nothing_else(pipeline: Path) -> None:
    assert _found(pipeline, "2026-06-15", "Fatal") == _manifest(
        pipeline, "2026-06-15", "fatal_defects"
    )


def test_every_injected_warning_found_and_nothing_else(pipeline: Path) -> None:
    assert _found(pipeline, "2026-06-15", "Warning") == _manifest(
        pipeline, "2026-06-15", "warnings"
    )


def test_corrected_batch_is_clean(pipeline: Path) -> None:
    assert _found(pipeline, "2026-06-22", "Fatal") == set()
