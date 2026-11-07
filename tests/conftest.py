from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from k12att.build import run_dbt
from k12att.cli import DEMO_BATCHES
from k12att.generate import generate
from k12att.load import load_batch
from k12att.publish import publish

N = 1500  # smaller than the 9,000-student demo, to keep the suite fast


@pytest.fixture(scope="session")
def pipeline(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run the full demo once: three batches, dbt build (with tests), publish."""
    root = tmp_path_factory.mktemp("pipeline")
    db = root / "warehouse.duckdb"
    for batch_id, mode in DEMO_BATCHES:
        generate(root / "raw" / batch_id, n_students=N, mode=mode)
        con = duckdb.connect(str(db))
        load_batch(con, root / "raw" / batch_id)
        con.close()
    run_dbt(db)
    publish(db, root / "site", root / "private")
    return root
