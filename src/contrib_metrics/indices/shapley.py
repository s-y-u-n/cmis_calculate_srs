from __future__ import annotations

import math
import random
from itertools import combinations, permutations
from typing import Dict, Iterable

from ..model.game import Game


def compute_shapley_exact(game: Game) -> Dict[int, float]:
    n = len(game.players)
    if n == 0:
        return {}

    factorials = [math.factorial(k) for k in range(n + 1)]
    total_factorial = factorials[n]

    value_cache = _value_cache(game)
    indices: dict[int, float] = {i: 0.0 for i in game.players}
    players = list(game.players)

    for i in players:
        others = [p for p in players if p != i]
        for k in range(0, len(others) + 1):
            for subset in combinations(others, k):
                s = frozenset(subset)
                with_i = frozenset(set(subset) | {i})
                weight = (
                    factorials[len(s)]
                    * factorials[n - len(s) - 1]
                    / total_factorial
                )
                marginal = value_cache.get(with_i, 0.0) - value_cache.get(s, 0.0)
                indices[i] += weight * marginal

    return indices


def compute_shapley_mc(
    game: Game,
    num_samples: int = 1000,
    rng: random.Random | None = None,
) -> Dict[int, float]:
    if rng is None:
        rng = random.Random()

    n = len(game.players)
    if n == 0 or num_samples <= 0:
        return {i: 0.0 for i in game.players}

    value_cache = _value_cache(game)
    players = list(game.players)
    indices: dict[int, float] = {i: 0.0 for i in players}

    for _ in range(num_samples):
        perm = players[:]
        rng.shuffle(perm)
        coalition: set[int] = set()
        prev_value = 0.0

        for i in perm:
            coalition.add(i)
            current_value = value_cache.get(frozenset(coalition), 0.0)
            indices[i] += current_value - prev_value
            prev_value = current_value

    for i in players:
        indices[i] /= num_samples

    return indices


def _value_cache(game: Game) -> dict[frozenset[int], float]:
    cache: dict[frozenset[int], float] = {}
    for coalition, value in game.values.items():
        cache[coalition] = float(value)
    return cache
