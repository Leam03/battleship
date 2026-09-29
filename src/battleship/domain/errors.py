class GameError(Exception):
    pass


class InvalidInput(GameError):
    pass


class SessionNotFound(GameError):
    pass


class SessionClosed(GameError):
    pass


class Conflict(GameError):
    pass


class AlreadyClosed(GameError):
    pass
