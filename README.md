# contribution-metrics

ゲームテーブル（`scenario_id`, `game_id`, `coalition`, `value` または `rank`）を入力として、
Shapley 値や Banzhaf 値など各種貢献度指標を計算する後処理エンジンです。

## 特徴

- 入力形式: CSV / Parquet / SQL からのエクスポート（まずは CSV / Parquet をサポート）
- ゲームテーブルを内部モデル `Game` に変換して計算
- 指標:
  - Shapley 値（厳密 / モンテカルロ）
  - Banzhaf 値
  - Group value（拡張用の雛形）
  - Ordinal 指標（ordinal marginal, ordinal Banzhaf）
  - Synergy / Anasy（拡張可能なクラスベース API）

## 前提

- Python 3.10+
- Poetry を利用したパッケージ管理
- Black / Ruff による整形・Lint を想定

## インストール

```bash
poetry install
```

## 使い方

例: 設定ファイルを指定して一括計算を実行

```bash
poetry run contrib-metrics compute --config config/example_config.yaml
```

詳細な仕様・設計は `docs/` を参照してください。
