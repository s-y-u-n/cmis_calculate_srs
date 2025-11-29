from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import shutil
import yaml


@dataclass
class GameTableRun:
    kind: str
    run_id: int
    path: Path
    format: str
    created_at: datetime
    metadata_path: Optional[Path]


def _kind_root(root: Path | str, kind: str) -> Path:
    return Path(root) / kind


def list_runs(kind: str, root: Path | str = Path("data/game_tables")) -> List[GameTableRun]:
    """List all runs for a given game-table kind.

    サポートするレイアウト:
    - data/game_tables/<kind>/<kind>_NNN.csv 形式の「生ファイル」
    - data/game_tables/<kind>/run_NNNN/{game_table.csv, metadata.yaml} 形式の登録済みファイル
    """
    base = _kind_root(root, kind)
    if not base.exists():
        return []

    runs: list[GameTableRun] = []

    # 1) Simple layout: kind/kind_001.csv, kind_002.csv, ...
    for entry in sorted(base.iterdir()):
        if not entry.is_file():
            continue
        name = entry.name
        stem = entry.stem
        if not stem.startswith(f"{kind}_"):
            continue
        suffix = stem.split("_", 1)[1]
        try:
            run_id = int(suffix)
        except ValueError:
            continue
        fmt = entry.suffix.lstrip(".").lower()
        created_at = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
        runs.append(
            GameTableRun(
                kind=kind,
                run_id=run_id,
                path=entry,
                format=fmt,
                created_at=created_at,
                metadata_path=None,
            )
        )

    # 2) Managed layout: kind/run_0001/..., with metadata.yaml
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if not name.startswith("run_"):
            continue
        try:
            run_id = int(name.split("_", 1)[1])
        except ValueError:
            continue

        meta_path = entry / "metadata.yaml"
        if not meta_path.exists():
            continue

        with meta_path.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        fmt = str(meta.get("format", "") or "")
        filename = meta.get("filename", "game_table.csv")
        table_path = entry / filename

        created_raw = meta.get("created_at")
        if isinstance(created_raw, str):
            try:
                created_at = datetime.fromisoformat(created_raw)
            except ValueError:
                created_at = datetime.now(timezone.utc)
        else:
            created_at = datetime.now(timezone.utc)

        runs.append(
            GameTableRun(
                kind=kind,
                run_id=run_id,
                path=table_path,
                format=fmt,
                created_at=created_at,
                metadata_path=meta_path,
            )
        )

    runs.sort(key=lambda r: r.run_id)
    return runs


def get_latest_run(kind: str, root: Path | str = Path("data/game_tables")) -> Optional[GameTableRun]:
    """Return the latest (highest run_id) run for the given kind."""
    runs = list_runs(kind=kind, root=root)
    if not runs:
        return None
    return runs[-1]


def register_game_table(
    kind: str,
    src: Path | str,
    root: Path | str = Path("data/game_tables"),
    fmt: str | None = None,
    note: str | None = None,
    copy: bool = True,
) -> GameTableRun:
    """Register a new game table run under a given kind.

    data/game_tables/<kind>/run_xxxx にディレクトリを作成し、
    ソースファイルをコピーして metadata.yaml を生成する。
    既存の簡易レイアウト（<kind>_NNN.csv）とは独立して利用できる。
    """
    root_path = Path(root)
    kind_dir = _kind_root(root_path, kind)
    kind_dir.mkdir(parents=True, exist_ok=True)

    existing = list_runs(kind=kind, root=root_path)
    next_id = existing[-1].run_id + 1 if existing else 1

    run_dir = kind_dir / f"run_{next_id:04d}"
    run_dir.mkdir()

    src_path = Path(src)
    if fmt is None:
        fmt = src_path.suffix.lstrip(".").lower()
    filename = f"game_table.{fmt}" if copy else src_path.name
    dest = run_dir / filename if copy else src_path

    if copy:
        shutil.copy2(src_path, dest)

    created_at = datetime.now(timezone.utc)
    meta = {
        "kind": kind,
        "run_id": next_id,
        "format": fmt,
        "filename": dest.name,
        "source_path": str(src_path),
        "copied": copy,
        "created_at": created_at.isoformat(),
    }
    if note:
        meta["note"] = note

    metadata_path = run_dir / "metadata.yaml"
    with metadata_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(meta, f, sort_keys=False)

    return GameTableRun(
        kind=kind,
        run_id=next_id,
        path=dest,
        format=fmt,
        created_at=created_at,
        metadata_path=metadata_path,
    )
