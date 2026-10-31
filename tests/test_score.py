import numpy as np
import pandas as pd

from pim.monitor import monthly
from pim.score import baseline_spiked_ball, prepare, score

SLIM = "data/slim/pitchers_clase_ortiz.parquet"


def test_no_lookahead():
    """A pitch's score must not change when later games are removed."""
    raw = pd.read_parquet(SLIM)
    raw = raw[raw["pitcher"] == 661403]
    full = score(raw)
    cut = pd.Timestamp("2024-06-01")
    part = score(raw[pd.to_datetime(raw["game_date"]) < cut])
    key = ["game_pk", "at_bat_number", "pitch_number"]
    m = part.merge(full, on=key, suffixes=("_p", "_f"))
    assert len(m) == len(part)
    assert np.allclose(m["pim_score_p"], m["pim_score_f"], equal_nan=True)


def test_all_labels_scored_and_matched():
    lab = pd.read_csv("data/labels/matched.csv")
    assert (lab["match_status"] == "matched").sum() == 18
    d = score(pd.read_parquet(SLIM))
    key = ["game_pk", "at_bat_number", "pitch_number"]
    j = d.merge(lab[lab["match_status"] == "matched"][key], on=key)
    assert len(j) == 18 and j["pim_score"].notna().all()


def test_baseline_only_scores_balls():
    d = prepare(pd.read_parquet(SLIM))
    s = baseline_spiked_ball(d)
    assert np.isneginf(s[~d["description"].isin(["ball", "blocked_ball"])]).all()


def test_monitor_cells_have_min_volume():
    m = monthly(prepare(pd.read_parquet(SLIM)))
    assert (m["n"] >= 20).all() and m["score_audit"].ge(0).all()
