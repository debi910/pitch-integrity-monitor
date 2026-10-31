import json

import pandas as pd

from pim.__main__ import main, monitor
from pim.monitor import monthly
from pim.score import prepare


def test_cli_matches_frozen_monitor_on_league_data():
    """The CLI's scores equal pim.monitor.monthly when the league rate comes from the same data."""
    df = pd.read_parquet("data/slim/statcast_2025.parquet")
    ref = monthly(prepare(df))
    rate = ref["league_rate"].iloc[0]
    got = monitor(df, rate)
    key = ["pitcher", "month"]
    m = ref.merge(got, on=key, suffixes=("_r", "_g"))
    assert len(m) == len(ref) == len(got)
    assert (m["score_audit_r"] - m["score_audit_g"]).abs().max() < 1e-9
    assert (m["score_live_r"] - m["score_live_g"]).abs().max() < 1e-9


def test_cli_runs_on_a_single_pitcher_file(tmp_path, capsys):
    out = tmp_path / "ranked.csv"
    main(["data/slim/pitchers_clase_ortiz.parquet", "--mode", "audit", "--top", "5", "--out", str(out)])
    r = pd.read_csv(out)
    top = r[r["pitcher"] == 661403].sort_values("score_audit", ascending=False).iloc[0]
    assert top["month"] == "2025-05" and top["k"] == 9 and top["n"] == 41
    assert "review list" in capsys.readouterr().out
