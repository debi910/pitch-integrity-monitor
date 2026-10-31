"""Coach mode: has a pitcher's command or velocity drifted below HIS OWN earlier level?

Same idea as the integrity monitor (each pitcher judged only against himself), aimed at a
pitching coach or front office instead of an integrity desk. Live mode only: every month is
compared with that pitcher's EARLIER months, so it could run on the first morning of a month.

Two signals per pitcher-month:
  command   - share of non-competitive pitches (well outside the zone, see WILD_*), binomial
              tail vs his earlier rate shrunk to the league rate (one-sided: worse command)
  velocity  - mean speed of his primary fastball vs his earlier mean (one-sided: slower)
Combined with Fisher's method: drift_score = -log10 p.  Constants are fixed; nothing is fitted
to injuries.
"""
import numpy as np
import pandas as pd
from scipy import stats

WILD_X = 1.33        # ft from plate centre (half plate 0.83 + 6 in)
WILD_Z_LOW = -0.5    # zone heights below the bottom of the zone
WILD_Z_HIGH = 1.5    # zone heights from the bottom (i.e. half a zone above the top)
FASTBALLS = ["FF", "SI", "FC"]
MIN_PITCHES = 60     # pitches in the month
MIN_PRIOR = 200      # earlier pitches needed before we score
MIN_FB = 15          # primary-fastball pitches in the month for the velocity signal
SHRINK = 300.0       # pseudo pitches at the league wild rate
VELO_SD_FLOOR = 0.7  # mph, floor on the per-pitch sd
VELO_TAU = 0.6       # mph, normal month-to-month wobble in a pitcher's mean fastball speed


def pitcher_months(d: pd.DataFrame) -> pd.DataFrame:
    """d = output of pim.score.prepare (all pitches). One row per pitcher-month with both signals."""
    d = d.copy()
    d["month"] = d["game_date"].dt.to_period("M").astype(str)
    d["wild"] = ((d["x_rel"].abs() > WILD_X) | (d["z_rel"] < WILD_Z_LOW) | (d["z_rel"] > WILD_Z_HIGH)).astype(int)
    m = d.groupby(["pitcher", "month"]).agg(n=("wild", "size"), k=("wild", "sum"),
                                            last_game=("game_date", "max")).reset_index()
    lg = m.groupby("month")[["k", "n"]].sum().sort_index()
    cum = lg.cumsum() - lg  # league totals from EARLIER months only (no look-ahead)
    lg_rate = (cum["k"] / cum["n"]).where(cum["n"] > 0, lg["k"] / lg["n"])
    m = m.sort_values(["pitcher", "month"])
    league = m["month"].map(lg_rate)
    prev_n = m.groupby("pitcher")["n"].cumsum() - m["n"]
    prev_k = m.groupby("pitcher")["k"].cumsum() - m["k"]
    base = (prev_k + SHRINK * league) / (prev_n + SHRINK)
    m["wild_rate"], m["wild_base"], m["prior_n"] = m["k"] / m["n"], base, prev_n
    m["p_command"] = stats.binom.sf(m["k"] - 1, m["n"], base)

    # primary fastball = his most-thrown of FF/SI/FC over his EARLIER months (fallback: this month)
    fb = d[d["pitch_type"].isin(FASTBALLS) & d["release_speed"].notna()]
    g = fb.groupby(["pitcher", "month", "pitch_type"])["release_speed"].agg(["size", "sum", lambda s: (s ** 2).sum()])
    g.columns = ["c", "s", "ss"]
    g = g.reset_index().sort_values(["pitcher", "pitch_type", "month"])
    for col in ["c", "s", "ss"]:
        g["prev_" + col] = g.groupby(["pitcher", "pitch_type"])[col].cumsum() - g[col]
    g["rank_key"] = g["prev_c"].where(g["prev_c"] > 0, g["c"] * 1e-6)
    prim = g.sort_values("rank_key", ascending=False).drop_duplicates(["pitcher", "month"])
    with np.errstate(invalid="ignore", divide="ignore"):
        prev_mean = prim["prev_s"] / prim["prev_c"]
        prev_sd = np.sqrt(np.maximum(prim["prev_ss"] / prim["prev_c"] - prev_mean ** 2, VELO_SD_FLOOR ** 2))
        mean = prim["s"] / prim["c"]
        z = (mean - prev_mean) / np.sqrt(prev_sd ** 2 / prim["c"] + VELO_TAU ** 2)
    prim = prim.assign(fb_type=prim["pitch_type"], fb_n=prim["c"], velo=mean, velo_base=prev_mean,
                       velo_drop=prev_mean - mean, p_velocity=stats.norm.cdf(z))
    ok = (prim["fb_n"] >= MIN_FB) & (prim["prev_c"] >= 30)
    prim.loc[~ok, ["p_velocity", "velo_drop"]] = np.nan
    m = m.merge(prim[["pitcher", "month", "fb_type", "fb_n", "velo", "velo_base", "velo_drop", "p_velocity"]],
                on=["pitcher", "month"], how="left")

    pc = np.clip(m["p_command"].to_numpy(float), 1e-300, 1)
    pv = np.clip(m["p_velocity"].fillna(1.0).to_numpy(float), 1e-300, 1)  # missing velocity = no evidence
    m["drift_score"] = -np.log10(np.clip(stats.chi2.sf(-2 * (np.log(pc) + np.log(pv)), 4), 1e-300, 1))
    m["command_score"] = -np.log10(pc)
    m["league_wild_rate"] = league
    return m[(m["n"] >= MIN_PITCHES) & (m["prior_n"] >= MIN_PRIOR)].reset_index(drop=True)
