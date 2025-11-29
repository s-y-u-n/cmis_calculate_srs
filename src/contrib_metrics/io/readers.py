from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ..utils.coalition_encoding import normalize_coalition


def read_game_table(
    path: str | Path,
    fmt: str | None = None,
    coalition_column: str = "coalition",
) -> pd.DataFrame:
    p = Path(path)
    if fmt is None:
        fmt = p.suffix.lstrip(".").lower()

    if fmt == "csv":
        df = pd.read_csv(p)
    elif fmt in {"parquet", "pq"}:
        df = pd.read_parquet(p)
    else:
        msg = f"Unsupported format: {fmt}"
        raise ValueError(msg)

    if coalition_column not in df.columns:
        msg = "Input table must contain 'coalition' column."
        raise ValueError(msg)

    df = df.copy()
    if coalition_column != "coalition":
        df = df.rename(columns={coalition_column: "coalition"})
    df["coalition"] = df["coalition"].map(_normalize_coalition_cell)
    return df


def _normalize_coalition_cell(value: Any) -> frozenset[int]:
    return normalize_coalition(value)
