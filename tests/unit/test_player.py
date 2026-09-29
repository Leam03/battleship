import pytest
from pydantic import ValidationError

from battleship.arena.models import Player


@pytest.mark.parametrize(
    "url",
    ["http://host:abc", "http://host:65536", "http://host:0", "http://ho\nst", "http://host /api"],
)
def test_reject_invalid_network_address(url):
    with pytest.raises(ValidationError):
        Player(name="test", url=url)


@pytest.mark.parametrize("url", ["http://localhost:8000", "http://[::1]:8000/api", "https://host"])
def test_accept_valid_network_address(url):
    assert Player(name="test", url=url + "/").url == url
