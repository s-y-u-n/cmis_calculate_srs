# 内部モデル設計

## Game オブジェクト

`contrib_metrics.model.game.Game` は 1 つのゲームインスタンスを表現します。

- `players: list[int]`
- `coalitions: list[frozenset[int]]`
- `values: dict[frozenset[int], float]`
- `ranks: dict[frozenset[int], int] | None`
- `game_type: GameType` (`TU`, `ORDINAL` など)

主なメソッド:

- `value(S)`: 連立 `S` の値を返す（未定義の場合は 0.0）
- `rank(S)`: 連立 `S` の順位を返す（未定義の場合は None）

同じ `Game` オブジェクトの中で、cardinal な情報（`values`）と ordinal な情報（`ranks`）の
両方を持つことができます。
Shapley や Banzhaf などの cardinal 指標は `values` を用い、
lex-cel などの ordinal 指標は `ranks` を用いて計算します。

## game_table からの変換

`contrib_metrics.model.transforms` で以下を提供します。

- `build_games_from_table(df, game_type) -> list[Game]`
  - `scenario_id`, `game_id` 単位でグルーピング
  - `coalition` カラムは `frozenset[int]` に正規化済みを前提
  - `value` / `rank` を `Game.values` / `Game.ranks` に反映

また、`add_rank_from_value(df, ...) -> pd.DataFrame` によって
同一のゲームテーブル内に `rank` カラムを追加し、coalition レベルの ordinal 情報を生成します。

これにより、IO 層はテーブル形式、モデル層はオブジェクト指向の API を提供します。
