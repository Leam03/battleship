import pytest
from hypothesis import given
from hypothesis import strategies as st

from battleship.domain.coordinates import (
    ALL_CELLS,
    format_coordinate,
    neighbors,
    parse_coordinate,
    surrounding_cells,
)
from battleship.domain.errors import InvalidInput


@pytest.mark.parametrize("cell", ALL_CELLS)
def test_round_trip(cell):
    assert parse_coordinate(format_coordinate(cell)) == cell


@pytest.mark.parametrize(
    "value", ["", "A01", "a1", "A0", "K1", "J11", " A1", "A1\n", "A١", None, 1]
)
def test_reject_invalid_coordinate(value):
    with pytest.raises(InvalidInput):
        parse_coordinate(value)


@given(st.integers(min_value=10), st.integers())
def test_format_rejects_outside_board(x, y):
    with pytest.raises(InvalidInput):
        format_coordinate((x, y))


def test_neighbors_and_halo_are_clipped():
    assert neighbors((0, 0)) == {(1, 0), (0, 1)}
    assert surrounding_cells(frozenset({(9, 9)})) == {(8, 8), (8, 9), (9, 8), (9, 9)}
