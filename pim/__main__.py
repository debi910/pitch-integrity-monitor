"""Command line: score any Statcast export with the frozen pattern monitor and the per-pitch model.

    python -m pim pitches.csv                 # a Baseball Savant CSV export or a parquet file
    python -m pim pitches.csv --mode live --top 15 --out alerts.csv [--names]

Each pitcher-month gets k template events (first pitch, taken for a ball, well below the zone) out of n
first pitches, compared with that pitcher's own baseline shrunk toward the league rate. Months scoring
>= 3 (p <= 0.001) are marked ALERT; across MLB 2023-25 that happened about once a month league-wide.
Output is a ranked review list for a human investigator, never a verdict.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from pim.monitor import MIN_FIRST_PITCHES, SHRINK, template_events
from pim.score import prepare

ALERT = 3.0
_LEAGUE_JSON = Path(__file__).resolve().parents[1] / "results" / "league_monitor.json"


def league_rate():
    try:
        return json.loads(_LEAGUE_JSON.read_text())["league_first_pitch_spike_rate"]
    except (OSError, KeyError):
        return 0.0587  # MLB 2023-25, see results/league_monitor.json


def monitor(df, rate):
    fp = template_events(prepare(df))
    m = fp.groupby(["pitcher", "month"]).agg(n=("event", "size"), k=("event", "sum")).reset_index()
    m = m.sort_values(["pitcher", "month"])
    tot_n, tot_k = m.groupby("pitcher")["n"].transform("sum"), m.groupby("pitcher")["k"].transform("sum")
    prev_n = m.groupby("pitcher")["n"].cumsum() - m["n"]
    prev_k = m.groupby("pitcher")["k"].cumsum() - m["k"]
    for mode, (ok, on) in {"audit": (tot_k - m["k"], tot_n - m["n"]), "live": (prev_k, prev_n)}.items():
        base = (ok + SHRINK * rate) / (on + SHRINK)
        m[f"base_{mode}"] = base
        m[f"score_{mode}"] = -np.log10(np.clip(stats.binom.sf(m["k"] - 1, m["n"], base), 1e-300, 1))
    m["rate"] = m["k"] / m["n"]
    return m[m["n"] >= MIN_FIRST_PITCHES].reset_index(drop=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m pim", description=__doc__.split("\n\n")[0])
    ap.add_argument("path", help="Statcast pitch-level CSV (Baseball Savant export) or parquet")
    ap.add_argument("--mode", choices=["audit", "live"], default="live",
                    help="baseline from other months (audit) or earlier months only (live, default)")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--league-rate", type=float, default=None, help="override the MLB template rate")
    ap.add_argument("--out", help="write the full ranked table to this CSV")
    ap.add_argument("--names", action="store_true",
                    help="show player names (off by default: an alert is not an accusation)")
    a = ap.parse_args(argv)

    p = Path(a.path)
    df = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p, low_memory=False)
    m = monitor(df, a.league_rate or league_rate())
    col = f"score_{a.mode}"
    m = m.sort_values(col, ascending=False).reset_index(drop=True)
    m["alert"] = np.where(m[col] >= ALERT, "ALERT", "")
    names = {}
    if a.names and "player_name" in df.columns:
        names = df.drop_duplicates("pitcher").set_index("pitcher")["player_name"].to_dict()
    m.insert(1, "name", m["pitcher"].map(names).fillna(""))
    show = m.head(a.top)[["pitcher", "name", "month", "n", "k", "rate", f"base_{a.mode}", col, "alert"]]
    pd.set_option("display.width", 160)
    print(show.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\n{len(m)} pitcher-months scored ({a.mode} baseline); {(m[col] >= ALERT).sum()} at score >= {ALERT}.")
    print("Unusual is not proof of anything: treat this as a review list for a human.")
    if a.out:
        m.to_csv(a.out, index=False)
        print("wrote", a.out)


if __name__ == "__main__":
    main()
