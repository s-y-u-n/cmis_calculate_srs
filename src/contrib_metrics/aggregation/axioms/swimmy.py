from __future__ import annotations

from itertools import combinations
from typing import Mapping

from ...model.game import Coalition, Game


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

    two_sets: list[Coalition] = [
        frozenset({i, j}) for i, j in combinations(players, 2)
    ]

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

    for rule_name in synergy_rules:
        counts.setdefault(rule_name, {"triggered": 0, "satisfied": 0})

    for S in two_sets:
        s1, s2 = sorted(S)
        for T in two_sets:
            if T == S:
                continue
            t1, t2 = sorted(T)

            antecedent_holds = False
            for t1p, t2p in ((t1, t2), (t2, t1)):
                c1 = cmp_coalitions(frozenset({s1}), frozenset({t1p}))
                c2 = cmp_coalitions(frozenset({s2}), frozenset({t2p}))
                cS = cmp_coalitions(S, T)
                if c1 is None or c2 is None or cS is None:
                    continue

                ge1 = c1 in (0, 1)
                ge2 = c2 in (0, 1)
                S_pre_T = cS in (0, -1)
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

                counts[rule_name]["triggered"] += 1

                if rule_name.endswith("_rank"):
                    satisfied = vT < vS
                else:
                    satisfied = vT > vS

                if satisfied:
                    counts[rule_name]["satisfied"] += 1
