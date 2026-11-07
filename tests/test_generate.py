from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from k12att.generate import DEFECT_RATES, generate


def test_same_seed_same_files(tmp_path: Path) -> None:
    generate(tmp_path / "a", n_students=500)
    generate(tmp_path / "b", n_students=500)
    for f in sorted((tmp_path / "a").iterdir()):
        assert f.read_bytes() == (tmp_path / "b" / f.name).read_bytes(), f.name


def test_manifest_labels_data_as_generated(tmp_path: Path) -> None:
    generate(tmp_path, n_students=500)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["generated"] is True
    assert set(Counter(d["rule_id"] for d in manifest["fatal_defects"])) == set(DEFECT_RATES)


def test_corrected_batch_has_no_fatal_defects(tmp_path: Path) -> None:
    ds = generate(tmp_path, n_students=500, mode="corrected")
    assert ds.defects == []
