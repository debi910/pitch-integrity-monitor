"""Detection power: how many rigged first pitches a month before the frozen monitor can see them?

Post-hoc, label-free. For every real pitcher-month (n >= 20 first pitches) we swap r ordinary first
pitches for rigged ones (taken ball in the dirt, the template event) and re-score that month with the
frozen monitor against the pitcher's own other months. Detection = the month crosses the alert line.
Two alert lines:
  - binomial null, p <= 0.001 (the frozen setting, ~1.1 alerts/month league-wide)
  - beta-binomial null, p <= 0.001 (allows normal month-to-month wobble; 3 alerts in 3 seasons)
Answers "how big must a fix be to show up in public data?" without relying on the 18 allegations.
Writes results/power.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.league_monitor import load_league  # noqa: E402
from pim.monitor import monthly  # noqa: E402
from pim.score import prepare  # noqa: E402

ALERT = 3.0
RS = list(range(0, 16))
RHO = json.loads(Path("results/robustness.json").read_text())["beta_binomial"]["rho"]


def detect(n, k, base, r, rho=None):
    k2 = np.minimum(n, k + r)
    if rho is None:
        sf = stats.binom.sf(k2 - 1, n, base)
    else:
        sf = stats.betabinom.sf(k2 - 1, n, base * (1 - rho) / rho, (1 - base) * (1 - rho) / rho)
    return -np.log10(np.clip(sf, 1e-300, 1)) >= ALERT


def curve(m, rho=None):
    n, k, b = m["n"].to_numpy(), m["k"].to_numpy(), m["base_audit"].to_numpy()
    return [round(float(detect(n, k, b, r, rho).mean()), 4) for r in RS]


def first_r(c, level):
    return next((r for r, p in zip(RS, c) if p >= level), None)


def main():
    raw, _ = load_league()
    m = monthly(prepare(raw))
    # relievers face ~1 batter-inning; split by monthly first-pitch volume (batters faced)
    groups = {"all": m, "light (20-59 batters/month, mostly relievers)": m[m["n"] < 60],
              "heavy (60+ batters/month, mostly starters)": m[m["n"] >= 60]}
    out = {"r": RS, "alert_score": ALERT, "rho": RHO, "groups": {}}
    for g, mm in groups.items():
        cb, cbb = curve(mm), curve(mm, RHO)
        out["groups"][g] = {"cells": int(len(mm)), "median_n": int(mm["n"].median()),
                            "binomial": cb, "beta_binomial": cbb,
                            "r50_binomial": first_r(cb, .5), "r90_binomial": first_r(cb, .9),
                            "r50_beta_binomial": first_r(cbb, .5), "r90_beta_binomial": first_r(cbb, .9)}
    Path("results/power.json").write_text(json.dumps(out, indent=2))
    for g, v in out["groups"].items():
        print(g, v["cells"], "median n", v["median_n"])
        print("  binom ", v["binomial"][:12], "r50", v["r50_binomial"], "r90", v["r90_binomial"])
        print("  betab ", v["beta_binomial"][:12], "r50", v["r50_beta_binomial"], "r90", v["r90_beta_binomial"])


if __name__ == "__main__":
    main()
