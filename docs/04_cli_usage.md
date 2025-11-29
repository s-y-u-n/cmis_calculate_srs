# CLI 利用方法

## 基本コマンド

Poetry 経由で CLI を実行します。

```bash
poetry run contrib-metrics compute --config config/example_config.yaml
```

- `config/example_config.yaml` は、単一のゲームテーブル（`value` と `rank` を含む）から
  Shapley / Banzhaf / Synergy と lex-cel / ordinal 指標をまとめて計算する例です。
  - `rank` が存在しない場合でも、`input.ranking` セクションの設定に従って
    実行時に `value` から順位を自動生成します。

## 設定ファイル

設定は YAML で記述します（例: `config/example_config.yaml`）。

主なセクション:

- `input`: 入力データのパス・フォーマット・ゲームタイプなど
  - `ranking`: `value` から `rank` を生成する際のオプション
    - `mode`: `dense`（dense ranking）または `bin`（ビン分割してから ranking）
    - `bin_width`: `mode: bin` のときのビン幅（例: 0.01）
    - `descending`: true のとき大きい値ほど良い（rank=1 が最良）
- `indices`: 計算する指標とオプション
- `output`: 結果の出力先
  - `format`: `csv` または `parquet` など
  - `path`: 明示的に指定しない（null のまま）の場合は、
    `input.path` に対して
    `outputs/<inputの親ディレクトリ>/<input_stem>/` を自動生成し、
    そのディレクトリ内に
    - `individuals.<format>`（プレイヤー指標）
    - `coalitions.<format>`（グループ指標: Shapley/Banzhaf interaction）
    を出力する
  - `path` を明示指定した場合は、そのパスをディレクトリとして扱い、
    `individuals.<format>` / `coalitions.<format>` をその中に出力する
- `logging`: ログ設定ファイル

詳細な項目は `config/example_config.yaml` を参照してください。
