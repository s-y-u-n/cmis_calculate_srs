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
  - `players`: プレイヤーIDを明示的に指定したい場合のリスト（例: `[0,1,2,3]`）。  
    入力テーブルに全プレイヤーが登場しないケースでも、ここに指定すれば計算対象に含められる。
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
- `axioms`: 公理レベルのメタ評価の設定
  - `swimmy`:
    - `enabled`: true のとき Swimmy Axiom に関する満足度を集計
    - `rules`: 対象とするシナジー比較ルール名のリスト  
      （例: `shapley_interaction`, `banzhaf_interaction`, `group_ordinal_banzhaf_score`, `group_lexcel_rank`）
  - `sada`:
    - `enabled`: true のとき Synergy–Anasy Distinction Axiom に関する満足度を集計
    - `rules`: 対象とするシナジー比較ルール名のリスト（指定しない場合は利用可能なものすべて）
- `logging`: ログ設定ファイル

## 可視化（デフォルト ON）

`compute` 実行時には、結果テーブルと同じディレクトリに簡易な可視化も自動出力されます。

- プレイヤー指標 (`individuals.<format>`) に対して:
  - `individuals_shapley.png`: Shapley 値の棒グラフ
  - `individuals_banzhaf.png`: Banzhaf 値の棒グラフ
  - `individuals_ordinal_banzhaf_rank.png`: ordinal Banzhaf ランクの棒グラフ
  - `individuals_lex_cel_rank.png`: lex-cel ランクの棒グラフ
  - `individuals_rank_heatmap.png`:  
    `*_rank` カラム（例: `shapley_rank`, `banzhaf_rank`, `ordinal_banzhaf_rank`, `lex_cel_rank`）同士の
    Spearman 相関行列のヒートマップ（全組み合わせのランキング比較）
- 連立指標 (`coalitions.<format>`) に対して:
  - `coalitions_shapley_interaction.png`: 連立ごとの Shapley interaction の棒グラフ
  - `coalitions_banzhaf_interaction.png`: 連立ごとの Banzhaf interaction の棒グラフ
  - `coalitions_group_ordinal_banzhaf_score.png`: 連立ごとの Group Ordinal Banzhaf スコアの棒グラフ
  - `coalitions_group_lexcel_rank.png`: 連立ごとの Group lex-cel ランクの棒グラフ
  - `coalitions_value.png`: 元のゲームテーブルの value（`value_column`）に基づく連立スコアの棒グラフ
  - `coalitions_interaction_heatmap.png`:  
    `shapley_interaction`, `banzhaf_interaction`, `group_ordinal_banzhaf_score`, `group_lexcel_rank`
    を rank ベースに変換したもの同士の相関行列ヒートマップ（interaction / group-ordinal 系指標の比較）

可視化を無効化したい場合は、設定ファイルに:

```yaml
visualization:
  enabled: false
```

を追加してください。

詳細な項目は `config/example_config.yaml` を参照してください。

## 公理レベルのメタ評価（Swimmy / Synergy–Anasy）

`axioms.swimmy.enabled: true` の場合、各ゲームについて:

- 2 人連立のペア \((S,T)\) のうち、Swimmy Axiom の前件を満たすものを「チェック対象」とし、
- 指定された各シナジー比較ルール（例: Shapley interaction, Banzhaf interaction, Group Ordinal Banzhaf, Group lex-cel）について
  - `triggered_pairs`: 前件を満たしたペア数
  - `satisfied_pairs`: さらに後件も満たしたペア数
  - `satisfaction_rate`: `satisfied_pairs / triggered_pairs`

を集計し、ゲームごとの出力ディレクトリに `axioms_swimmy.csv` として保存します。

`axioms.sada.enabled: true` の場合、Synergy–Anasy Distinction Axiom についても同様に:

- 各 2 人連立 \(T=\{i,j\}\) のシナジーレベル \(\mathrm{syn}_{\succeq}(T)\in\{1,\ldots,6\}\) を rank から計算し、
- 2 つの連立 \(T, U\) に対して \(\mathrm{syn}_{\succeq}(T) < \mathrm{syn}_{\succeq}(U)\) であれば
  指定されたシナジー比較ルール \(R^I\) について `T` が `U` より strictly interaction-better になっているかどうかをチェックし、
- ルールごとに `triggered_pairs`, `satisfied_pairs`, `satisfaction_rate` を集計します。

結果は `axioms_sada.csv` に出力されます。
