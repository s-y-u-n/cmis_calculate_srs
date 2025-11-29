from __future__ import annotations

from pathlib import Path

from contrib_metrics.io.readers import read_game_table


def test_read_game_table_csv(tmp_path: Path) -> None:
    csv_content = "scenario_id,game_id,coalition,value\n1,1,\"{1,2}\",3.0\n"
    path = tmp_path / "game.csv"
    path.write_text(csv_content, encoding="utf-8")

    df = read_game_table(path)
    assert len(df) == 1
    c = df.loc[0, "coalition"]
    assert isinstance(c, frozenset)
    assert c == frozenset({1, 2})
