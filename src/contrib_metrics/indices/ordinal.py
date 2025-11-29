from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence

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


def compute_group_ordinal_banzhaf_scores(
    game: Game,
    subsets: Iterable[Coalition] | None = None,
) -> Dict[Coalition, int]:
    """Group ordinal Banzhaf scores s_T for coalitions T.

    定義に従い、各 T ⊆ N について
      m_T^S(≽) = 1  if S ∪ T ≻ S
                = -1 if S ≻ S ∪ T
                = 0  otherwise,
    とし、
      u_T^+ = |{S | m_T^S = 1}|
      u_T^- = |{S | m_T^S = -1}|
      s_T    = u_T^+ - u_T^-.
    を計算する。
    """
    if game.ranks is None:
        msg = "Game.ranks must be defined for group ordinal Banzhaf."
        raise ValueError(msg)

    ranks = game.ranks
    players = list(game.players)
    n = len(players)

    # 対象となる連立 T
    if subsets is None:
        target_subsets: list[Coalition] = [
            frozenset(S)
            for k in range(1, n + 1)
            for S in __import__("itertools").combinations(players, k)
        ]
    else:
        target_subsets = [frozenset(T) for T in subsets]

    # プレイヤー集合を固定
    from itertools import combinations

    scores: dict[Coalition, int] = {}

    for T in target_subsets:
        if not T:
            scores[T] = 0
            continue

        rest = [p for p in players if p not in T]
        u_plus = 0
        u_minus = 0

        for k in range(len(rest) + 1):
            for S_tuple in combinations(rest, k):
                S = frozenset(S_tuple)
                with_T = frozenset(set(S) | set(T))
                if S not in ranks or with_T not in ranks:
                    continue

                r_S = ranks[S]
                r_with = ranks[with_T]

                if r_with < r_S:
                    u_plus += 1
                elif r_S < r_with:
                    u_minus += 1

        scores[T] = u_plus - u_minus

    return scores


@dataclass(frozen=True)
class GroupOrdinalBanzhafRelation:
    """Group ordinal Banzhaf relation on coalitions."""

    scores: Mapping[Coalition, int]
    R: frozenset[tuple[Coalition, Coalition]]


def compute_group_ordinal_banzhaf_relation(
    game: Game,
    subsets: Iterable[Coalition] | None = None,
) -> GroupOrdinalBanzhafRelation:
    """Compute the group ordinal Banzhaf relation over coalitions."""
    scores = compute_group_ordinal_banzhaf_scores(game, subsets=subsets)
    coalitions = list(scores.keys())

    R: set[tuple[Coalition, Coalition]] = set()
    for S in coalitions:
        for T in coalitions:
            if scores[S] >= scores[T]:
                R.add((S, T))

    return GroupOrdinalBanzhafRelation(scores=scores, R=frozenset(R))


@dataclass(frozen=True)
class GroupLexCelRelation:
    """Group lex-cel relation on coalitions.

    Theta: frequency vectors Θ_≽(T) for each coalition (highest layer first).
    P: asymmetric part P^{grp,le}_{≽} as a set of ordered pairs (T, U).
    I: symmetric part I^{grp,le}_{≽} as a set of unordered pairs frozenset({T, U}).
    """

    theta: Mapping[Coalition, Sequence[int]]
    P: frozenset[tuple[Coalition, Coalition]]
    I: frozenset[frozenset[Coalition]]


def compute_group_lex_cel(
    game: Game,
    subsets: Iterable[Coalition] | None = None,
) -> GroupLexCelRelation:
    """Compute group lex-cel relation from coalition ranking.

    For each nonempty coalition T, we build Θ_≽(T) = (T_1, ..., T_ell) where
    T_k = |{ S ∈ Σ_k | T ⊆ S }|, and compare lexicographically.
    """
    if game.ranks is None:
        msg = "Game.ranks must be defined for group lex-cel."
        raise ValueError(msg)

    ranks = game.ranks
    players = list(game.players)

    # Build quotient ranking: layers Σ_1, ..., Σ_ell
    layer_values = sorted({r for r in ranks.values()})
    layers: list[list[Coalition]] = [[] for _ in layer_values]
    value_to_index = {v: idx for idx, v in enumerate(layer_values)}

    for coalition, r in ranks.items():
        idx = value_to_index[r]
        layers[idx].append(coalition)

    # Target coalitions T: nonempty coalitions over N (or restricted subsets)
    from itertools import combinations

    n = len(players)
    if subsets is None:
        target_subsets: list[Coalition] = [
            frozenset(S)
            for k in range(1, n + 1)
            for S in combinations(players, k)
        ]
    else:
        target_subsets = [frozenset(T) for T in subsets if T]

    # Compute frequency vectors Θ(T) = (T_1, ..., T_ell)
    theta: dict[Coalition, list[int]] = {
        T: [0] * len(layers) for T in target_subsets
    }
    for k, coalitions in enumerate(layers):
        for S in coalitions:
            for T in target_subsets:
                if T.issubset(S):
                    theta[T][k] += 1

    # Lexicographic comparison helper
    def _lex_cmp(a: Sequence[int], b: Sequence[int]) -> int:
        for x, y in zip(a, b):
            if x > y:
                return 1
            if x < y:
                return -1
        return 0

    P: set[tuple[Coalition, Coalition]] = set()
    I: set[frozenset[Coalition]] = set()

    for T in target_subsets:
        for U in target_subsets:
            if T == U:
                continue
            cmp = _lex_cmp(theta[T], theta[U])
            if cmp > 0:
                P.add((T, U))
            elif cmp == 0:
                I.add(frozenset({T, U}))

    return GroupLexCelRelation(
        theta={T: tuple(v) for T, v in theta.items()},
        P=frozenset(P),
        I=frozenset(I),
    )
