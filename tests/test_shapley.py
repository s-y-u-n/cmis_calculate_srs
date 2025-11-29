from __future__ import annotations

from contrib_metrics.indices.shapley import compute_shapley_exact
from contrib_metrics.model.game import Game
from contrib_metrics.model.game_types import GameType


def test_shapley_additive_game() -> None:
    # v(S) = sum_{i in S} 1  -> Shapley = 1 for all players
    players = [1, 2, 3]
    coalitions = []
    values = {}
    for mask in range(1 << len(players)):
        s = frozenset(p for i, p in enumerate(players) if mask & (1 << i))
        coalitions.append(s)
        values[s] = float(len(s))

    game = Game(
        players=players,
        coalitions=coalitions,
        values=values,
        game_type=GameType.TU,
    )

    phi = compute_shapley_exact(game)
    assert all(abs(phi[p] - 1.0) < 1e-9 for p in players)
