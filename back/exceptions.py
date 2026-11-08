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


class InvalidAccountError(DomainError):
    """Le pseudo ou le mot de passe ne respecte pas les règles des comptes.

    `field` désigne le champ fautif : l'app joueur affiche le message sous ce champ.
    """

    field: str = ""


class InvalidPseudoError(InvalidAccountError):
    field = "pseudo"


class InvalidPasswordError(InvalidAccountError):
    field = "password"


class PseudoAlreadyTakenError(InvalidPseudoError):
    """Un autre joueur porte déjà ce pseudo."""


class InvalidCredentialsError(ApplicationError):
    """Pseudo ou mot de passe incorrect, sans dire lequel des deux."""


class NotAuthenticatedError(ApplicationError):
    """Aucune session de joueur valide."""


class TooManyAttemptsError(ApplicationError):
    """Trop d'essais rapprochés : on attend `retry_after_seconds` avant de réessayer."""

    def __init__(self, retry_after_seconds: int) -> None:
        minutes = max(1, -(-retry_after_seconds // 60))
        super().__init__(f"Trop de tentatives. Réessaie dans {minutes} min.")
        self.retry_after_seconds = retry_after_seconds


class ConcurrentModificationError(ApplicationError):
    """Verrou optimiste : la partie a été écrite entre notre lecture et notre écriture ; rien n'a été écrasé."""

    def __init__(self) -> None:
        super().__init__("La partie vient d'être modifiée en même temps : l'action n'a pas été appliquée, réessaie.")
