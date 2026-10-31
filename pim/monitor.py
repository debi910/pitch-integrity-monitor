"""Pattern monitor: has a pitcher's OWN first-pitch miss rate jumped?

Single rigged pitches look like ordinary misses (see results/within_clase.json), so we
monitor the rate of a public "scheme template" instead. The template comes from the
DOJ indictment's own description, not from the labelled pitches:
  "To ensure certain pitches were called as balls, Clase threw many of them in the dirt"
  and they were "often ... the first pitch of an at-bat".

Template event: first pitch of a plate appearance, taken for a ball, landing well below
the zone (z_rel < SPIKE_Z, i.e. more than 30% of the zone height under the bottom).

For every pitcher-month with enough first pitches we compare k events out of n with that
pitcher's own baseline rate from his OTHER months (audit mode) or EARLIER months only
(live mode), shrunk toward the league rate. Score = -log10 P(X >= k | n, baseline).
"""
import numpy as np
import pandas as pd
from scipy import stats

SPIKE_Z = -0.3
MIN_FIRST_PITCHES = 20   # per pitcher-month
SHRINK = 150.0           # pseudo first-pitches at the league rate added to every baseline


def template_events(d: pd.DataFrame) -> pd.DataFrame:
    """d = output of pim.score.prepare. Returns first pitches with an `event` flag."""
    fp = d[d["pitch_number"] == 1].copy()
    fp["event"] = (fp["description"].isin(["ball", "blocked_ball"]) & (fp["z_rel"] < SPIKE_Z)).astype(int)
    fp["month"] = fp["game_date"].dt.to_period("M").astype(str)
    return fp


def monthly(d: pd.DataFrame) -> pd.DataFrame:
    fp = template_events(d)
    m = fp.groupby(["pitcher", "month"]).agg(n=("event", "size"), k=("event", "sum")).reset_index()
    league = m["k"].sum() / m["n"].sum()
    m = m.sort_values(["pitcher", "month"])
    tot_n = m.groupby("pitcher")["n"].transform("sum")
    tot_k = m.groupby("pitcher")["k"].transform("sum")
    prev_n = m.groupby("pitcher")["n"].cumsum() - m["n"]
    prev_k = m.groupby("pitcher")["k"].cumsum() - m["k"]

    def tail(k, n, other_k, other_n):
        base = (other_k + SHRINK * league) / (other_n + SHRINK)
        return base, -np.log10(np.clip(stats.binom.sf(k - 1, n, base), 1e-300, 1))

    m["base_audit"], m["score_audit"] = tail(m["k"], m["n"], tot_k - m["k"], tot_n - m["n"])
    m["base_live"], m["score_live"] = tail(m["k"], m["n"], prev_k, prev_n)
    m["rate"] = m["k"] / m["n"]
    m["league_rate"] = league
    return m[m["n"] >= MIN_FIRST_PITCHES].reset_index(drop=True)
