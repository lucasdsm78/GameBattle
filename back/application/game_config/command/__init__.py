from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.game_config.command.game_config_command_usecase import (
        GameConfigCommandUseCase,
        GameConfigCommandUseCaseImpl,
    )

__all__ = ["GameConfigCommandUseCase", "GameConfigCommandUseCaseImpl"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from application.game_config.command.game_config_command_usecase import (
            GameConfigCommandUseCase,
            GameConfigCommandUseCaseImpl,
        )

        return {
            "GameConfigCommandUseCase": GameConfigCommandUseCase,
            "GameConfigCommandUseCaseImpl": GameConfigCommandUseCaseImpl,
        }[name]
    raise AttributeError(name)
