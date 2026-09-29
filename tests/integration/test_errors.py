from uuid import uuid4

import pytest


@pytest.mark.parametrize(
    "body",
    [
        {"coordinate": ""},
        {"coordinate": "A01"},
        {"coordinate": "A1\n"},
        {"coordinate": "A١"},
        {"coordinates": "A1"},
        {"coordinate": 1},
        {},
        {"coordinate": "A1", "extra": True},
    ],
)
async def test_bad_coordinates(client, body):
    response = await client.post(f"/game/{uuid4()}/opponent-shot", json=body)
    assert response.status_code == 400
    assert set(response.json()) == {"detail"}


@pytest.mark.parametrize("body", [{}, {"result": "sunk"}, {"result": None}, {"result": 1}])
async def test_bad_results(client, body):
    response = await client.post(f"/game/{uuid4()}/shot/result", json=body)
    assert response.status_code == 400


async def test_invalid_json(client):
    response = await client.post(
        f"/game/{uuid4()}/shot/result",
        content="broken",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
