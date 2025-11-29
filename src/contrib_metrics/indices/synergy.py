from __future__ import annotations

from typing import Dict, Iterable

from ..model.game import Coalition, Game


def compute_synergy(game: Game) -> Dict[Coalition, float]:
    base_singletons = {frozenset({i}): game.value({i}) for i in game.players}
    result: dict[Coalition, float] = {}
    for coalition in game.coalitions:
        if not coalition:
            result[coalition] = 0.0
            continue
        v_s = game.value(coalition)
        singles_sum = sum(base_singletons.get(frozenset({i}), 0.0) for i in coalition)
        result[coalition] = v_s - singles_sum
    return result


class SynergyCalculator:
    def __init__(self) -> None:
        ...

    def compute(self, game: Game) -> Dict[Coalition, float]:
        return compute_synergy(game)
