from __future__ import annotations

from importlib import resources
from typing import Any, Mapping

import pandas as pd


def validate_game_table(df: pd.DataFrame) -> None:
    """Very lightweight validation for now."""
    required = {"scenario_id", "game_id", "coalition"}
    missing = required - set(df.columns)
    if missing:
        msg = f"Missing required columns: {sorted(missing)}"
        raise ValueError(msg)


def load_schema() -> Mapping[str, Any]:
    """Load JSON schema for game table (for future extensions)."""
    with resources.files("contrib_metrics").joinpath(
        "../../data/schema/game_table_schema.json"
    ).open("r", encoding="utf-8") as f:
        import json

        return json.load(f)
