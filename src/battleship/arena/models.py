from dataclasses import dataclass, field
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator


class Player(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    url: str

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value.strip() or len(value) > 80:
            raise ValueError("Player name must contain 1–80 characters")
        return value

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
            or parts.port == 0
            or any(char.isspace() or ord(char) < 32 for char in value)
        ):
            raise ValueError("Player URL must be an HTTP(S) base URL without credentials")
        return value.rstrip("/")


class TechnicalDefeat(Exception):
    def __init__(self, player: str, reason: str) -> None:
        self.player = player
        self.reason = reason
        super().__init__(f"{player}: {reason}")


@dataclass
class Move:
    player: str
    coordinate: str
    result: str


@dataclass
class RequestTiming:
    player: str
    operation: str
    elapsed: float
    success: bool


@dataclass
class MatchResult:
    players: tuple[str, str]
    first: str
    winner: str | None = None
    reason: str = ""
    failures: dict[str, list[str]] = field(default_factory=dict)
    moves: list[Move] = field(default_factory=list)
    timings: list[RequestTiming] = field(default_factory=list)

    def add_failure(self, player: str, reason: str) -> None:
        self.failures.setdefault(player, []).append(reason)

    def settle(self) -> None:
        if len(self.failures) == 2:
            self.winner = None
            self.reason = "Both services failed"
        elif self.failures:
            self.winner = next(name for name in self.players if name not in self.failures)
            self.reason = "Technical defeat"
