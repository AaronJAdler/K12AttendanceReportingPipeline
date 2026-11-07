from __future__ import annotations

from k12att.load import parse_file

GOOD = "STAS^2025-2026^9000011^4000000001^L1^^180^170^5^5^0"


def test_malformed_lines_are_reported_with_line_numbers_never_dropped() -> None:
    text = "\n".join(
        [
            GOOD,
            "STAS^2025-2026^9000011^4000000002^L2^^180^170^5^5",  # missing field
            "STAS^2025-2026^9000011^4000000003^L3^^180^abc^5^5^0",  # not an integer
            "",
            "SENR^2025-2026^9000011^4000000004^L4^^180^170^5^5^0",  # wrong record type
            "STAS^2025-2026^9000011^4000000005^L5^^-1^0^0^0^0",  # negative
        ]
    )
    rows, failures = parse_file("STAS", text)
    assert [r[0] for r in rows] == [1]
    assert [f.line_no for f in failures] == [2, 3, 5, 6]
    assert failures[0].ssid == "4000000002"
    assert len(rows) + len(failures) == sum(1 for line in text.splitlines() if line.strip())


def test_empty_optional_fields_become_null() -> None:
    rows, failures = parse_file("STAS", GOOD)
    assert failures == []
    assert rows[0][5] is None  # exemption indicator
