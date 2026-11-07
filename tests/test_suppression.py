from __future__ import annotations

from collections import defaultdict

from hypothesis import given
from hypothesis import strategies as st

from k12att.constants import SUPPRESSION_MAX
from k12att.suppression import Cell, suppress

RACES = ("RB", "RI", "RA", "RF", "RH", "RD", "RP", "RT", "RW")


@st.composite
def groups(draw: st.DrawFn) -> list[Cell]:
    cells = []
    for entity in draw(
        st.lists(
            st.sampled_from(["district", "9000011", "9000021"]), min_size=1, max_size=3, unique=True
        )
    ):
        for dimension, cats in (("gender", ("GM", "GF", "GX", "GZ")), ("race", RACES)):
            for cat in cats:
                n = draw(st.integers(0, 60))
                cells.append(Cell(entity, dimension, cat, n, draw(st.integers(0, n))))
    return cells


@given(groups())
def test_no_published_cell_has_ten_or_fewer_students(cells: list[Cell]) -> None:
    assert all(c.suppressed for c in suppress(cells) if c.eligible <= SUPPRESSION_MAX)


@given(groups())
def test_never_exactly_one_hidden_cell_in_a_group(cells: list[Cell]) -> None:
    hidden: dict[tuple[str, str], int] = defaultdict(int)
    for c in suppress(cells):
        hidden[(c.entity, c.dimension)] += c.suppressed
    assert all(n != 1 for n in hidden.values())


@given(groups())
def test_suppression_only_adds_hiding(cells: list[Cell]) -> None:
    out = suppress(cells)
    assert [(c.entity, c.category, c.eligible) for c in out] == [
        (c.entity, c.category, c.eligible) for c in cells
    ]


def test_not_reported_hidden_when_another_race_group_is() -> None:
    cells = [Cell("d", "race", r, 50, 5) for r in RACES]
    cells[1] = Cell("d", "race", "RI", 4, 1)
    cells[6] = Cell("d", "race", "RP", 6, 1)
    out = {c.category: c.suppressed for c in suppress(cells)}
    assert out["RD"] and out["RI"] and out["RP"]
    assert not out["RH"]


def test_complementary_picks_next_smallest() -> None:
    cells = [
        Cell("d", "gender", "GM", 500, 50),
        Cell("d", "gender", "GF", 480, 40),
        Cell("d", "gender", "GX", 3, 1),
        Cell("d", "gender", "GZ", 25, 2),
    ]
    out = {c.category: c.suppressed for c in suppress(cells)}
    assert out == {"GM": False, "GF": False, "GX": True, "GZ": True}
