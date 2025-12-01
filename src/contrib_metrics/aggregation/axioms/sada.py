from __future__ import annotations

from itertools import combinations
from typing import Mapping

from ...model.game import Coalition, Game


def update_sada_counts(
    game: Game,
    synergy_rules: Mapping[str, Mapping[Coalition, float]],
    counts: dict[str, dict[str, int]],
) -> None:
    """Update Synergy–Anasy Distinction counts for a single game."""
    ranks = game.ranks
    if ranks is None:
        return

    players = list(game.players)

    two_sets: list[Coalition] = [
        frozenset({i, j}) for i, j in combinations(players, 2)
    ]

    def _level(T: Coalition) -> int | None:
        """Synergy level in {1,...,6} or None if undefined."""
        if len(T) != 2:
            return None
        i, j = sorted(T)
        A, B, P = frozenset({i}), frozenset({j}), frozenset({i, j})
        if A not in ranks or B not in ranks or P not in ranks:
            return None

        def succeq(X: Coalition, Y: Coalition) -> bool:
            return ranks[X] <= ranks[Y]

        def succ(X: Coalition, Y: Coalition) -> bool:
            return ranks[X] < ranks[Y]

        def sim(X: Coalition, Y: Coalition) -> bool:
            return ranks[X] == ranks[Y]

        if sim(P, A) and sim(A, B):
            return 3

        for p1, p2 in ((i, j), (j, i)):
            C1, C2 = frozenset({p1}), frozenset({p2})

            if succ(P, C1) and succeq(C1, C2):
                return 1
            if sim(P, C1) and succ(C1, C2):
                return 2
            if succ(C1, P) and succ(P, C2):
                return 4
            if succ(C1, P) and sim(P, C2):
                return 5
            if succeq(C1, C2) and succ(C2, P):
                return 6

        return None

    levels: dict[Coalition, int] = {}
    for T in two_sets:
        level = _level(T)
        if level is not None:
            levels[T] = level

    for rule_name in synergy_rules:
        counts.setdefault(rule_name, {"triggered": 0, "satisfied": 0})

    for T in two_sets:
        if T not in levels:
            continue
        for U in two_sets:
            if U == T or U not in levels:
                continue
            if levels[T] >= levels[U]:
                continue

            for rule_name, scores in synergy_rules.items():
                vT = scores.get(T)
                vU = scores.get(U)
                if vT is None or vU is None:
                    continue

                counts[rule_name]["triggered"] += 1

                if rule_name.endswith("_rank"):
                    satisfied = vT < vU
                else:
                    satisfied = vT > vU

                if satisfied:
                    counts[rule_name]["satisfied"] += 1
