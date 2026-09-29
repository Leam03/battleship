import pytest

from battleship.domain.board import is_defeated, resolve_shot
from battleship.domain.errors import InvalidInput


def test_hit_kill_and_miss():
    fleet = (("A1", "A2"), ("J10",))
    assert resolve_shot(fleet, {}, "B4") == "miss"
    assert resolve_shot(fleet, {}, "A1") == "hit"
    assert resolve_shot(fleet, {"A1": "hit"}, "A2") == "killed"
    assert resolve_shot(fleet, {}, "J10") == "killed"
    assert not is_defeated(fleet, {"A1": "hit", "B4": "miss"})
    assert is_defeated(fleet, {"A1": "hit", "A2": "killed", "J10": "killed"})
    assert fleet == (("A1", "A2"), ("J10",))


@pytest.mark.parametrize("result", ["hit", "miss", "killed"])
def test_repeat_is_rejected(result):
    with pytest.raises(InvalidInput):
        resolve_shot((("A1",),), {"A1": result}, "A1")
