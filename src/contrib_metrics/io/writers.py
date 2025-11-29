from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_table(
    df: pd.DataFrame, path: str | Path, fmt: str | None = None
) -> None:
    p = Path(path)
    if fmt is None:
        fmt = p.suffix.lstrip(".").lower()

    if fmt == "csv":
        df.to_csv(p, index=False)
    elif fmt in {"parquet", "pq"}:
        df.to_parquet(p, index=False)
    else:
        msg = f"Unsupported output format: {fmt}"
        raise ValueError(msg)
