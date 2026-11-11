from __future__ import annotations

from application.shared.commands.input_model import InputModel


class AnswerCommand(InputModel):
    is_correct: bool
