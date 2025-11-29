from __future__ import annotations

import pandas as pd


def summarize_indices(df: pd.DataFrame) -> pd.DataFrame:
    if "player" not in df.columns:
        msg = "Input must contain 'player' column."
        raise ValueError(msg)
    return df.groupby("player").mean(numeric_only=True).reset_index()
