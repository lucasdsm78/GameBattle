class GameConfigError(Exception):
    """Base exception for game configuration domain errors."""


class InvalidGameConfigError(GameConfigError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class GameConfigurationNotReadyError(GameConfigError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


