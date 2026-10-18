"""Événements communs aux jeux à buzzer."""

from domain.events.shared.answer_judged import AnswerJudged
from domain.events.shared.buzzer_pressed import BuzzerPressed

__all__ = ["AnswerJudged", "BuzzerPressed"]
