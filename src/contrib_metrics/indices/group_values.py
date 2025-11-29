from __future__ import annotations

from typing import Dict, Iterable

from ..model.game import Game


def compute_group_values(game: Game, groups: Iterable[frozenset[int]]) -> Dict[frozenset[int], float]:
    """Placeholder for group value implementations.

    Currently returns zero for all groups. Extend with specific
    group value definitions (e.g., Owen value) as needed.
    """
    return {g: 0.0 for g in groups}
