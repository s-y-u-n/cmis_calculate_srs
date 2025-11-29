from __future__ import annotations

from itertools import combinations
from typing import Dict

from ..model.game import Game


def compute_banzhaf(game: Game, normalize: bool = True) -> Dict[int, float]:
    n = len(game.players)
    if n == 0:
        return {}

    value_cache: dict[frozenset[int], float] = {}
    for c, v in game.values.items():
        value_cache[c] = float(v)

    def v(coalition: frozenset[int]) -> float:
        return value_cache.get(coalition, 0.0)

    players = list(game.players)
    raw: dict[int, float] = {i: 0.0 for i in players}

    for i in players:
        others = [p for p in players if p != i]
        for k in range(0, len(others) + 1):
            for subset in combinations(others, k):
                s = frozenset(subset)
                with_i = frozenset(set(subset) | {i})
                marginal = v(with_i) - v(s)
                raw[i] += marginal

    if not normalize:
        return raw

    total = sum(abs(x) for x in raw.values())
    if total == 0:
        return raw
    return {i: x / total for i, x in raw.items()}
