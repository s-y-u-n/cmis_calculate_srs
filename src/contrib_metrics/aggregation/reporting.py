from __future__ import annotations

from typing import TextIO

import pandas as pd


def print_summary(df: pd.DataFrame, file: TextIO) -> None:
    df.to_markdown(file, index=False)
