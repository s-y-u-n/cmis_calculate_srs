from __future__ import annotations

from typing import Iterable, List

import pandas as pd

from .game import Coalition, Game
from .game_types import GameType


def build_games_from_table(
    df: pd.DataFrame,
    game_type: GameType,
    scenario_column: str = "scenario_id",
    game_column: str = "game_id",
    value_column: str = "value",
    rank_column: str = "rank",
) -> List[Game]:
    games: list[Game] = []

    group_cols: list[str] = [scenario_column, game_column]
    for _, g in df.groupby(group_cols):
        coalitions: list[Coalition] = list(g["coalition"])
        players = _infer_players_from_coalitions(coalitions)

        values = {}
        ranks = {}
        has_value = value_column in g.columns
        has_rank = rank_column in g.columns

        for _, row in g.iterrows():
            c = row["coalition"]
            if has_value and not pd.isna(row[value_column]):
                values[c] = float(row[value_column])
            if has_rank and not pd.isna(row[rank_column]):
                ranks[c] = int(row[rank_column])

        ranks_dict = ranks if ranks else None
        game = Game(
            players=sorted(players),
            coalitions=coalitions,
            values=values,
            ranks=ranks_dict,
            game_type=game_type,
        )
        games.append(game)

    return games


def _infer_players_from_coalitions(coalitions: Iterable[Coalition]) -> set[int]:
    players: set[int] = set()
    for c in coalitions:
        players.update(c)
    return players


def add_rank_from_value(
    df: pd.DataFrame,
    scenario_column: str = "scenario_id",
    game_column: str = "game_id",
    value_column: str = "value",
    rank_column: str = "rank",
    method: str = "dense",
    bin_width: float | None = None,
    descending: bool = True,
) -> pd.DataFrame:
    """Add an ordinal rank column derived from numeric values.

    For each (scenario, game) group, coalitions are ranked by ``value_column``.

    - method == \"dense\":
        larger values get better (smaller) ranks, ties share the same rank
        (dense ranking).
    - method == \"bin\":
        values are first discretized into buckets of width ``bin_width`` and
        then dense-ranked by bucket (e.g., 0.01 の幅で階級づけするなど)。
    """
    if value_column not in df.columns:
        msg = f"Column '{value_column}' not found for ranking."
        raise ValueError(msg)

    group_cols: list[str] = [scenario_column, game_column]
    if any(col not in df.columns for col in group_cols):
        msg = f"Columns {group_cols} must be present to compute ranks."
        raise ValueError(msg)

    work = df.copy()
    target_col = value_column

    method_normalized = method.lower()
    if method_normalized == "bin":
        if bin_width is None or bin_width <= 0:
            msg = "bin_width must be positive when method='bin'."
            raise ValueError(msg)
        # Discretize values into integer buckets before ranking.
        work["_bucket_for_rank"] = (work[value_column] / bin_width).floordiv(1)
        target_col = "_bucket_for_rank"
    elif method_normalized != "dense":
        msg = f"Unknown ranking method: {method}"
        raise ValueError(msg)

    ranks = (
        work.groupby(group_cols)[target_col]
        .rank(method="dense", ascending=not descending)
        .astype("Int64")
    )

    result = df.copy()
    result[rank_column] = ranks
    return result
