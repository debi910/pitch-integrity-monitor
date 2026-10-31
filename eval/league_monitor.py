"""Eval 2: league-wide false-alarm test for the pattern monitor.

Scores every pitcher-month in 2023-25 (all MLB pitchers) and asks:
  - where do the months that contain court-named pitches rank?
  - how many OTHER pitcher-months would an analyst have to review at the same threshold?
Compared with simple methods that ignore the pitcher's own baseline (raw rate, raw count).

Privacy/fairness: results name only the two publicly charged pitchers. Every other
flagged pitcher-month is reported as a count, never by name or id.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pim.monitor import monthly  # noqa: E402
from pim.score import prepare  # noqa: E402

NAMED = {661403: "Emmanuel Clase", 682847: "Luis L. Ortiz"}
COLS = ["game_date", "game_pk", "game_type", "at_bat_number", "pitch_number", "pitcher", "batter",
        "stand", "pitch_type", "plate_x", "plate_z", "sz_top", "sz_bot", "description"]


def load_league():
    files = sorted(glob.glob("data/slim/statcast_20*.parquet"))
    if not files:
        sys.exit("no league files in data/slim/")
    return pd.concat([pd.read_parquet(f, columns=COLS) for f in files], ignore_index=True), files


def positives():
    lab = pd.read_csv("data/labels/matched.csv")
    lab = lab[lab["match_status"] == "matched"]
    months = set(pd.to_datetime(lab["game_date"]).dt.to_period("M").astype(str))
    pos = {(661403, m) for m in months}
    ortiz = pd.read_csv("data/labels/ortiz_games.csv") if Path("data/labels/ortiz_games.csv").exists() else None
    if ortiz is not None and "game_date" in ortiz:
        pos |= {(682847, m) for m in pd.to_datetime(ortiz["game_date"]).dt.to_period("M").astype(str)}
    else:
        pos |= {(682847, "2025-06")}
    return pos


def expected_alerts(ns, bases, t):
    """If every pitcher threw at his own baseline rate, how many cells would score >= t?"""
    total = 0.0
    for n, b in zip(ns, bases):
        k = np.arange(n + 1)
        tail = stats.binom.sf(k - 1, n, b)  # P(X >= k)
        hit = k[tail <= 10 ** -t]
        total += tail[hit[0]] if len(hit) else 0.0
    return total


def rank_report(m, col, y):
    s = m[col].to_numpy()
    r = pd.Series(s).rank(ascending=False, method="min").to_numpy()
    top1 = r <= max(1, int(len(m) * 0.01))
    return {
        "avg_precision": float(average_precision_score(y, s)),
        "positive_ranks": {f"{NAMED[p]} {mo}": int(rk) for p, mo, rk, yy in
                           zip(m["pitcher"], m["month"], r, y) if yy},
        "positives_in_top1pct": int((top1 & (y == 1)).sum()),
        "cells_in_top1pct": int(top1.sum()),
    }


def main():
    raw, files = load_league()
    d = prepare(raw)
    m = monthly(d)
    pos = positives()
    m["label"] = [int((p, mo) in pos) for p, mo in zip(m["pitcher"], m["month"])]
    y = m["label"].to_numpy()
    m["baseline_rate"] = m["rate"]
    m["baseline_count"] = m["k"] + m["n"] * 1e-6  # tie-break by volume

    res = {"files": files, "n_pitches": int(len(d)), "n_pitchers": int(m["pitcher"].nunique()),
           "n_pitcher_months": int(len(m)), "n_positive_months": int(y.sum()),
           "positive_months_scored": sorted(f"{NAMED[p]} {mo}" for p, mo, yy in
                                            zip(m["pitcher"], m["month"], y) if yy),
           "league_first_pitch_spike_rate": float(m["league_rate"].iloc[0]), "methods": {}}
    for col in ["score_audit", "score_live", "baseline_rate", "baseline_count"]:
        res["methods"][col] = rank_report(m, col, y)

    # alert volume at fixed thresholds of the monitor (p <= 0.01, 0.001)
    months_covered = m["month"].nunique()
    res["alerts"] = {}
    for t in [2.0, 3.0]:
        for col in ["score_audit", "score_live"]:
            flag = m[col] >= t
            res["alerts"][f"{col}>={t}"] = {
                "flagged_cells": int(flag.sum()),
                "flagged_named_cells": int((flag & (y == 1)).sum()),
                "flagged_other_cells": int((flag & (y == 0)).sum()),
                "per_month_league_wide": round(float(flag.sum()) / months_covered, 2),
                "expected_by_chance_if_binomial": round(expected_alerts(
                    m["n"], m["base_audit" if col == "score_audit" else "base_live"], t), 1),
            }
    # where do the named pitchers' months sit in the league distribution
    named = m[m["pitcher"].isin(NAMED)][["pitcher", "month", "n", "k", "rate", "base_audit",
                                         "score_audit", "score_live", "label"]].copy()
    named["pitcher"] = named["pitcher"].map(NAMED)
    named["league_pct_audit"] = [float((m["score_audit"] >= s).mean() * 100) for s in named["score_audit"]]
    Path("results").mkdir(exist_ok=True)
    named.round(4).to_csv("results/named_pitcher_months.csv", index=False)
    # anonymised league distribution for the app
    m[["month", "n", "k", "rate", "score_audit", "score_live", "label"]].assign(
        is_named=m["pitcher"].isin(NAMED)).round(4).to_csv("results/league_cells_anon.csv", index=False)
    Path("results/league_monitor.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(named.round(3).to_string())


if __name__ == "__main__":
    main()
