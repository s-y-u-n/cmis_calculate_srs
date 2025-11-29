from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from ..config_loader import load_config
from ..indices.banzhaf import compute_banzhaf
from ..indices.ordinal import (
    GroupLexCelRelation,
    LexCelRelation,
    compute_group_lex_cel,
    compute_group_ordinal_banzhaf_scores,
    compute_lex_cel,
    compute_ordinal_banzhaf_scores,
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
    plot_coalition_values,
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
    axioms_cfg: Mapping[str, Any] = cfg.get("axioms", {})
    swimmy_cfg: Mapping[str, Any] = axioms_cfg.get("swimmy", {})
    swimmy_enabled = swimmy_cfg.get("enabled", False)
    swimmy_rule_filter = swimmy_cfg.get("rules")  # optional list of rule names
    sada_cfg: Mapping[str, Any] = axioms_cfg.get("sada", {})
    sada_enabled = sada_cfg.get("enabled", False)
    sada_rule_filter = sada_cfg.get("rules")  # optional list of rule names

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
    swimmy_counts: dict[str, dict[str, int]] = {}
    sada_counts: dict[str, dict[str, int]] = {}

    interactions_cfg: Mapping[str, Any] = indices_cfg.get("interactions", {})
    interactions_enabled = interactions_cfg.get("enabled", False)
    shapley_interactions_enabled = interactions_cfg.get("shapley", True)
    banzhaf_interactions_enabled = interactions_cfg.get("banzhaf", True)
    group_ordinal_interactions_enabled = interactions_cfg.get(
        "group_ordinal_banzhaf",
        False,
    )
    group_lexcel_interactions_enabled = interactions_cfg.get(
        "group_lex_cel",
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
            group_lex_rel: GroupLexCelRelation | None = None
            group_lex_rank: dict[Coalition, int] | None = None
            group_lex_theta: dict[Coalition, Sequence[int]] | None = None
            if group_lexcel_interactions_enabled:
                try:
                    group_lex_rel = compute_group_lex_cel(game)
                    group_lex_theta = {
                        c: tuple(v) for c, v in group_lex_rel.theta.items()
                    }
                    unique_vecs = sorted(
                        set(group_lex_theta.values()),
                        reverse=True,
                    )
                    vec_to_rank = {
                        vec: idx + 1 for idx, vec in enumerate(unique_vecs)
                    }
                    group_lex_rank = {
                        c: vec_to_rank[group_lex_theta[c]] for c in group_lex_theta
                    }
                except ValueError as exc:
                    logger.warning("group lex-cel requested but not applicable: %s", exc)

            all_coalitions = (
                set(shap_int.keys())
                | set(banz_int.keys())
                | set(group_ord.keys())
                | (set(group_lex_theta.keys()) if group_lex_theta else set())
            )

            def _coalition_to_str(c: frozenset[int]) -> str:
                if not c:
                    return "{}"
                parts = ",".join(str(x) for x in sorted(c))
                return "{" + parts + "}"

            for coalition in all_coalitions:
                theta_str = None
                rank_val = None
                if group_lex_theta is not None and coalition in group_lex_theta:
                    theta_str = ",".join(str(x) for x in group_lex_theta[coalition])
                if group_lex_rank is not None:
                    rank_val = group_lex_rank.get(coalition)

                interaction_rows.append(
                    {
                        "coalition": _coalition_to_str(coalition),
                        "size": len(coalition),
                        "shapley_interaction": shap_int.get(coalition),
                        "banzhaf_interaction": banz_int.get(coalition),
                        "group_ordinal_banzhaf_score": group_ord.get(coalition),
                        "group_lexcel_theta": theta_str,
                        "group_lexcel_rank": rank_val,
                    }
                )

        if (swimmy_enabled or sada_enabled) and game.ranks is not None:
            # 様々なシナジー比較ルールに対して Swimmy Axiom の満足度を集計
            available_rules: dict[str, dict[Coalition, float]] = {}
            if shap_int:
                available_rules["shapley_interaction"] = {
                    c: float(v) for c, v in shap_int.items()
                }
            if banz_int:
                available_rules["banzhaf_interaction"] = {
                    c: float(v) for c, v in banz_int.items()
                }
            if group_ord:
                available_rules["group_ordinal_banzhaf_score"] = {
                    c: float(v) for c, v in group_ord.items()
                }
            if group_lex_rank:
                available_rules["group_lexcel_rank"] = {
                    c: float(v) for c, v in group_lex_rank.items()
                }

            if swimmy_rule_filter:
                available_rules = {
                    name: scores
                    for name, scores in available_rules.items()
                    if name in swimmy_rule_filter
                }

            if swimmy_enabled:
                _update_swimmy_counts(game, available_rules, swimmy_counts)

            if sada_enabled:
                # Synergy–Anasy Distinction 用には、rule のサブセットを選べるようにする
                sada_rules = available_rules
                if sada_rule_filter:
                    sada_rules = {
                        name: scores
                        for name, scores in available_rules.items()
                        if name in sada_rule_filter
                    }
                _update_sada_counts(game, sada_rules, sada_counts)

    result_df = pd.DataFrame(rows)
    interactions_df = pd.DataFrame(interaction_rows)

    # coalition の並び順は coalition の構造に基づく固定順序に統一する
    if not interactions_df.empty:
        if "size" in interactions_df.columns:
            interactions_df = interactions_df.sort_values(
                ["size", "coalition"],
                kind="mergesort",
            )
        else:
            interactions_df = interactions_df.sort_values(
                ["coalition"],
                kind="mergesort",
            )

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
            # 元のゲームテーブル値に基づく coalition スコアの棒グラフ
            value_col = input_cfg.get("value_column", "value")
            if value_col in df.columns:
                # coalition の並び順は interactions_df の coalition 列に合わせる
                order: list[str] | None = None
                if not interactions_df.empty and "coalition" in interactions_df.columns:
                    order = interactions_df["coalition"].astype(str).tolist()
                plot_coalition_values(df, value_col, base_dir, coalition_order=order)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Visualization failed: %s", exc)

    # Swimmy Axiom の集計結果を出力
    if swimmy_enabled and swimmy_counts:
        rows_axiom: list[dict[str, Any]] = []
        for rule_name, cnt in swimmy_counts.items():
            triggered = cnt.get("triggered", 0)
            satisfied = cnt.get("satisfied", 0)
            satisfaction_rate = satisfied / triggered if triggered > 0 else None
            rows_axiom.append(
                {
                    "rule": rule_name,
                    "triggered_pairs": triggered,
                    "satisfied_pairs": satisfied,
                    "satisfaction_rate": satisfaction_rate,
                }
            )
        swimmy_df = pd.DataFrame(rows_axiom)
        axioms_path = base_dir / "axioms_swimmy.csv"
        write_table(swimmy_df, axioms_path, fmt=fmt)
        logger.info("Wrote Swimmy axiom summary to %s", axioms_path)

    if sada_enabled and sada_counts:
        rows_axiom: list[dict[str, Any]] = []
        for rule_name, cnt in sada_counts.items():
            triggered = cnt.get("triggered", 0)
            satisfied = cnt.get("satisfied", 0)
            satisfaction_rate = satisfied / triggered if triggered > 0 else None
            rows_axiom.append(
                {
                    "rule": rule_name,
                    "triggered_pairs": triggered,
                    "satisfied_pairs": satisfied,
                    "satisfaction_rate": satisfaction_rate,
                }
            )
        sada_df = pd.DataFrame(rows_axiom)
        axioms_path = base_dir / "axioms_sada.csv"
        write_table(sada_df, axioms_path, fmt=fmt)
        logger.info("Wrote Synergy–Anasy Distinction summary to %s", axioms_path)


def _update_swimmy_counts(
    game: Game,
    synergy_rules: Mapping[str, Mapping[Coalition, float]],
    counts: dict[str, dict[str, int]],
) -> None:
    """Update Swimmy Axiom satisfaction counts for a single game."""
    ranks = game.ranks
    if ranks is None:
        return

    players = list(game.players)

    # 2 人連立の集合
    two_sets: list[Coalition] = [
        frozenset({i, j}) for i, j in combinations(players, 2)
    ]

    # 比較ヘルパ: 1 if A ≻ B, -1 if A ≺ B, 0 if A ∼ B, None if undefined
    def cmp_coalitions(A: Coalition, B: Coalition) -> int | None:
        rA = ranks.get(A)
        rB = ranks.get(B)
        if rA is None or rB is None:
            return None
        if rA < rB:
            return 1
        if rA > rB:
            return -1
        return 0

    for S in two_sets:
        s_list = sorted(S)
        s1, s2 = s_list[0], s_list[1]
        for T in two_sets:
            if T == S:
                continue
            t_list = sorted(T)
            t1, t2 = t_list[0], t_list[1]

            # antecedent を満たすかどうか
            antecedent_holds = False

            for pi in [(t1, t2), (t2, t1)]:
                t1p, t2p = pi
                c1 = cmp_coalitions(frozenset({s1}), frozenset({t1p}))
                c2 = cmp_coalitions(frozenset({s2}), frozenset({t2p}))
                cS = cmp_coalitions(S, T)
                if c1 is None or c2 is None or cS is None:
                    continue

                ge1 = c1 in (0, 1)  # {s1} ≽ {pi(t1)}
                ge2 = c2 in (0, 1)  # {s2} ≽ {pi(t2)}
                S_pre_T = cS in (0, -1)  # S \precsim T
                strict = (c1 == 1) or (c2 == 1) or (cS == -1)

                if ge1 and ge2 and S_pre_T and strict:
                    antecedent_holds = True
                    break

            if not antecedent_holds:
                continue

            for rule_name, scores in synergy_rules.items():
                vS = scores.get(S)
                vT = scores.get(T)
                if vS is None or vT is None:
                    continue

                # 初期化
                if rule_name not in counts:
                    counts[rule_name] = {"triggered": 0, "satisfied": 0}

                counts[rule_name]["triggered"] += 1

                # rule_name に応じて「T が S より良い」の判定方法を変える
                if rule_name.endswith("_rank"):
                    # rank は小さいほど良い
                    satisfied = vT < vS
                else:
                    # スコアは大きいほど良い
                    satisfied = vT > vS

                if satisfied:
                    counts[rule_name]["satisfied"] += 1


def _update_sada_counts(
    game: Game,
    synergy_rules: Mapping[str, Mapping[Coalition, float]],
    counts: dict[str, dict[str, int]],
) -> None:
    """Update Synergy–Anasy Distinction counts for a single game."""
    ranks = game.ranks
    if ranks is None:
        return

    players = list(game.players)

    # 2 人連立の集合
    two_sets: list[Coalition] = [
        frozenset({i, j}) for i, j in combinations(players, 2)
    ]

    def _synergy_level(T: Coalition) -> int | None:
        """Return synergy level in {1,...,6} or None if undefined."""
        if len(T) != 2:
            return None
        i, j = sorted(T)
        A = frozenset({i})
        B = frozenset({j})
        P = frozenset({i, j})
        rA = ranks.get(A)
        rB = ranks.get(B)
        rP = ranks.get(P)
        if rA is None or rB is None or rP is None:
            return None

        def succeq(X: Coalition, Y: Coalition) -> bool:
            return ranks[X] <= ranks[Y]

        def succ(X: Coalition, Y: Coalition) -> bool:
            return ranks[X] < ranks[Y]

        def sim(X: Coalition, Y: Coalition) -> bool:
            return ranks[X] == ranks[Y]

        # L3: {i,j} ~ {i} ~ {j}
        if sim(P, A) and sim(A, B):
            return 3

        # Patterns with permutation over (i, j)
        for p1, p2 in ((i, j), (j, i)):
            C1 = frozenset({p1})
            C2 = frozenset({p2})

            # L1: exists pi s.t. {pi1,pi2} ≻ {pi1} ∧ {pi1} ≽ {pi2}
            if succ(P, C1) and succeq(C1, C2):
                return 1

            # L2: exists pi s.t. {pi1,pi2} ~ {pi1} ∧ {pi1} ≻ {pi2}
            if sim(P, C1) and succ(C1, C2):
                return 2

            # L4: exists pi s.t. {pi1} ≻ {pi1,pi2} ∧ {pi1,pi2} ≻ {pi2}
            if succ(C1, P) and succ(P, C2):
                return 4

            # L5: exists pi s.t. {pi1} ≻ {pi1,pi2} ∧ {pi1,pi2} ~ {pi2}
            if succ(C1, P) and sim(P, C2):
                return 5

            # L6: exists pi s.t. {pi1} ≽ {pi2} ∧ {pi2} ≻ {pi1,pi2}
            if succeq(C1, C2) and succ(C2, P):
                return 6

        # If nothing matched, treat as undefined
        return None

    # Precompute synergy levels for all 2-person coalitions
    levels: dict[Coalition, int] = {}
    for T in two_sets:
        level = _synergy_level(T)
        if level is not None:
            levels[T] = level

    # Evaluate axiom: for any distinct T, U, if syn(T) < syn(U) then T PI U
    for T in two_sets:
        if T not in levels:
            continue
        for U in two_sets:
            if U == T or U not in levels:
                continue
            if levels[T] >= levels[U]:
                continue

            for rule_name, scores in synergy_rules.items():
                vT = scores.get(T)
                vU = scores.get(U)
                if vT is None or vU is None:
                    continue

                if rule_name not in counts:
                    counts[rule_name] = {"triggered": 0, "satisfied": 0}

                counts[rule_name]["triggered"] += 1

                if rule_name.endswith("_rank"):
                    satisfied = vT < vU  # smaller rank is better
                else:
                    satisfied = vT > vU  # larger score is better

                if satisfied:
                    counts[rule_name]["satisfied"] += 1
