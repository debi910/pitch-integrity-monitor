"""Post-hoc robustness of the frozen v2 monitor (run AFTER eval/league_monitor.py; nothing here changes it).

Two questions a judge should ask:
  1. Does the Clase May 2025 result survive other reasonable settings, or did we get lucky with one?
     Grid: SPIKE_Z x MIN_FIRST_PITCHES x SHRINK. We report every cell, including the bad ones.
  2. The binomial null under-counts alerts (27 seen vs 4.4 expected). What if the null allows for
     real month-to-month wobble? We fit a beta-binomial (method of moments) to the league and re-score.
Writes results/robustness.json. Names only the two charged pitchers.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pim.monitor as mon  # noqa: E402
from eval.league_monitor import load_league, positives  # noqa: E402
from pim.score import prepare  # noqa: E402

TARGET = (661403, "2025-05")
ALERT = 3.0  # score >= 3 means p <= 0.001


def run(d, pos, spike_z, min_n, shrink):
    mon.SPIKE_Z, mon.MIN_FIRST_PITCHES, mon.SHRINK = spike_z, min_n, shrink
    m = mon.monthly(d)
    m["label"] = [int((p, mo) in pos) for p, mo in zip(m["pitcher"], m["month"])]
    rank = m["score_audit"].rank(ascending=False, method="min")
    hit = (m["pitcher"] == TARGET[0]) & (m["month"] == TARGET[1])
    return m, {
        "spike_z": spike_z, "min_first_pitches": min_n, "shrink": shrink, "cells": int(len(m)),
        "rank_clase_2025_05": int(rank[hit].iloc[0]) if hit.any() else None,
        "rank_raw_rate": int(m["rate"].rank(ascending=False, method="min")[hit].iloc[0]) if hit.any() else None,
        "alerts": int((m["score_audit"] >= ALERT).sum()),
        "named_months_alerted": int(((m["score_audit"] >= ALERT) & (m["label"] == 1)).sum()),
        "named_months": int(m["label"].sum()),
    }


def beta_binomial(m):
    """Method-of-moments overdispersion of a pitcher's monthly rate around his own baseline."""
    p, n, k = m["base_audit"].to_numpy(), m["n"].to_numpy(), m["k"].to_numpy()
    resid = (k - n * p) ** 2 / (n * p * (1 - p))            # = 1 + (n-1)rho under beta-binomial
    rho = float(np.clip(np.sum(resid - 1) / np.sum(n - 1), 1e-6, 0.5))
    a, b = p * (1 - rho) / rho, (1 - p) * (1 - rho) / rho
    s = -np.log10(np.clip(stats.betabinom.sf(k - 1, n, a, b), 1e-300, 1))
    hit = (m["pitcher"] == TARGET[0]) & (m["month"] == TARGET[1])
    exp_bb = float(sum(stats.betabinom.sf(np.arange(nn + 1) - 1, nn, aa, bb)[
        np.argmax(stats.betabinom.sf(np.arange(nn + 1) - 1, nn, aa, bb) <= 10 ** -ALERT)]
        if (stats.betabinom.sf(np.arange(nn + 1) - 1, nn, aa, bb) <= 10 ** -ALERT).any() else 0.0
        for nn, aa, bb in zip(n, a, b)))
    return {
        "rho": rho, "alerts": int((s >= ALERT).sum()), "expected_alerts_under_null": round(exp_bb, 1),
        "rank_clase_2025_05": int(pd.Series(s).rank(ascending=False, method="min")[hit.to_numpy()].iloc[0]),
        "score_clase_2025_05": round(float(s[hit.to_numpy()][0]), 2),
        "named_months_alerted": int(((s >= ALERT) & (m["label"].to_numpy() == 1)).sum()),
    }


def main():
    raw, _ = load_league()
    d, pos = prepare(raw), positives()
    frozen = (mon.SPIKE_Z, mon.MIN_FIRST_PITCHES, mon.SHRINK)
    grid = [run(d, pos, *g)[1] for g in itertools.product([-0.2, -0.3, -0.4], [15, 20, 30], [50, 150, 400])]
    m, _ = run(d, pos, *frozen)
    out = {"frozen": dict(zip(["spike_z", "min_first_pitches", "shrink"], frozen)), "grid": grid,
           "beta_binomial": beta_binomial(m),
           "summary": {"settings": len(grid),
                       "clase_top50": sum(g["rank_clase_2025_05"] is not None and g["rank_clase_2025_05"] <= 50 for g in grid),
                       "beats_raw_rate": sum(g["rank_clase_2025_05"] is not None and g["rank_clase_2025_05"] < g["rank_raw_rate"] for g in grid),
                       "best_rank": min(g["rank_clase_2025_05"] for g in grid if g["rank_clase_2025_05"]),
                       "worst_rank": max(g["rank_clase_2025_05"] for g in grid if g["rank_clase_2025_05"]),
                       "alerts_range": [min(g["alerts"] for g in grid), max(g["alerts"] for g in grid)]}}
    Path("results/robustness.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["summary"], indent=2), json.dumps(out["beta_binomial"], indent=2), sep="\n")
    for g in grid:
        print(g)


if __name__ == "__main__":
    main()
