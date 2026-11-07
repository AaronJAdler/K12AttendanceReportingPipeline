"""Command-line entry point: ``k12att demo`` runs the whole pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from k12att.build import run_dbt
from k12att.calibrate import compare
from k12att.generate import Mode, generate
from k12att.load import load_batch
from k12att.publish import publish

DEMO_BATCHES: tuple[tuple[str, Mode], ...] = (
    ("2026-06-15", "initial"),  # first end-of-year submission, with injected defects
    ("2026-06-22", "corrected"),  # resubmission with Fatal defects fixed
    ("2026-06-29", "truncated"),  # a partial extract: one school lost 60% of its rows
)


def _load(db: Path, batch_dir: Path) -> None:
    con = duckdb.connect(str(db))
    try:
        r = load_batch(con, batch_dir)
    finally:
        con.close()
    note = f" ({r.reason})" if r.reason else ""
    print(f"batch {r.batch_id}: {r.status}{note}; {r.fatal} Fatal, {r.warnings} Warning")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="k12att")
    p.add_argument("--db", type=Path, default=Path("warehouse.duckdb"))
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="write one synthetic batch")
    g.add_argument("out", type=Path)
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--students", type=int, default=9000)
    g.add_argument("--mode", choices=["initial", "corrected", "truncated"], default="initial")

    ld = sub.add_parser("load", help="land, parse and validate one batch directory")
    ld.add_argument("batch_dir", type=Path)

    sub.add_parser("build", help="run dbt build (models and tests)")

    pb = sub.add_parser("publish", help="write the dashboard and private error reports")
    pb.add_argument("--site", type=Path, default=Path("site"))
    pb.add_argument("--private", type=Path, default=Path("private"))

    cal = sub.add_parser("calibrate", help="compare with a CDE chronic absenteeism file")
    cal.add_argument("cde_file", type=Path)

    d = sub.add_parser("demo", help="generate, load and report three demo batches")
    d.add_argument("--data", type=Path, default=Path("data/raw"))
    d.add_argument("--site", type=Path, default=Path("site"))
    d.add_argument("--private", type=Path, default=Path("private"))

    a = p.parse_args(argv)
    if a.cmd == "generate":
        generate(a.out, seed=a.seed, n_students=a.students, mode=a.mode)
    elif a.cmd == "load":
        _load(a.db, a.batch_dir)
    elif a.cmd == "build":
        run_dbt(a.db)
    elif a.cmd == "publish":
        publish(a.db, a.site, a.private)
    elif a.cmd == "calibrate":
        for c in compare(a.db, a.cde_file):
            print(
                f"{c.category:7} state={c.state_rate_pct} generated={c.generated_rate_pct} "
                f"gap={c.gap_pts}"
            )
    elif a.cmd == "demo":
        a.db.unlink(missing_ok=True)
        for batch_id, mode in DEMO_BATCHES:
            generate(a.data / batch_id, mode=mode)
            _load(a.db, a.data / batch_id)
        run_dbt(a.db)
        pages = publish(a.db, a.site, a.private)
        print(f"published {len(pages)} pages to {a.site}/, error reports to {a.private}/")


if __name__ == "__main__":
    main()
