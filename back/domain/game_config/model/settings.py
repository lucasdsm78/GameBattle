from __future__ import annotations

from dataclasses import dataclass, field

from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.culture_questions import CULTURE_DIFFICULTIES

SUPPORTED_GAME_KEYS = frozenset(
    {"blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word"}
)
DEFAULT_BUZZER_KEYS = ("1", "2", "3", "4", "5", "6")
ALLOWED_CULTURE_DIFFICULTIES = frozenset({"toutes", *CULTURE_DIFFICULTIES})
MAX_TOTAL_ROUNDS = 30


def build_default_buzzer_keys(team_count: int) -> list[str]:
    if team_count <= len(DEFAULT_BUZZER_KEYS):
        return list(DEFAULT_BUZZER_KEYS[:team_count])
    return [str(index + 1) for index in range(team_count)]


@dataclass(slots=True)
class GameDefinition:
    game_key: str
    label: str
    enabled: bool
    round_count: int

    def validate(self) -> None:
        if self.game_key not in SUPPORTED_GAME_KEYS:
            raise InvalidGameConfigError(f"Jeu non supporté: {self.game_key}.")
        if len(self.label.strip()) < 2:
            raise InvalidGameConfigError("Chaque jeu doit avoir un libellé lisible.")
        # Conservé pour compatibilité : la séquence est répartie depuis `total_rounds`.
        if not 0 <= self.round_count <= MAX_TOTAL_ROUNDS:
            raise InvalidGameConfigError("Le nombre de manches par jeu est invalide.")


@dataclass(slots=True)
class GameSettings:
    game_title: str
    random_round_order: bool
    teams: list[str]
    buzzer_keys: list[str] = field(default_factory=list)
    total_rounds: int = 1
    culture_difficulty: str = "toutes"

    def validate(self) -> None:
        if len(self.game_title.strip()) < 3:
            raise InvalidGameConfigError("Le titre de la partie doit contenir au moins 3 caractères.")
        if not 1 <= self.total_rounds <= MAX_TOTAL_ROUNDS:
            raise InvalidGameConfigError(f"Le nombre de manches doit être compris entre 1 et {MAX_TOTAL_ROUNDS}.")
        if self.culture_difficulty not in ALLOWED_CULTURE_DIFFICULTIES:
            raise InvalidGameConfigError("La difficulté de culture générale est invalide.")
        if len(self.teams) < 2:
            raise InvalidGameConfigError("Au moins 2 équipes sont requises.")
        normalized_teams = [team.strip() for team in self.teams]
        if any(len(team) < 2 for team in normalized_teams):
            raise InvalidGameConfigError("Chaque équipe doit contenir au moins 2 caractères.")
        if len({team.lower() for team in normalized_teams}) != len(normalized_teams):
            raise InvalidGameConfigError("Les noms d'équipes doivent être uniques.")
        normalized_keys = [key.strip().lower() for key in self.buzzer_keys if key.strip()]
        if not normalized_keys:
            normalized_keys = build_default_buzzer_keys(len(normalized_teams))
        if len(normalized_keys) != len(normalized_teams):
            raise InvalidGameConfigError("Chaque équipe doit avoir une touche buzzer configurée.")
        if len(set(normalized_keys)) != len(normalized_keys):
            raise InvalidGameConfigError("Les touches buzzer doivent être uniques pour chaque équipe.")
        self.teams = normalized_teams
        self.buzzer_keys = normalized_keys


@dataclass(slots=True)
class GameRoundPlan:
    id: str
    label: str
    game_key: str
    planned_track_count: int
    buzzer_enabled: bool

    def validate(self) -> None:
        if len(self.id.strip()) < 3:
            raise InvalidGameConfigError("Chaque manche doit avoir un identifiant valide.")
        if len(self.label.strip()) < 2:
            raise InvalidGameConfigError("Chaque manche doit avoir un nom lisible.")
        if self.game_key not in SUPPORTED_GAME_KEYS:
            raise InvalidGameConfigError(f"Jeu de manche non supporté: {self.game_key}.")
        if not 1 <= self.planned_track_count <= 100:
            raise InvalidGameConfigError("Le nombre d'éléments prévus pour une manche doit être compris entre 1 et 100.")
