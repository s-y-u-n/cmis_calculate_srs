from __future__ import annotations

from pathlib import Path

from contrib_metrics.cli import main


def test_cli_compute(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    cfg = tmp_path / "config.yaml"
    data = tmp_path / "game.csv"

    data.write_text(
        "scenario_id,game_id,coalition,value\n"
        "1,1,\"{1}\",1.0\n"
        "1,1,\"{1,2}\",2.0\n",
        encoding="utf-8",
    )

    cfg.write_text(
        f"""
input:
  path: {data}
  format: csv
  game_type: TU
indices:
  shapley:
    exact: true
    monte_carlo_samples: 0
  banzhaf:
    enabled: true
    normalize: true
  synergy:
    enabled: false
""",
        encoding="utf-8",
    )

    # Support both styles: with and without 'compute'
    main(["compute", "--config", str(cfg)])

    # CLI は標準出力ではなく CSV に結果を書き出す想定なので、
    # 出力ディレクトリに individuals テーブルが生成されていることを確認する。
    base_dir = Path("outputs") / data.parent / data.stem
    individuals = base_dir / "tables" / "individuals.csv"
    assert individuals.exists()
