"""Pitcher-relative surprise scores.

Every pitch is compared only with the same pitcher's EARLIER games (no look-ahead),
the way a live monitor would see it. Three questions, each answered as a tail
probability (p-value) against his own history:

  location  - is this spot unusual for this pitch type, to this batter side?
  choice    - is this pitch type unusual for him in this count?
  velocity  - is this speed unusual for this pitch type?

The p-values are combined with Fisher's method into one score:
  pim_score = -log10(combined p). Higher = stranger for THIS pitcher.

Nothing here is fitted to the court-named pitches. Settings are fixed constants.
"""
import numpy as np
import pandas as pd
from scipy import stats

GAME_TYPES = ["R", "F", "D", "L", "W"]  # regular season + postseason
MIN_PRIOR = 30        # prior pitches of this type needed before we score location/velocity
CHOICE_PRIOR = 20.0   # Dirichlet pseudo-count pulling count-specific mix toward his overall mix
HALF_PLATE = 0.83     # ft, half plate width plus a ball radius
COUNTS = [(b, s) for b in range(4) for s in range(3)]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["game_type"].isin(GAME_TYPES)].copy()
    d = d.dropna(subset=["pitch_type", "plate_x", "plate_z", "sz_top", "sz_bot"])
    d = d[d["pitch_type"] != "PO"]  # pitchouts/pickoff markers
    d["game_date"] = pd.to_datetime(d["game_date"])
    side = np.where(d["stand"] == "L", -1.0, 1.0)
    d["x_rel"] = d["plate_x"] * side                         # + = away from a RHB's body side
    d["z_rel"] = (d["plate_z"] - d["sz_bot"]) / (d["sz_top"] - d["sz_bot"])  # 0..1 = in zone
    d = d.sort_values(["pitcher", "game_date", "game_pk", "at_bat_number", "pitch_number"])
    return d.reset_index(drop=True)


def _prior_by_game(d: pd.DataFrame, keys: list[str], cols: dict[str, pd.Series]) -> pd.DataFrame:
    """Sum `cols` per (keys, game), then cumulate over earlier games only."""
    g = d[keys + ["game_date", "game_pk"]].copy()
    for k, v in cols.items():
        g[k] = v.values
    per_game = g.groupby(keys + ["game_date", "game_pk"], sort=True).sum().reset_index()
    per_game = per_game.sort_values(keys + ["game_date", "game_pk"])
    summed = per_game.groupby(keys)[list(cols)].cumsum() - per_game[list(cols)]
    per_game[list(cols)] = summed
    return d[keys + ["game_pk"]].merge(per_game.drop(columns="game_date"), on=keys + ["game_pk"], how="left")


def location_p(d: pd.DataFrame) -> np.ndarray:
    x, z = d["x_rel"], d["z_rel"]
    one = pd.Series(1.0, index=d.index)
    p = _prior_by_game(d, ["pitcher", "pitch_type", "stand"], {
        "n": one, "sx": x, "sz": z, "sxx": x * x, "szz": z * z, "sxz": x * z})
    n = p["n"].to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        mx, mz = p["sx"] / n, p["sz"] / n
        vxx = p["sxx"] / n - mx ** 2
        vzz = p["szz"] / n - mz ** 2
        vxz = p["sxz"] / n - mx * mz
        det = vxx * vzz - vxz ** 2
        dx, dz = x.to_numpy() - mx.to_numpy(), z.to_numpy() - mz.to_numpy()
        m2 = (vzz * dx * dx - 2 * vxz * dx * dz + vxx * dz * dz) / det
    out = stats.chi2.sf(m2, df=2)
    out[(n < MIN_PRIOR) | ~(det > 0)] = np.nan
    return np.asarray(out, dtype=float)


def velocity_p(d: pd.DataFrame) -> np.ndarray:
    v = d["release_speed"].astype(float)
    one = pd.Series(1.0, index=d.index)
    p = _prior_by_game(d, ["pitcher", "pitch_type"], {"n": one, "sv": v, "svv": v * v})
    n = p["n"].to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = p["sv"].to_numpy() / n
        sd = np.sqrt(np.maximum(p["svv"].to_numpy() / n - mu ** 2, 0)) + 0.3  # 0.3 mph floor
        zv = (v.to_numpy() - mu) / sd
    out = 2 * stats.norm.sf(np.abs(zv))
    out[(n < MIN_PRIOR) | np.isnan(zv)] = np.nan
    return out


def choice_p(d: pd.DataFrame) -> np.ndarray:
    """P(this pitch type | pitcher, count) from earlier games, shrunk to his overall mix.
    Used as a tail probability: a pitch he throws 5% of the time in this count gets p=0.05."""
    one = pd.Series(1.0, index=d.index)
    cnt = _prior_by_game(d, ["pitcher", "balls", "strikes", "pitch_type"], {"n": one})["n"].to_numpy()
    tot = _prior_by_game(d, ["pitcher", "balls", "strikes"], {"n": one})["n"].to_numpy()
    typ = _prior_by_game(d, ["pitcher", "pitch_type"], {"n": one})["n"].to_numpy()
    allp = _prior_by_game(d, ["pitcher"], {"n": one})["n"].to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        overall = (typ + 0.5) / (allp + 0.5 * 6)
        prob = (cnt + CHOICE_PRIOR * overall) / (tot + CHOICE_PRIOR)
    prob[allp < MIN_PRIOR * 3] = np.nan
    return np.clip(prob, 1e-6, 1.0)


def score(df: pd.DataFrame) -> pd.DataFrame:
    d = prepare(df)
    d["p_location"] = location_p(d)
    d["p_choice"] = choice_p(d)
    d["p_velocity"] = velocity_p(d)
    ps = d[["p_location", "p_choice", "p_velocity"]].to_numpy()
    ok = ~np.isnan(ps).any(axis=1)
    fisher = -2 * np.log(np.clip(ps, 1e-12, 1)).sum(axis=1)
    comb = stats.chi2.sf(fisher, df=6)
    d["pim_score"] = np.where(ok, -np.log10(np.clip(comb, 1e-300, 1)), np.nan)
    return d


# ---------- baselines (the "simple methods" we must beat) ----------

def baseline_spiked_ball(d: pd.DataFrame) -> np.ndarray:
    """B1: how far below the zone a pitch called/taken as a ball landed. Non-balls score -inf."""
    is_ball = d["description"].isin(["ball", "blocked_ball"])
    depth = (d["sz_bot"] - d["plate_z"]).to_numpy()
    return np.where(is_ball, depth, -np.inf)


def baseline_out_of_zone(d: pd.DataFrame) -> np.ndarray:
    """B2: plain distance outside the rulebook zone, same rule for every pitcher."""
    dx = np.maximum(np.abs(d["plate_x"].to_numpy()) - HALF_PLATE, 0)
    dz = np.maximum(d["sz_bot"] - d["plate_z"], 0) + np.maximum(d["plate_z"] - d["sz_top"], 0)
    return np.hypot(dx, dz.to_numpy())
