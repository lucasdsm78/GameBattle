"""Événements communs aux jeux à buzzer."""

from domain.shared.events.answer_judged import AnswerJudged
from domain.shared.events.buzz_stream_auto_paused import BuzzStreamAutoPaused
from domain.shared.events.buzzer_pressed import BuzzerPressed

__all__ = ["AnswerJudged", "BuzzStreamAutoPaused", "BuzzerPressed"]
