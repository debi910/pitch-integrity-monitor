"""Eval 3 (pre-registered before any IL data was joined): does coach-mode drift come BEFORE an IL stint?

Unit: pitcher-month scored by pim/drift.py (live mode, earlier months only).
Label: the pitcher is PLACED on the injured list within INJ_WINDOW days after his last game that
month (type == "placed"; "transferred"/"activated" rows ignored). Pitcher-months that themselves
contain an IL placement before the last game are dropped (already hurt).
Methods compared, all live:
  ours      drift_score (command + velocity, Fisher)
  B1        velocity drop in mph vs his earlier mean (what most teams already watch)
  B2        command score alone
  B3        raw wild-pitch rate (no personal baseline)
  B4        random
Metrics: ROC AUC, average precision, lift in the top 5% of months, each with a pitcher-clustered
bootstrap 95% CI (1,000 resamples, seed 20261031). Primary comparison: ours vs B1 (AUC difference).
We report every number whatever it shows. Writes results/injury.json.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pim.drift import pitcher_months  # noqa: E402
from pim.score import prepare  # noqa: E402

INJ_WINDOW = 30
SEED, B = 20261031, 1000
COLS = ["game_date", "game_pk", "game_type", "at_bat_number", "pitch_number", "pitcher", "batter", "stand",
        "pitch_type", "release_speed", "plate_x", "plate_z", "sz_top", "sz_bot", "description"]


def load():
    files = sorted(glob.glob("data/slim/statcast_20*.parquet"))
    return pd.concat([pd.read_parquet(f, columns=COLS) for f in files], ignore_index=True)


def labels(m, il):
    il = il[il["type"] == "placed"].copy()
    il["d"] = pd.to_datetime(il["effective_date"].fillna(il["date"]))
    il = il[["person_id", "d"]].rename(columns={"person_id": "pitcher"})
    x = m[["pitcher", "month", "last_game"]].merge(il, on="pitcher", how="left")
    month_start = pd.PeriodIndex(x["month"], freq="M").start_time
    gap = (x["d"] - x["last_game"]).dt.days
    x["pos"] = gap.between(1, INJ_WINDOW)
    x["already"] = (x["d"] >= month_start) & (x["d"] <= x["last_game"])
    agg = x.groupby(["pitcher", "month"]).agg(label=("pos", "max"), already=("already", "max")).reset_index()
    return m.merge(agg, on=["pitcher", "month"])


def metrics(y, s):
    top = s >= np.quantile(s, 0.95)
    return {"auc": roc_auc_score(y, s), "ap": average_precision_score(y, s),
            "lift_top5": (y[top].mean() / y.mean()) if y.mean() > 0 else np.nan}


def main():
    m = pitcher_months(prepare(load()))
    il = pd.read_csv("data/labels/il_transactions.csv")
    m = labels(m, il)
    m = m[~m["already"]].reset_index(drop=True)
    rng = np.random.default_rng(SEED)
    scores = {"ours: drift (command + velocity)": m["drift_score"].to_numpy(),
              "B1: velocity drop (mph)": m["velo_drop"].fillna(-99).to_numpy(),
              "B2: command alone": m["command_score"].to_numpy(),
              "B3: raw wild rate": m["wild_rate"].to_numpy(),
              "B4: random": rng.random(len(m))}
    y = m["label"].astype(int).to_numpy()
    pitchers = m["pitcher"].to_numpy()
    uniq = np.unique(pitchers)
    idx_by_p = {p: np.flatnonzero(pitchers == p) for p in uniq}
    point = {k: metrics(y, s) for k, s in scores.items()}
    boots = {k: {q: [] for q in ["auc", "ap", "lift_top5"]} for k in scores}
    diff = []
    for _ in range(B):
        take = np.concatenate([idx_by_p[p] for p in rng.choice(uniq, len(uniq))])
        if y[take].sum() == 0:
            continue
        for k, s in scores.items():
            for q, v in metrics(y[take], s[take]).items():
                boots[k][q].append(v)
        diff.append(boots["ours: drift (command + velocity)"]["auc"][-1] - boots["B1: velocity drop (mph)"]["auc"][-1])
    out = {"n_pitcher_months": int(len(m)), "n_pitchers": int(len(uniq)), "n_positive": int(y.sum()),
           "base_rate": float(y.mean()), "window_days": INJ_WINDOW, "methods": {}}
    for k in scores:
        out["methods"][k] = {q: {"point": round(float(point[k][q]), 4),
                                 "ci95": [round(float(np.nanpercentile(boots[k][q], 2.5)), 4),
                                          round(float(np.nanpercentile(boots[k][q], 97.5)), 4)]}
                             for q in ["auc", "ap", "lift_top5"]}
    out["auc_diff_ours_minus_velocity"] = {"point": round(float(point["ours: drift (command + velocity)"]["auc"] -
                                                                point["B1: velocity drop (mph)"]["auc"]), 4),
                                           "ci95": [round(float(np.percentile(diff, 2.5)), 4),
                                                    round(float(np.percentile(diff, 97.5)), 4)]}
    Path("results/injury.json").write_text(json.dumps(out, indent=2))
    m.drop(columns=["pitcher"]).assign(label=y).to_csv("results/drift_cells_anon.csv", index=False)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
