class GameBattleError(Exception):
    """Erreur attendue : son message est rédigé pour être affiché tel quel au présentateur."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DomainError(GameBattleError):
    """Base des erreurs métier (règles du jeu ou de la configuration)."""


class InvalidGameConfigError(DomainError):
    """Une action viole une règle du jeu ou la configuration est incohérente."""


class GameConfigurationNotReadyError(DomainError):
    """La partie ne peut pas encore être lancée."""


class ApplicationError(GameBattleError):
    """Base des refus applicatifs (avant toute règle métier)."""


class UnknownCommandError(ApplicationError):
    """La commande demandée n'existe pas."""


class CommandNotAllowedError(ApplicationError):
    """Le client n'a pas le droit d'envoyer cette commande."""


class InvalidCommandPayloadError(ApplicationError):
    """Les données de la commande sont invalides."""
