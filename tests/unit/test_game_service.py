from random import Random
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from battleship.db.models import GameSession
from battleship.domain.errors import Conflict, SessionClosed
from battleship.services import game


def session_mock():
    db = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=False)
    db.begin = MagicMock(return_value=transaction)
    db.add = MagicMock()
    return db, transaction


async def test_closed_session_never_invokes_targeting(monkeypatch):
    db, transaction = session_mock()
    stored = GameSession(id=uuid4(), status="closed", turn="unknown", pending_shot=None)
    monkeypatch.setattr(game.queries, "get_game_for_update", AsyncMock(return_value=stored))
    strategy = MagicMock()
    monkeypatch.setattr(game, "choose_shot", strategy)
    with pytest.raises(SessionClosed):
        await game.make_shot(db, stored.id, Random(1))
    strategy.assert_not_called()
    db.add.assert_not_called()
    assert transaction.__aexit__.await_args.args[0] is SessionClosed


async def test_unexpected_result_does_not_complete_a_shot(monkeypatch):
    db, _ = session_mock()
    stored = GameSession(id=uuid4(), status="active", turn="unknown", pending_shot=None)
    monkeypatch.setattr(game.queries, "get_game_for_update", AsyncMock(return_value=stored))
    complete = AsyncMock()
    monkeypatch.setattr(game.queries, "complete_pending_shot", complete)
    with pytest.raises(Conflict):
        await game.accept_shot_result(db, stored.id, "hit")
    complete.assert_not_awaited()
    assert stored.turn == "unknown"


async def test_failed_create_exits_transaction_with_error():
    db, transaction = session_mock()
    db.flush.side_effect = RuntimeError("storage unavailable")
    with pytest.raises(RuntimeError):
        await game.create_game(db, Random(1))
    assert transaction.__aexit__.await_args.args[0] is RuntimeError
