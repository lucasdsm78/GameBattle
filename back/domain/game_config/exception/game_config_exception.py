class GameConfigError(Exception):
    """Erreur métier : son message est rédigé pour être affiché tel quel au présentateur."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidGameConfigError(GameConfigError):
    pass


class GameConfigurationNotReadyError(GameConfigError):
    pass
