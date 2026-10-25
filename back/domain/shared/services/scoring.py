from __future__ import annotations

TIE_LABEL = "Égalité"


def zero_scores(teams: list[str]) -> dict[str, int]:
    return {team: 0 for team in teams}


def pick_round_winner(teams: list[str], scores: dict[str, int]) -> str:
    """Équipe au meilleur score, ou `TIE_LABEL` si plusieurs équipes sont à égalité en tête."""
    best = max((scores.get(team, 0) for team in teams), default=0)
    leaders = [team for team in teams if scores.get(team, 0) == best]
    return leaders[0] if len(leaders) == 1 else TIE_LABEL


def award_buzz(scores: dict[str, int], team: str, correct: bool) -> tuple[dict[str, int], int]:
    """Buzz juste : +1 ; buzz faux : −1, sans jamais descendre sous 0. Renvoie (scores, points gagnés)."""
    previous = scores.get(team, 0)
    score = previous + 1 if correct else max(0, previous - 1)
    return {**scores, team: score}, score - previous
