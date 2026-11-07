from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from k12att.generate import generate
from k12att.load import load_batch

TABLES = ("batches", "raw_files", "validation_results", "senr", "sinf", "stas", "sinc")


def _snapshot(con: duckdb.DuckDBPyConnection) -> dict[str, list[tuple[object, ...]]]:
    out = {}
    for t in TABLES:
        cols = "* exclude (loaded_at)" if t == "batches" else "*"
        out[t] = sorted(con.execute(f"select {cols} from {t}").fetchall(), key=repr)
    return out


def test_loading_a_batch_twice_equals_loading_it_once(tmp_path: Path) -> None:
    generate(tmp_path / "2026-06-15", n_students=400)
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    load_batch(con, tmp_path / "2026-06-15")
    once = _snapshot(con)
    load_batch(con, tmp_path / "2026-06-15")
    assert _snapshot(con) == once


def test_resubmission_under_same_id_replaces_old_rows(tmp_path: Path) -> None:
    generate(tmp_path / "b1", n_students=400, mode="initial")
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    assert load_batch(con, tmp_path / "b1", "2026-06-15").fatal > 0
    generate(tmp_path / "b2", n_students=400, mode="corrected")
    assert load_batch(con, tmp_path / "b2", "2026-06-15").fatal == 0

    fresh = duckdb.connect(str(tmp_path / "f.duckdb"))
    load_batch(fresh, tmp_path / "b2", "2026-06-15")
    assert _snapshot(con) == _snapshot(fresh)


def test_truncated_batch_is_rejected(tmp_path: Path) -> None:
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    generate(tmp_path / "2026-06-22", n_students=1500, mode="corrected")
    generate(tmp_path / "2026-06-29", n_students=1500, mode="truncated")
    assert load_batch(con, tmp_path / "2026-06-22").status == "accepted"
    r = load_batch(con, tmp_path / "2026-06-29")
    assert r.status == "rejected"
    assert r.reason is not None and "9000031" in r.reason


def test_failed_load_leaves_no_partial_batch(tmp_path: Path) -> None:
    generate(tmp_path / "2026-06-15", n_students=400)
    (tmp_path / "2026-06-15" / "SINC.txt").unlink()  # SINC is read last
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    with pytest.raises(FileNotFoundError):
        load_batch(con, tmp_path / "2026-06-15")
    for t in TABLES:
        assert con.execute(f"select count(*) from {t}").fetchone() == (0,), t


def test_rejected_batch_is_not_reported(pipeline: Path) -> None:
    con = duckdb.connect(str(pipeline / "warehouse.duckdb"))
    try:
        assert con.execute("select batch_id from stg_current_batch").fetchone() == ("2026-06-22",)
    finally:
        con.close()
