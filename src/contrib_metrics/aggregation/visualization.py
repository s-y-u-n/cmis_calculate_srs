from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import matplotlib.pyplot as plt
import pandas as pd


def plot_individuals(df: pd.DataFrame, out_dir: Path, title_prefix: str = "") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if "player" not in df.columns:
        return

    players = df["player"].astype(str)

    def _bar_plot(column: str, filename: str, ylabel: str) -> None:
        if column not in df.columns:
            return
        values = df[column]
        plt.figure(figsize=(8, 4))
        plt.bar(players, values)
        plt.xlabel("player")
        plt.ylabel(ylabel)
        plt.title(f"{title_prefix}{column}")
        plt.tight_layout()
        plt.savefig(out_dir / filename)
        plt.close()

    _bar_plot("shapley", "individuals_shapley.png", "Shapley value")
    _bar_plot("banzhaf", "individuals_banzhaf.png", "Banzhaf value")


def plot_coalitions(df: pd.DataFrame, out_dir: Path, title_prefix: str = "") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if "coalition" not in df.columns:
        return

    # Sort by size then by interaction
    plot_df = df.copy()
    if "size" in plot_df.columns:
        plot_df = plot_df.sort_values(["size", "coalition"])

    coalitions = plot_df["coalition"].astype(str)

    def _bar_plot(column: str, filename: str, ylabel: str) -> None:
        if column not in plot_df.columns:
            return
        values = plot_df[column]
        plt.figure(figsize=(max(8, len(coalitions) * 0.4), 4))
        plt.bar(range(len(coalitions)), values)
        plt.xticks(range(len(coalitions)), coalitions, rotation=90)
        plt.ylabel(ylabel)
        plt.title(f"{title_prefix}{column}")
        plt.tight_layout()
        plt.savefig(out_dir / filename)
        plt.close()

    _bar_plot("shapley_interaction", "coalitions_shapley_interaction.png", "Shapley interaction")
    _bar_plot("banzhaf_interaction", "coalitions_banzhaf_interaction.png", "Banzhaf interaction")


def plot_rank_heatmap(
    df: pd.DataFrame,
    out_dir: Path,
    title: str = "Rank correlation (Spearman)",
    rank_columns: List[str] | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    if rank_columns is None:
        rank_columns = [c for c in df.columns if c.endswith("_rank")]

    # 必要なランキング列が 2 つ未満ならスキップ
    rank_columns = [c for c in rank_columns if c in df.columns]
    if len(rank_columns) < 2:
        return

    data = df[rank_columns].copy()
    if data.empty:
        return

    corr = data.corr(method="spearman")

    plt.figure(figsize=(4 + len(rank_columns), 4 + len(rank_columns)))
    # origin=\"lower\" で縦方向を「下から上」に統一
    im = plt.imshow(corr.values, vmin=-1, vmax=1, cmap="coolwarm", origin="lower")
    plt.colorbar(im, fraction=0.046, pad=0.04)

    tick_positions = range(len(rank_columns))
    plt.xticks(tick_positions, rank_columns, rotation=45, ha="right")
    plt.yticks(tick_positions, rank_columns)
    plt.title(title)

    # セルに相関係数を表示
    for i in range(len(rank_columns)):
        for j in range(len(rank_columns)):
            val = corr.values[i, j]
            plt.text(
                j,
                i,
                f"{val:.2f}",
                ha="center",
                va="center",
                color="black" if abs(val) < 0.6 else "white",
            )

    plt.tight_layout()
    plt.savefig(out_dir / "individuals_rank_heatmap.png")
    plt.close()
