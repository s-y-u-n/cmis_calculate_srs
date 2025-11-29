from __future__ import annotations

import math
from itertools import combinations
from typing import Dict, Iterable, Mapping, Optional

from ..model.game import Coalition, Game


def _value_cache(game: Game) -> Mapping[Coalition, float]:
    cache: dict[Coalition, float] = {}
    for c, v in game.values.items():
        cache[c] = float(v)
    return cache


def _all_subsets(players: Iterable[int]) -> list[Coalition]:
    p_list = list(players)
    subsets: list[Coalition] = []
    for k in range(len(p_list) + 1):
        for comb in combinations(p_list, k):
            subsets.append(frozenset(comb))
    return subsets


def compute_shapley_interaction(
    game: Game,
    subsets: Optional[Iterable[Coalition]] = None,
) -> Dict[Coalition, float]:
    """Compute Shapley interaction index I_v(S) for coalitions S.

    Definition:
        I_v(S) =
            sum_{T ⊆ N\\S} [(n - t - s)! t! / (n - s + 1)!]
                * sum_{L ⊆ S} (-1)^{s-l} v(L ∪ T),
    where n = |N|, s = |S|, t = |T|, l = |L|.
    """
    players = list(game.players)
    n = len(players)
    if n == 0:
        return {}

    value_cache = _value_cache(game)

    # Target coalitions S
    if subsets is None:
        target_subsets = [
            frozenset(S)
            for k in range(1, n + 1)
            for S in combinations(players, k)
        ]
    else:
        target_subsets = [frozenset(S) for S in subsets]

    # Precompute factorials up to n
    factorials = [math.factorial(k) for k in range(n + 1)]

    def v(coalition: Coalition) -> float:
        return value_cache.get(coalition, 0.0)

    result: dict[Coalition, float] = {}

    for S in target_subsets:
        s = len(S)
        if s == 0:
            # By convention we return 0 for the empty coalition.
            result[S] = 0.0
            continue

        outer_sum = 0.0
        rest = [p for p in players if p not in S]

        for t in range(len(rest) + 1):
            for T_tuple in combinations(rest, t):
                T = frozenset(T_tuple)

                inner_sum = 0.0
                # L ⊆ S
                for l in range(s + 1):
                    for L_tuple in combinations(S, l):
                        L = frozenset(L_tuple)
                        sign = -1.0 if (s - l) % 2 == 1 else 1.0
                        inner_sum += sign * v(L | T)

                coeff = (
                    factorials[n - t - s] * factorials[t] /
                    math.factorial(n - s + 1)
                )
                outer_sum += coeff * inner_sum

        result[S] = outer_sum

    return result


def compute_banzhaf_interaction(
    game: Game,
    subsets: Optional[Iterable[Coalition]] = None,
) -> Dict[Coalition, float]:
    """Compute Banzhaf interaction index I_v^B(S) for coalitions S.

    Definition:
        I_v^B(S) =
            (1 / 2^{n-s}) * sum_{T ⊆ N\\S} sum_{L ⊆ S} (-1)^{s-l} v(L ∪ T),
    where n = |N|, s = |S|, t = |T|, l = |L|.
    """
    players = list(game.players)
    n = len(players)
    if n == 0:
        return {}

    value_cache = _value_cache(game)

    # Target coalitions S
    if subsets is None:
        target_subsets = [
            frozenset(S)
            for k in range(1, n + 1)
            for S in combinations(players, k)
        ]
    else:
        target_subsets = [frozenset(S) for S in subsets]

    def v(coalition: Coalition) -> float:
        return value_cache.get(coalition, 0.0)

    result: dict[Coalition, float] = {}

    for S in target_subsets:
        s = len(S)
        if s == 0:
            result[S] = 0.0
            continue

        rest = [p for p in players if p not in S]
        total_sum = 0.0

        for t in range(len(rest) + 1):
            for T_tuple in combinations(rest, t):
                T = frozenset(T_tuple)

                inner_sum = 0.0
                for l in range(s + 1):
                    for L_tuple in combinations(S, l):
                        L = frozenset(L_tuple)
                        sign = -1.0 if (s - l) % 2 == 1 else 1.0
                        inner_sum += sign * v(L | T)

                total_sum += inner_sum

        result[S] = total_sum / (2.0 ** (n - s))

    return result

