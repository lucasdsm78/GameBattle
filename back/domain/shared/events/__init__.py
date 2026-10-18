"""Événements communs aux jeux à buzzer."""

from domain.shared.events.answer_judged import AnswerJudged
from domain.shared.events.buzzer_pressed import BuzzerPressed

__all__ = ["AnswerJudged", "BuzzerPressed"]
