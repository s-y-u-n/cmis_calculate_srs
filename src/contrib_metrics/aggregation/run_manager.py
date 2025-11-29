from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ..config_loader import load_config
from ..indices.banzhaf import compute_banzhaf
from ..indices.ordinal import (
    LexCelRelation,
    compute_lex_cel,
    compute_ordinal_banzhaf_scores,
    compute_group_ordinal_banzhaf_scores,
)
from ..indices.interactions import (
    compute_banzhaf_interaction,
    compute_shapley_interaction,
)
from ..indices.shapley import compute_shapley_exact, compute_shapley_mc
from ..indices.synergy import compute_synergy
from ..io.readers import read_game_table
from ..io.validators import validate_game_table
from ..io.writers import write_table
from ..model.game_types import GameType
from ..model.transforms import add_rank_from_value, build_games_from_table
from ..utils.logging_utils import get_logger
from .visualization import (
    plot_coalitions,
    plot_individuals,
    plot_interaction_heatmap,
    plot_rank_heatmap,
)

logger = get_logger(__name__)


def run_from_config(config_path: Path) -> None:
    cfg = load_config(config_path)
    input_cfg: Mapping[str, Any] = cfg.get("input", {})
    indices_cfg: Mapping[str, Any] = cfg.get("indices", {})
    output_cfg: Mapping[str, Any] = cfg.get("output", {})

    df = read_game_table(
        input_cfg["path"],
        fmt=input_cfg.get("format"),
        coalition_column=input_cfg.get("coalition_column", "coalition"),
    )

    # Fill missing scenario/game columns with defaults if absent
    scenario_col = input_cfg.get("scenario_column", "scenario_id")
    game_col = input_cfg.get("game_column", "game_id")
    if scenario_col not in df.columns:
        df[scenario_col] = 0
    if game_col not in df.columns:
        df[game_col] = 0

    # Optionally derive coalition ranks from values.
    ranking_cfg: Mapping[str, Any] = input_cfg.get("ranking", {})  # type: ignore[assignment]
    mode = str(ranking_cfg.get("mode", "dense")).lower()
    if mode != "none":
        df = add_rank_from_value(
            df,
            scenario_column=scenario_col,
            game_column=game_col,
            value_column=input_cfg.get("value_column", "value"),
            rank_column=input_cfg.get("rank_column", "rank"),
            method=mode,
            bin_width=ranking_cfg.get("bin_width"),
            descending=ranking_cfg.get("descending", True),
        )

    game_type = GameType[input_cfg.get("game_type", "TU")]

    validate_game_table(df)

    games = build_games_from_table(
        df,
        game_type=game_type,
        scenario_column=scenario_col,
        game_column=game_col,
        value_column=input_cfg.get("value_column", "value"),
        rank_column=input_cfg.get("rank_column", "rank"),
        players_override=input_cfg.get("players"),
    )

    rows: list[dict[str, Any]] = []
    interaction_rows: list[dict[str, Any]] = []

    interactions_cfg: Mapping[str, Any] = indices_cfg.get("interactions", {})
    interactions_enabled = interactions_cfg.get("enabled", False)
    shapley_interactions_enabled = interactions_cfg.get("shapley", True)
    banzhaf_interactions_enabled = interactions_cfg.get("banzhaf", True)
    group_ordinal_interactions_enabled = interactions_cfg.get(
        "group_ordinal_banzhaf",
        False,
    )
    for game in games:
        shap_cfg = indices_cfg.get("shapley", {})
        banz_cfg = indices_cfg.get("banzhaf", {})
        syn_cfg = indices_cfg.get("synergy", {})
        ord_cfg = indices_cfg.get("ordinal", {})
        lex_cfg = indices_cfg.get("lex_cel", {})

        shapley: dict[int, float] = {}
        if shap_cfg.get("exact", True):
            shapley = compute_shapley_exact(game)
        else:
            mc_samples = int(shap_cfg.get("monte_carlo_samples", 1000))
            shapley = compute_shapley_mc(game, num_samples=mc_samples)

        banzhaf = {}
        if banz_cfg.get("enabled", True):
            banzhaf = compute_banzhaf(game, normalize=banz_cfg.get("normalize", True))

        synergy = {}
        if syn_cfg.get("enabled", True):
            synergy = compute_synergy(game)

        # Player-level rankings based on cardinal indices (dense ranking).
        def _rank_values(values: dict[int, float]) -> dict[int, int]:
            if not values:
                return {}
            unique_vals = sorted(set(values.values()), reverse=True)
            val_to_rank = {v: idx + 1 for idx, v in enumerate(unique_vals)}
            return {pid: val_to_rank[v] for pid, v in values.items()}

        shapley_rank: dict[int, int] | None = None
        if shapley:
            shapley_rank = _rank_values(shapley)

        banzhaf_rank: dict[int, int] | None = None
        if banzhaf:
            banzhaf_rank = _rank_values(banzhaf)

        lex_rel: LexCelRelation | None = None
        lex_ranks: dict[int, int] | None = None
        if lex_cfg.get("enabled", False):
            try:
                lex_rel = compute_lex_cel(game)
                # Build rank (layer) from frequency vectors: higher is better.
                unique_vectors = sorted(
                    {tuple(v) for v in lex_rel.theta.values()},
                    reverse=True,
                )
                vec_to_rank = {
                    vec: idx + 1 for idx, vec in enumerate(unique_vectors)
                }
                lex_ranks = {
                    pid: vec_to_rank[tuple(lex_rel.theta[pid])]
                    for pid in game.players
                    if pid in lex_rel.theta
                }
            except ValueError as exc:
                logger.warning("lex-cel requested but not applicable: %s", exc)

        ordinal_scores: dict[int, int] | None = None
        ordinal_rank: dict[int, int] | None = None
        if ord_cfg.get("enabled", False):
            try:
                ordinal_scores = compute_ordinal_banzhaf_scores(game)
                if ordinal_scores:
                    # Reuse ranking helper; larger score is better.
                    ordinal_rank = _rank_values(
                        {pid: float(s) for pid, s in ordinal_scores.items()}
                    )
            except ValueError as exc:
                logger.warning("ordinal Banzhaf requested but not applicable: %s", exc)

        for pid in game.players:
            row: dict[str, Any] = {
                "player": pid,
                "shapley": shapley.get(pid),
                "banzhaf": banzhaf.get(pid),
            }
            if shapley_rank is not None:
                row["shapley_rank"] = shapley_rank.get(pid)
            if banzhaf_rank is not None:
                row["banzhaf_rank"] = banzhaf_rank.get(pid)
            if ordinal_scores is not None:
                row["ordinal_banzhaf_score"] = ordinal_scores.get(pid)
            if ordinal_rank is not None:
                row["ordinal_banzhaf_rank"] = ordinal_rank.get(pid)
            if lex_rel is not None:
                theta = lex_rel.theta.get(pid)
                row["lex_cel_theta"] = (
                    ",".join(str(x) for x in theta) if theta is not None else None
                )
                if lex_ranks is not None:
                    row["lex_cel_rank"] = lex_ranks.get(pid)
            rows.append(row)

        logger.info(
            "Processed game with %d players and %d coalitions",
            len(game.players),
            len(game.coalitions),
        )

        if interactions_enabled:
            shap_int = (
                compute_shapley_interaction(game)
                if shapley_interactions_enabled
                else {}
            )
            banz_int = (
                compute_banzhaf_interaction(game)
                if banzhaf_interactions_enabled
                else {}
            )
            group_ord = (
                compute_group_ordinal_banzhaf_scores(game)
                if group_ordinal_interactions_enabled
                else {}
            )

            all_coalitions = (
                set(shap_int.keys()) | set(banz_int.keys()) | set(group_ord.keys())
            )

            def _coalition_to_str(c: frozenset[int]) -> str:
                if not c:
                    return "{}"
                parts = ",".join(str(x) for x in sorted(c))
                return "{" + parts + "}"

            for coalition in all_coalitions:
                interaction_rows.append(
                    {
                        "coalition": _coalition_to_str(coalition),
                        "size": len(coalition),
                        "shapley_interaction": shap_int.get(coalition),
                        "banzhaf_interaction": banz_int.get(coalition),
                        "group_ordinal_banzhaf_score": group_ord.get(coalition),
                    }
                )

    result_df = pd.DataFrame(rows)
    interactions_df = pd.DataFrame(interaction_rows)

    fmt = str(output_cfg.get("format", "csv"))
    raw_out_path = output_cfg.get("path")

    src_path = Path(input_cfg["path"])
    if raw_out_path is None:
        # Default: outputs/<input_parent>/<input_stem>/ にまとめて出力
        try:
            rel = src_path.relative_to(Path.cwd())
        except ValueError:
            rel = src_path
        base_dir = Path("outputs") / rel.parent / src_path.stem
    else:
        # path が指定されている場合は、そのパスをディレクトリとみなす
        base_dir = Path(str(raw_out_path))

    base_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = base_dir / f"individuals.{fmt}"
    interactions_path = base_dir / f"coalitions.{fmt}"

    if result_df.empty:
        logger.warning("No player-level results produced.")
    else:
        write_table(result_df, metrics_path, fmt=fmt)
        logger.info("Wrote metrics table to %s", metrics_path)

    if not interactions_df.empty:
        # coalition カラムは既に "{1,2}" 形式の文字列なので、そのまま保存
        write_table(interactions_df, interactions_path, fmt=fmt)
        logger.info("Wrote interaction table to %s", interactions_path)

    # Visualization (enabled by default)
    viz_cfg: Mapping[str, Any] = cfg.get("visualization", {})
    viz_enabled = viz_cfg.get("enabled", True)
    if viz_enabled:
        try:
            if not result_df.empty:
                plot_individuals(result_df, base_dir)
                plot_rank_heatmap(result_df, base_dir)
            if not interactions_df.empty:
                plot_coalitions(interactions_df, base_dir)
                plot_interaction_heatmap(interactions_df, base_dir)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Visualization failed: %s", exc)
