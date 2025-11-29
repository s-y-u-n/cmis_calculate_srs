# ゲームテーブル管理

## 目的

同じゲームクラス（例: Buldyrev, NK, 港湾物流など）でも、パラメータやシナリオを変えて
複数回ゲームテーブルを生成することがあります。
このとき、

- ゲームクラスごとにディレクトリを分ける
- 1 回目, 2 回目, ... の生成結果を「ラン番号」で管理する

ための簡易的な管理レイヤーを提供します。

## ディレクトリ構造

### このリポジトリでの実データ配置

`data/game_tables` には、別リポジトリで生成されたゲームテーブルが
「種別ごとのディレクトリ + `<kind>_NNN.csv`」という構造で配置されています。

```text
data/
  game_tables/
    ethiraj2004/
      ethiraj2004_001.csv
      ethiraj2004_002.csv
      ethiraj2004_003.csv
    lazer2007/
      lazer2007_001.csv
      lazer2007_002.csv
      ...
    levinthal1997/
      levinthal1997_001.csv
      levinthal1997_002.csv
      ...
```

- `game_tables/` 以下の 1 階層目のディレクトリ名（例: `ethiraj2004`）を
  **ゲームテーブル種別（kind）** と呼びます。
- その配下の `<kind>_NNN.csv` を「ラン番号 NNN の実験結果」とみなし、
  `GameTableRun.run_id` と対応づけて扱います。

### 拡張: 管理用ディレクトリとメタデータ

必要に応じて、よりリッチな管理のために

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
```

のように `run_0001`, `run_0002`, ... の下に

- 実際のゲームテーブル (`game_table.csv` など)
- メタデータ (`metadata.yaml`)

を置く構造もサポートしています。

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
    metadata_path: Path | None
```

- 1 つのランを表現する軽量オブジェクトです。
  - `metadata_path` は、管理用レイアウト（`run_0001` 配下に metadata.yaml がある場合）のみに設定され、
    `<kind>_NNN.csv` のような生ファイルの場合は `None` になります。

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

runs = list_runs(kind="ethiraj2004", root="data/game_tables")
for r in runs:
    print(r.run_id, r.path)
```

- 指定した `kind` の全ランを `run_id` 昇順で返します。
  - `ethiraj2004_001.csv` のような名前のファイルも自動的に検出して `run_id=1` として扱います。

### `get_latest_run`

```python
from contrib_metrics.io.game_table_manager import get_latest_run

latest = get_latest_run(kind="ethiraj2004", root="data/game_tables")
if latest is not None:
    print("latest run:", latest.run_id, latest.path)
```

- 指定した `kind` のうち、最大の `run_id` を持つランを返します（存在しない場合は `None`）。

## 計算への組み込みイメージ

他リポジトリやノートブック側でゲームテーブルを生成した後:

1. 既存の `<kind>_NNN.csv` をそのまま `GameTableRun` として扱う場合:

   ```python
   from contrib_metrics.io.game_table_manager import get_latest_run

   latest = get_latest_run("ethiraj2004", root="data/game_tables")
   if latest is not None:
       print(latest.run_id, latest.path)
       # latest.path を config の input.path に指定して計算
   ```

2. 追加でメタデータ付きの管理レイアウトを使いたい場合:

   - `register_game_table` で `data/game_tables/<kind>/run_xxxx` に登録
   - `GameTableRun.path` を `config/example_config.yaml` の `input.path` に設定
   - `poetry run contrib-metrics compute --config ...` で貢献度指標を計算

というフローを想定しています。

CLI からの直接操作（例: `contrib-metrics table-register ...`）は必要になった段階で追加できるよう、
現在は Python API とディレクトリレイアウトの仕様にフォーカスしています。
