"""Post-hoc: remove the hand-picked dirt cut-off (SPIKE_Z = -0.3).

The frozen monitor counts first pitches more than 30% of a zone height below the zone. That 30% came from
the indictment's wording, but we chose it after seeing the labels, and the stress test showed the rank moves
a lot at 20% or 40%. Here we score every pitcher-month at ELEVEN cut-offs (10% to 60% below the zone, step
5%) and combine them two ways, decided before looking at any rank:
  mean   - average of the eleven -log10 p scores (integrates over cut-offs)
  max    - best single cut-off, i.e. min-p (more sensitive, more multiple testing)
League alert line for each is set label-free so the whole league gets the same ~1.1 alerts/month as the
frozen monitor (27 in 3 seasons). Writes results/threshold_free.json and an anonymised cell file.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pim.monitor as mon  # noqa: E402
from eval.league_monitor import load_league, positives  # noqa: E402
from pim.score import prepare  # noqa: E402

GRID = [round(-0.10 - 0.05 * i, 2) for i in range(11)]
TARGET = (661403, "2025-05")
FROZEN_ALERTS = 27


def main():
    raw, _ = load_league()
    d, pos = prepare(raw), positives()
    key = ["pitcher", "month"]
    cols = {}
    base = None
    for z in GRID:
        mon.SPIKE_Z = z
        m = mon.monthly(d)
        cols[z] = m.set_index(key)["score_audit"]
        if base is None:
            base = m.set_index(key)[["n"]]
    S = pd.DataFrame(cols).reindex(base.index).fillna(0.0)
    out_cells = base.assign(mean=S.mean(axis=1), max=S.max(axis=1), frozen=S[-0.3]).reset_index()
    out_cells["label"] = [int((p, mo) in pos) for p, mo in zip(out_cells["pitcher"], out_cells["month"])]
    hit = (out_cells["pitcher"] == TARGET[0]) & (out_cells["month"] == TARGET[1])
    res = {"grid": GRID, "cells": int(len(out_cells)), "methods": {}}
    for c in ["frozen", "mean", "max"]:
        s = out_cells[c]
        rank = s.rank(ascending=False, method="min")
        line = float(np.sort(s.to_numpy())[::-1][FROZEN_ALERTS - 1])  # same alert volume as frozen
        alerts = s >= line
        res["methods"][c] = {
            "rank_clase_2025_05": int(rank[hit].iloc[0]),
            "named_month_ranks": {f"{p} {mo}": int(r) for p, mo, r, y in
                                  zip(out_cells["pitcher"], out_cells["month"], rank, out_cells["label"]) if y},
            "alert_line": round(line, 3), "alerts": int(alerts.sum()),
            "named_months_alerted": int((alerts & (out_cells["label"] == 1)).sum()),
        }
    res["clase_2025_05_by_cutoff"] = {str(z): round(float(S.loc[TARGET, z]), 3) for z in GRID}
    res["clase_2025_05_rank_by_cutoff"] = {str(z): int(S[z].rank(ascending=False, method="min").loc[TARGET]) for z in GRID}
    Path("results/threshold_free.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
