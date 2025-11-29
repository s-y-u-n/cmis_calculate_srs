from __future__ import annotations

from itertools import combinations
from typing import Mapping

from ..model.game import Coalition, Game


def update_swimmy_counts(
    game: Game,
    synergy_rules: Mapping[str, Mapping[Coalition, float]],
    counts: dict[str, dict[str, int]],
) -> None:
    """Update Swimmy Axiom satisfaction counts for a single game."""
    ranks = game.ranks
    if ranks is None:
        return

    players = list(game.players)

    # 2 人連立の集合
    two_sets: list[Coalition] = [
        frozenset({i, j}) for i, j in combinations(players, 2)
    ]

    # 比較ヘルパ: 1 if A ≻ B, -1 if A ≺ B, 0 if A ∼ B, None if undefined
    def cmp_coalitions(A: Coalition, B: Coalition) -> int | None:
        rA = ranks.get(A)
        rB = ranks.get(B)
        if rA is None or rB is None:
            return None
        if rA < rB:
            return 1
        if rA > rB:
            return -1
        return 0

    for S in two_sets:
        s_list = sorted(S)
        s1, s2 = s_list[0], s_list[1]
        for T in two_sets:
            if T == S:
                continue
            t_list = sorted(T)
            t1, t2 = t_list[0], t_list[1]

            # antecedent を満たすかどうか
            antecedent_holds = False

            for t1p, t2p in ((t1, t2), (t2, t1)):
                c1 = cmp_coalitions(frozenset({s1}), frozenset({t1p}))
                c2 = cmp_coalitions(frozenset({s2}), frozenset({t2p}))
                cS = cmp_coalitions(S, T)
                if c1 is None or c2 is None or cS is None:
                    continue

                ge1 = c1 in (0, 1)  # {s1} ≽ {pi(t1)}
                ge2 = c2 in (0, 1)  # {s2} ≽ {pi(t2)}
                S_pre_T = cS in (0, -1)  # S \precsim T
                strict = (c1 == 1) or (c2 == 1) or (cS == -1)

                if ge1 and ge2 and S_pre_T and strict:
                    antecedent_holds = True
                    break

            if not antecedent_holds:
                continue

            for rule_name, scores in synergy_rules.items():
                vS = scores.get(S)
                vT = scores.get(T)
                if vS is None or vT is None:
                    continue

                if rule_name not in counts:
                    counts[rule_name] = {"triggered": 0, "satisfied": 0}

                counts[rule_name]["triggered"] += 1

                if rule_name.endswith("_rank"):
                    satisfied = vT < vS  # rank: smaller is better
                else:
                    satisfied = vT > vS  # score: larger is better

                if satisfied:
                    counts[rule_name]["satisfied"] += 1


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
        """synergy level in {1,...,6} or None."""
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

        # L3
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

                if rule_name not in counts:
                    counts[rule_name] = {"triggered": 0, "satisfied": 0}

                counts[rule_name]["triggered"] += 1

                if rule_name.endswith("_rank"):
                    satisfied = vT < vU
                else:
                    satisfied = vT > vU

                if satisfied:
                    counts[rule_name]["satisfied"] += 1
