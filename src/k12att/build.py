"""Run the dbt project against the DuckDB warehouse."""

from __future__ import annotations

import json
import os
from pathlib import Path

from k12att.constants import CHRONIC_THRESHOLD, MIN_EXPECTED_DAYS

DBT_DIR = Path(__file__).resolve().parents[2] / "dbt"


def run_dbt(db_path: Path, command: str = "build") -> None:
    """Run ``dbt <command>``; raise if any model or test fails."""
    from dbt.cli.main import dbtRunner

    os.environ["K12ATT_DB"] = str(db_path.resolve())
    dbt_vars = json.dumps(
        {"chronic_threshold": CHRONIC_THRESHOLD, "min_expected_days": MIN_EXPECTED_DAYS}
    )
    result = dbtRunner().invoke(
        [
            command,
            "--project-dir",
            str(DBT_DIR),
            "--profiles-dir",
            str(DBT_DIR),
            "--vars",
            dbt_vars,
            "--quiet",
        ]
    )
    if not result.success:
        raise RuntimeError(f"dbt {command} failed: {result.exception or 'see output above'}")
