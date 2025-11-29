from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence

from ..model.game import Coalition, Game


def ordinal_marginal_contributions(game: Game) -> Dict[int, Dict[Coalition, float]]:
    """Legacy ordinal marginal contribution based on rank differences.

    m_i^S = rank(S ∪ {i}) - rank(S)
    """
    if game.ranks is None:
        msg = "Game.ranks must be defined for ordinal metrics."
        raise ValueError(msg)

    players = list(game.players)
    coalitions = list(game.coalitions)
    ranks = game.ranks

    result: dict[int, dict[Coalition, float]] = {i: {} for i in players}

    for i in players:
        for S in coalitions:
            if i in S:
                continue
            s = S
            with_i = frozenset(set(S) | {i})
            if s not in ranks or with_i not in ranks:
                continue
            m = float(ranks[with_i] - ranks[s])
            result[i][s] = m

    return result


def compute_ordinal_banzhaf(game: Game) -> Dict[int, float]:
    """Legacy ordinal Banzhaf: average of rank differences."""
    contributions = ordinal_marginal_contributions(game)
    scores: dict[int, float] = {}
    for i, mc in contributions.items():
        if not mc:
            scores[i] = 0.0
        else:
            scores[i] = sum(mc.values()) / len(mc)
    return scores


def ordinal_marginal_contributions_sign(game: Game) -> Dict[int, Dict[Coalition, int]]:
    """New ordinal marginal contributions m_i^S ∈ {1, -1, 0}.

    m_i^S(≽) = 1  if S ∪ {i} ≻ S
             = -1 if S ≻ S ∪ {i}
             = 0  otherwise
    where smaller rank is preferred.
    """
    if game.ranks is None:
        msg = "Game.ranks must be defined for ordinal metrics."
        raise ValueError(msg)

    players = list(game.players)
    coalitions = list(game.coalitions)
    ranks = game.ranks

    result: dict[int, dict[Coalition, int]] = {i: {} for i in players}

    for i in players:
        for S in coalitions:
            if i in S:
                continue
            s = S
            with_i = frozenset(set(S) | {i})
            if s not in ranks or with_i not in ranks:
                continue
            r_s = ranks[s]
            r_with = ranks[with_i]
            if r_with < r_s:
                m = 1
            elif r_s < r_with:
                m = -1
            else:
                m = 0
            result[i][s] = m

    return result


def compute_ordinal_banzhaf_scores(game: Game) -> Dict[int, int]:
    """Ordinal Banzhaf scores s_i = u_i^+ - u_i^-."""
    contributions = ordinal_marginal_contributions_sign(game)
    scores: dict[int, int] = {}
    for i, mc in contributions.items():
        u_plus = sum(1 for v in mc.values() if v == 1)
        u_minus = sum(1 for v in mc.values() if v == -1)
        scores[i] = u_plus - u_minus
    return scores


@dataclass(frozen=True)
class OrdinalBanzhafRelation:
    """Ordinal Banzhaf relation on players.

    scores: s_i^{≽} = u_i^+ - u_i^-
    R: binary relation on players, i R j ↔ s_i >= s_j
    """

    scores: Mapping[int, int]
    R: frozenset[tuple[int, int]]


def compute_ordinal_banzhaf_relation(game: Game) -> OrdinalBanzhafRelation:
    """Compute the Ordinal Banzhaf relation from coalition ranking."""
    scores = compute_ordinal_banzhaf_scores(game)
    players = list(scores.keys())

    R: set[tuple[int, int]] = set()
    for i in players:
        for j in players:
            if scores[i] >= scores[j]:
                R.add((i, j))

    return OrdinalBanzhafRelation(scores=scores, R=frozenset(R))


@dataclass(frozen=True)
class LexCelRelation:
    """Result of lex-cel computation.

    theta: frequency vectors for each player (highest layer first).
    P: asymmetric part P^le_{succsim} as a set of ordered pairs (i, j).
    I: symmetric part I^le_{succsim} as a set of unordered pairs frozenset({i, j}).
    """

    theta: Mapping[int, Sequence[int]]
    P: frozenset[tuple[int, int]]
    I: frozenset[frozenset[int]]


def compute_lex_cel(game: Game) -> LexCelRelation:
    """Compute lex-cel relation from an ordinal game's coalition ranking.

    Assumes game.ranks provides a total preorder over game.coalitions
    where smaller rank is preferred (Sigma_1 is the best layer).
    """
    if game.ranks is None:
        msg = "Game.ranks must be defined for lex-cel."
        raise ValueError(msg)

    ranks = game.ranks
    players = list(game.players)

    # Build quotient ranking: layers Sigma_1, ..., Sigma_ell
    layer_values = sorted({r for r in ranks.values()})
    layers: list[list[Coalition]] = [[] for _ in layer_values]
    value_to_index = {v: idx for idx, v in enumerate(layer_values)}

    for coalition, r in ranks.items():
        idx = value_to_index[r]
        layers[idx].append(coalition)

    # Compute frequency vectors theta(i) = (i_1, ..., i_ell)
    theta: dict[int, list[int]] = {i: [0] * len(layers) for i in players}
    for k, coalitions in enumerate(layers):
        for S in coalitions:
            for i in S:
                if i in theta:
                    theta[i][k] += 1

    # Lexicographic comparison helper: returns 1 if a > b, -1 if a < b, 0 if equal.
    def _lex_cmp(a: Sequence[int], b: Sequence[int]) -> int:
        for x, y in zip(a, b):
            if x > y:
                return 1
            if x < y:
                return -1
        return 0

    P: set[tuple[int, int]] = set()
    I: set[frozenset[int]] = set()

    for i in players:
        for j in players:
            if i == j:
                continue
            cmp = _lex_cmp(theta[i], theta[j])
            if cmp > 0:
                P.add((i, j))
            elif cmp == 0:
                I.add(frozenset({i, j}))

    return LexCelRelation(
        theta={i: tuple(v) for i, v in theta.items()},
        P=frozenset(P),
        I=frozenset(I),
    )
