from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from battleship.domain.errors import InvalidInput
from battleship.domain.fleet import (
    FALLBACK,
    generate_fleet,
    ship_placements,
    validate_fleet,
    validate_ship,
)


@given(st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=100)
def test_generated_fleet_is_valid(seed):
    fleet = generate_fleet(Random(seed))
    validate_fleet(fleet)
    assert sum(map(len, fleet)) == 20
    assert fleet == generate_fleet(Random(seed))


@pytest.mark.parametrize("seed", range(10))
def test_fallback_is_valid(seed):
    validate_fleet(generate_fleet(Random(seed), max_steps=0))


@pytest.mark.parametrize("ship", [[], ["A1", "A1"], ["A1", "B2"], ["A1", "A3"], ["Z1"]])
def test_invalid_ship(ship):
    with pytest.raises(InvalidInput):
        validate_ship(ship)


@pytest.mark.parametrize("cell", ["A1", "A2", "E2"])
def test_touching_and_overlap(cell):
    fleet = list(FALLBACK)
    fleet[-1] = (cell,)
    with pytest.raises(InvalidInput):
        validate_fleet(fleet)


def test_fleet_composition():
    with pytest.raises(InvalidInput):
        validate_fleet(FALLBACK[:-1])


@pytest.mark.parametrize("length, count", [(1, 100), (2, 180), (3, 160), (4, 140)])
def test_placement_counts(length, count):
    assert len(ship_placements(length)) == count
    assert len(set(ship_placements(length))) == count
