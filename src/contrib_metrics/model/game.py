from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, Mapping, Optional

from .game_types import GameType


Coalition = FrozenSet[int]


@dataclass
class Game:
    players: list[int]
    coalitions: list[Coalition]
    values: Dict[Coalition, float] = field(default_factory=dict)
    ranks: Optional[Dict[Coalition, int]] = None
    game_type: GameType = GameType.TU

    def value(self, coalition: Iterable[int]) -> float:
        key: Coalition = frozenset(coalition)
        return self.values.get(key, 0.0)

    def rank(self, coalition: Iterable[int]) -> Optional[int]:
        if self.ranks is None:
            return None
        key: Coalition = frozenset(coalition)
        return self.ranks.get(key)

    @classmethod
    def from_mapping(
        cls,
        players: Iterable[int],
        values: Mapping[Coalition, float],
        ranks: Optional[Mapping[Coalition, int]] = None,
        game_type: GameType = GameType.TU,
    ) -> "Game":
        coalitions = list(values.keys())
        return cls(
            players=list(players),
            coalitions=coalitions,
            values=dict(values),
            ranks=dict(ranks) if ranks is not None else None,
            game_type=game_type,
        )
