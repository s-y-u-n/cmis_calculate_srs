# ゲームテーブル管理

## 目的

同じゲームクラス（例: Buldyrev, NK, 港湾物流など）でも、パラメータやシナリオを変えて
複数回ゲームテーブルを生成することがあります。
このとき、

- ゲームクラスごとにディレクトリを分ける
- 1 回目, 2 回目, ... の生成結果を「ラン番号」で管理する

ための簡易的な管理レイヤーを提供します。

## ディレクトリ構造

標準的な配置は次のようになります。

```text
data/
  game_tables/
    buldyrev/
      run_0001/
        game_table.csv
        metadata.yaml
      run_0002/
        game_table.csv
        metadata.yaml
    nk_model/
      run_0001/
        game_table.parquet
        metadata.yaml
    port_logistics/
      run_0001/
        game_table.csv
        metadata.yaml
```

- `game_tables/` 以下の 1 階層目のディレクトリ名（例: `buldyrev`）を **ゲームテーブル種別（kind）** と呼びます。
- その配下に `run_0001`, `run_0002`, ... のように **ラン番号付きディレクトリ** を作成します。
- 各ランには:
  - 実際のゲームテーブル (`game_table.csv` など)
  - メタデータ (`metadata.yaml`)
  を保存します。

## メタデータ仕様

`metadata.yaml` は最低限以下の情報を持ちます。

```yaml
kind: buldyrev
run_id: 1
format: csv
filename: game_table.csv
source_path: /absolute/or/relative/path/to/original.csv
copied: true        # true のとき run ディレクトリにコピー済み
created_at: "2025-01-01T12:34:56.789012+00:00"
note: "任意のコメント"
```

- `kind`: ゲームテーブルの種別名
- `run_id`: 1 から始まる整数のラン番号
- `format`: `csv`, `parquet` など
- `filename`: ランディレクトリ内のファイル名
- `source_path`: 元のファイルのパス
- `copied`: 元ファイルをコピーしたかどうか
- `created_at`: ISO8601 形式のタイムスタンプ
- `note`: 任意のコメント

## Python API

モジュール: `contrib_metrics.io.game_table_manager`

### `GameTableRun`

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

@dataclass
class GameTableRun:
    kind: str
    run_id: int
    path: Path
    format: str
    created_at: datetime
    metadata_path: Path
```

- 1 つのランを表現する軽量オブジェクトです。

### `register_game_table`

```python
from pathlib import Path
from contrib_metrics.io.game_table_manager import register_game_table

run = register_game_table(
    kind="buldyrev",
    src=Path("path/to/game_table.csv"),
    root=Path("data/game_tables"),
    fmt="csv",           # デフォルトは拡張子から推定
    note="baseline run", # 任意
    copy=True,           # True なら run ディレクトリにコピー
)
print(run.run_id, run.path)
```

- 指定した `kind` 用の次のラン番号 (`run_0001`, `run_0002`, ...) を自動で割り当て、
  ディレクトリ・ゲームテーブル・`metadata.yaml` を作成します。

### `list_runs`

```python
from contrib_metrics.io.game_table_manager import list_runs

runs = list_runs(kind="buldyrev", root="data/game_tables")
for r in runs:
    print(r.run_id, r.path)
```

- 指定した `kind` の全ランを `run_id` 昇順で返します。

### `get_latest_run`

```python
from contrib_metrics.io.game_table_manager import get_latest_run

latest = get_latest_run(kind="buldyrev", root="data/game_tables")
if latest is not None:
    print("latest run:", latest.run_id, latest.path)
```

- 指定した `kind` のうち、最大の `run_id` を持つランを返します（存在しない場合は `None`）。

## 計算への組み込みイメージ

他リポジトリやノートブック側でゲームテーブルを生成した後:

1. `register_game_table` で `data/game_tables/<kind>/run_xxxx` に登録
2. `GameTableRun.path` を `config/example_config.yaml` の `input.path` に設定
3. `poetry run contrib-metrics compute --config ...` で貢献度指標を計算

というフローを想定しています。

CLI からの直接操作（例: `contrib-metrics table-register ...`）は必要になった段階で追加できるよう、
現在は Python API とディレクトリレイアウトの仕様にフォーカスしています。

