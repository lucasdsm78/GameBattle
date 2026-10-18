from __future__ import annotations

import random
from typing import Any, Optional


def build_round_sequence(pool: list[str], total: int, random_order: bool) -> list[str]:
    """Répartit `total` manches équitablement entre les jeux de `pool`.

    random_order=True : ordre mélangé en limitant les répétitions consécutives.
    random_order=False : ordre prévisible (round-robin).
    """
    if not pool or total <= 0:
        return []
    base, remainder = divmod(total, len(pool))
    counts = {key: base for key in pool}
    bonus_order = list(pool)
    if random_order:
        random.shuffle(bonus_order)
    for key in bonus_order[:remainder]:
        counts[key] += 1
    return _shuffle_spread(counts) if random_order else _round_robin(pool, counts)


def _round_robin(pool: list[str], counts: dict[str, int]) -> list[str]:
    remaining = dict(counts)
    sequence: list[str] = []
    while any(remaining.values()):
        for key in pool:
            if remaining[key] > 0:
                sequence.append(key)
                remaining[key] -= 1
    return sequence


def _shuffle_spread(counts: dict[str, int]) -> list[str]:
    remaining = dict(counts)
    sequence: list[str] = []
    while any(remaining.values()):
        previous = sequence[-1] if sequence else None
        candidates = [(key, count) for key, count in remaining.items() if count > 0 and key != previous]
        if not candidates:
            candidates = [(key, count) for key, count in remaining.items() if count > 0]
        max_remaining = max(count for _, count in candidates)
        picked = random.choice([key for key, count in candidates if count == max_remaining])
        sequence.append(picked)
        remaining[picked] -= 1
    return sequence


def compute_ranking(teams: list[str], manches_won: dict[str, int]) -> list[dict[str, Any]]:
    """Classement ordonné du DERNIER au PREMIER, pour la révélation progressive."""
    best_first = sorted(teams, key=lambda team: manches_won.get(team, 0), reverse=True)
    ranking: list[dict[str, Any]] = []
    previous_score: Optional[int] = None
    previous_rank = 0
    for index, team in enumerate(best_first):
        score = manches_won.get(team, 0)
        if score != previous_score:
            previous_rank = index + 1
            previous_score = score
        ranking.append({"team": team, "manches_won": score, "rank": previous_rank})
    return list(reversed(ranking))
