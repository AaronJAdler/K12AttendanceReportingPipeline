from __future__ import annotations

import csv
import re
from pathlib import Path


def test_every_page_has_basic_accessibility_structure(pipeline: Path) -> None:
    pages = sorted((pipeline / "site").glob("*.html"))
    assert len(pages) == 10
    for p in pages:
        html = p.read_text()
        assert '<html lang="en">' in html, p.name
        assert html.count("<table>") == html.count("<caption>"), p.name
        assert "<th>" not in html, f"{p.name}: header cell without scope"
        assert html.count("<svg") == html.count("<title id="), p.name
        assert "Synthetic data" in html, p.name
        assert "<script" not in html, p.name


def test_public_site_has_no_student_identifiers(pipeline: Path) -> None:
    for p in (pipeline / "site").glob("*.html"):
        html = p.read_text()
        assert not re.search(r"\bL1\d{5}\b", html), p.name
        assert not re.search(r"\b4\d{9}\b", html), p.name


def test_private_error_report_lists_findings_with_local_ids(pipeline: Path) -> None:
    with (pipeline / "private" / "error_report_2026-06-15.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    assert rows == sorted(
        rows, key=lambda r: (r["school_code"], r["severity"], r["rule_id"], int(r["line_no"] or 0))
    )
    stas_or_senr = [r for r in rows if r["record_type"] in ("SENR", "STAS")]
    assert all(r["local_id"] for r in stas_or_senr)


def test_suppressed_cells_appear_on_school_pages(pipeline: Path) -> None:
    assert any(">*<" in p.read_text() for p in (pipeline / "site").glob("school-*.html"))
