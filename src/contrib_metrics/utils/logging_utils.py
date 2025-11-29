from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Any, Mapping

import yaml


def configure_logging(config_path: Path | None = None) -> None:
    if config_path is None or not config_path.exists():
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s %(name)s - %(message)s",
        )
        return

    with config_path.open("r", encoding="utf-8") as f:
        config: Mapping[str, Any] = yaml.safe_load(f)
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
