"""Eval 1: where do the court-named pitches rank among ALL of Clase's 2023-25 pitches?

Compares the pre-registered PIM score with simple baselines. Labels are allegations
from a public court filing; they are used here only for evaluation, never for fitting.
Unscored pitches (not enough prior history) rank at the bottom, so they count as misses.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pim.score import baseline_out_of_zone, baseline_spiked_ball, score  # noqa: E402

CLASE = 661403
KEY = ["game_pk", "at_bat_number", "pitch_number"]
RNG = np.random.default_rng(20261031)


def load():
    d = score(pd.read_parquet("data/slim/pitchers_clase_ortiz.parquet"))
    d = d[d["pitcher"] == CLASE].copy()
    lab = pd.read_csv("data/labels/matched.csv")
    lab = lab[lab["match_status"] == "matched"][KEY].assign(label=1)
    d = d.merge(lab, on=KEY, how="left")
    d["label"] = d["label"].fillna(0).astype(int)
    return d


def metrics(y, s):
    s = np.where(np.isfinite(s), s, -1e9)
    order = np.argsort(-s, kind="stable")
    ranks = np.empty(len(s), int)
    ranks[order] = np.arange(1, len(s) + 1)
    pos = ranks[y == 1]
    return {
        "avg_precision": float(average_precision_score(y, s)),
        "hits_top18": int((pos <= 18).sum()),
        "hits_top50": int((pos <= 50).sum()),
        "hits_top100": int((pos <= 100).sum()),
        "hits_top300": int((pos <= 300).sum()),
        "median_rank": int(np.median(pos)),
        "median_top_pct": float(np.median(pos) / len(s) * 100),
    }


def bootstrap_ap(y, s, n=2000):
    s = np.where(np.isfinite(s), s, -1e9)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    out = []
    for _ in range(n):
        idx = np.concatenate([RNG.choice(pos, len(pos)), RNG.choice(neg, len(neg))])
        out.append(average_precision_score(y[idx], s[idx]))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def main():
    d = load()
    y = d["label"].to_numpy()
    methods = {
        "PIM (ours)": d["pim_score"].to_numpy(),
        "B1 spiked-ball rule": baseline_spiked_ball(d),
        "B2 distance outside zone": baseline_out_of_zone(d),
        "B3 random": RNG.random(len(d)),
    }
    res = {"n_pitches": int(len(d)), "n_labels": int(y.sum()),
           "n_labels_unscored_by_pim": int(((y == 1) & d["pim_score"].isna()).sum()),
           "prevalence": float(y.mean()), "methods": {}}
    for name, s in methods.items():
        m = metrics(y, s)
        m["ap_95ci"] = bootstrap_ap(y, s)
        res["methods"][name] = m
    Path("results").mkdir(exist_ok=True)
    Path("results/within_clase.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    cols = ["pitch_type", "release_speed", "balls", "strikes", "inning", "description",
            "p_location", "p_choice", "p_velocity", "pim_score"]
    d["pim_rank"] = d["pim_score"].rank(ascending=False, method="min")
    print(d.loc[d.label == 1, ["game_date"] + cols + ["pim_rank"]].to_string())


if __name__ == "__main__":
    main()
