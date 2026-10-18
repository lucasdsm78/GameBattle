from __future__ import annotations

TIE_LABEL = "Égalité"


def zero_scores(teams: list[str]) -> dict[str, int]:
    return {team: 0 for team in teams}


def pick_round_winner(teams: list[str], scores: dict[str, int]) -> str:
    """Équipe au meilleur score, ou `TIE_LABEL` si plusieurs équipes sont à égalité en tête."""
    best = max((scores.get(team, 0) for team in teams), default=0)
    leaders = [team for team in teams if scores.get(team, 0) == best]
    return leaders[0] if len(leaders) == 1 else TIE_LABEL
