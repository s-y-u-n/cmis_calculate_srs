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

    def _bar_plot_rank(column: str, filename: str, ylabel: str) -> None:
        if column not in df.columns:
            return
        values = df[column]
        if values.empty:
            return
        # rank は「小さいほど良い」ので、そのまま棒の高さに使うと
        # 下に良いプレイヤーが来てしまう。そこで、
        #   plot_val = max_rank + 1 - rank
        # として「良いほど棒が高い」ように変換し、
        # 軸の目盛りは元の rank を逆順で表示する。
        max_rank = int(values.max())
        plot_vals = max_rank + 1 - values
        plt.figure(figsize=(8, 4))
        plt.bar(players, plot_vals)
        plt.xlabel("player")
        plt.ylabel(ylabel)
        plt.title(f"{title_prefix}{column}")
        ax = plt.gca()
        ax.set_ylim(0, max_rank + 1)
        # 上に rank=1、下に rank=max_rank が来るように目盛りを配置
        tick_positions = [max_rank + 1 - r for r in range(1, max_rank + 1)]
        ax.set_yticks(tick_positions)
        ax.set_yticklabels([str(r) for r in range(1, max_rank + 1)])
        plt.tight_layout()
        plt.savefig(out_dir / filename)
        plt.close()

    # 値ベースの指標
    _bar_plot("shapley", "individuals_shapley.png", "Shapley value")
    _bar_plot("banzhaf", "individuals_banzhaf.png", "Banzhaf value")

    # ランクベースの指標（値を持たない純粋な ordinal 指標のみ）
    _bar_plot_rank(
        "ordinal_banzhaf_rank",
        "individuals_ordinal_banzhaf_rank.png",
        "Ordinal Banzhaf rank",
    )
    _bar_plot_rank(
        "lex_cel_rank",
        "individuals_lex_cel_rank.png",
        "lex-cel rank",
    )


def plot_coalitions(df: pd.DataFrame, out_dir: Path, title_prefix: str = "") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if "coalition" not in df.columns:
        return

    # 並び順は run_manager 側で既にソート済みの DataFrame に従う
    plot_df = df.copy()
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

    def _bar_plot_rank(column: str, filename: str, ylabel: str) -> None:
        if column not in plot_df.columns:
            return
        values = plot_df[column]
        if values.empty:
            return
        max_rank = int(values.max())
        plot_vals = max_rank + 1 - values
        plt.figure(figsize=(max(8, len(coalitions) * 0.4), 4))
        plt.bar(range(len(coalitions)), plot_vals)
        plt.xticks(range(len(coalitions)), coalitions, rotation=90)
        plt.ylabel(ylabel)
        plt.title(f"{title_prefix}{column}")
        ax = plt.gca()
        ax.set_ylim(0, max_rank + 1)
        tick_positions = [max_rank + 1 - r for r in range(1, max_rank + 1)]
        ax.set_yticks(tick_positions)
        ax.set_yticklabels([str(r) for r in range(1, max_rank + 1)])
        plt.tight_layout()
        plt.savefig(out_dir / filename)
        plt.close()

    _bar_plot("shapley_interaction", "coalitions_shapley_interaction.png", "Shapley interaction")
    _bar_plot("banzhaf_interaction", "coalitions_banzhaf_interaction.png", "Banzhaf interaction")
    _bar_plot("borda_interaction", "coalitions_borda_interaction.png", "Borda interaction")
    _bar_plot(
        "group_ordinal_banzhaf_score",
        "coalitions_group_ordinal_banzhaf_score.png",
        "Group Ordinal Banzhaf score",
    )
    _bar_plot_rank(
        "group_lexcel_rank",
        "coalitions_group_lexcel_rank.png",
        "Group lex-cel rank",
    )


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


def plot_interaction_heatmap(
    df: pd.DataFrame,
    out_dir: Path,
    title: str = "Interaction correlation (Spearman)",
    columns: List[str] | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    if columns is None:
        # 代表的な interaction / group-ordinal 系の列
        candidates = [
            "shapley_interaction",
            "banzhaf_interaction",
            "borda_interaction",
            "group_ordinal_banzhaf_score",
            "group_lexcel_rank",
        ]
        columns = [c for c in candidates if c in df.columns]

    columns = [c for c in columns if c in df.columns]
    if len(columns) < 2:
        return

    data = df[columns].copy()
    if data.empty:
        return

    # スコアではなく rank 単位で比較するため、列ごとに rank 変換してから
    # 相関を計算する（Spearman 相関と同値）。
    ranked = pd.DataFrame(index=data.index)
    for col in columns:
        s = data[col]
        if col.endswith("_rank"):
            ranked[col] = s
        else:
            # 大きいスコアほど良いとみなし dense ranking（1 が最大）を付与
            ranked[col] = s.rank(method="dense", ascending=False)

    corr = ranked.corr(method="pearson")

    plt.figure(figsize=(4 + len(columns), 4 + len(columns)))
    im = plt.imshow(corr.values, vmin=-1, vmax=1, cmap="coolwarm", origin="lower")
    plt.colorbar(im, fraction=0.046, pad=0.04)

    tick_positions = range(len(columns))
    plt.xticks(tick_positions, columns, rotation=45, ha="right")
    plt.yticks(tick_positions, columns)
    plt.title(title)

    for i in range(len(columns)):
        for j in range(len(columns)):
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
    plt.savefig(out_dir / "coalitions_interaction_heatmap.png")
    plt.close()


def plot_coalition_values(
    df: pd.DataFrame,
    value_column: str,
    out_dir: Path,
    title_prefix: str = "",
    coalition_order: List[str] | None = None,
) -> None:
    """Bar plot of original game-table values per coalition."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if "coalition" not in df.columns or value_column not in df.columns:
        return

    # coalition が frozenset の想定。文字列に整形し、同じ coalition が複数行ある場合は平均をとる。
    def _coalition_to_str(c: object) -> str:
        if isinstance(c, frozenset):
            if not c:
                return "{}"
            parts = ",".join(str(x) for x in sorted(c))
            return "{" + parts + "}"
        return str(c)

    plot_df = df.copy()
    plot_df["coal_str"] = plot_df["coalition"].map(_coalition_to_str)
    agg = plot_df.groupby("coal_str", as_index=False)[value_column].mean()

    if coalition_order is not None:
        # interactions_df の coalition 順に並べたい場合
        agg = agg[agg["coal_str"].isin(coalition_order)]
        agg = agg.set_index("coal_str").reindex(coalition_order).reset_index()
    else:
        agg = agg.sort_values("coal_str")

    if agg.empty:
        return

    coalitions = agg["coal_str"].astype(str)
    values = agg[value_column]

    plt.figure(figsize=(max(8, len(coalitions) * 0.4), 4))
    plt.bar(range(len(coalitions)), values)
    plt.xticks(range(len(coalitions)), coalitions, rotation=90)
    plt.ylabel(value_column)
    plt.title(f"{title_prefix}{value_column}")
    plt.tight_layout()
    plt.savefig(out_dir / "coalitions_value.png")
    plt.close()
