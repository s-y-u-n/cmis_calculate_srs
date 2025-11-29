from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


def load_config(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = "Configuration file must contain a mapping at top level."
        raise ValueError(msg)
    return data
