import pytest
from hypothesis import given
from hypothesis import strategies as st

from battleship.domain.errors import AlreadyClosed, Conflict, SessionClosed
from battleship.domain.state import GameState


@given(st.lists(st.sampled_from(["hit", "killed", "miss"]), min_size=1, max_size=100))
def test_shooting_sequences(results):
    state = GameState()
    for result in results:
        if state.turn == "opponent":
            state.receive_shot("hit")
            assert state.turn == "opponent"
            state.receive_shot("miss")
        state.request_shot("A1")
        assert state.accept_result(result) == "A1"
        assert state.pending_shot is None
        assert state.turn == ("opponent" if result == "miss" else "self")


def test_opponent_can_start_and_hit_keeps_the_turn():
    state = GameState()
    state.receive_shot("killed")
    assert state.turn == "opponent"
    with pytest.raises(Conflict):
        state.request_shot("A1")
    state.receive_shot("miss")
    state.request_shot("A1")
    with pytest.raises(Conflict):
        state.request_shot("B1")
    with pytest.raises(Conflict):
        state.receive_shot("miss")


@pytest.mark.parametrize("state", [GameState(), GameState(turn="opponent", pending_shot="A1")])
def test_unexpected_result(state):
    with pytest.raises(Conflict):
        state.accept_result("hit")


def test_closing_pending_game():
    state = GameState()
    state.request_shot("A1")
    state.close()
    with pytest.raises(AlreadyClosed):
        state.close()
    for operation in [
        lambda: state.request_shot("B1"),
        lambda: state.accept_result("hit"),
        lambda: state.receive_shot("miss"),
    ]:
        with pytest.raises(SessionClosed):
            operation()
