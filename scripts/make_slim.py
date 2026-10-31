"""Write slim, git-friendly parquet copies of raw Statcast pulls to data/slim/.

usage: python scripts/make_slim.py pitchers | 2023 2024 2025
"""
import sys
from pathlib import Path

import pandas as pd

COLS = ["game_date", "game_pk", "game_type", "at_bat_number", "pitch_number", "pitcher", "batter",
        "player_name", "stand", "p_throws", "pitch_type", "release_speed", "release_spin_rate",
        "pfx_x", "pfx_z", "plate_x", "plate_z", "sz_top", "sz_bot", "balls", "strikes",
        "outs_when_up", "inning", "inning_topbot", "on_1b", "on_2b", "on_3b", "bat_score",
        "fld_score", "description", "events", "home_team", "away_team"]
FLOATS = ["release_speed", "release_spin_rate", "pfx_x", "pfx_z", "plate_x", "plate_z", "sz_top", "sz_bot"]
SORT = ["game_date", "game_pk", "at_bat_number", "pitch_number"]
MAX_BYTES = 90 * 1024 * 1024
SLIM = Path("data/slim")
SLIM.mkdir(parents=True, exist_ok=True)


def slim(df, cols):
    df = df[cols].copy()
    df["game_date"] = pd.to_datetime(df["game_date"])
    for b in ("on_1b", "on_2b", "on_3b"):
        df[b] = df[b].notna().astype("int8")
    for c in FLOATS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    return df.sort_values(SORT, ignore_index=True)


def write(df, path):
    df.to_parquet(path, index=False, compression="zstd")
    if path.stat().st_size <= MAX_BYTES:
        print(f"{path}: {len(df):,} rows, {path.stat().st_size / 1e6:.1f} MB")
        return
    path.unlink()
    dates = df["game_date"].sort_values().unique()
    cut = dates[len(dates) // 2]
    for suffix, part in (("_a", df[df.game_date < cut]), ("_b", df[df.game_date >= cut])):
        write(part, path.with_name(path.stem + suffix + path.suffix))


for arg in sys.argv[1:]:
    if arg == "pitchers":
        write(slim(pd.read_parquet("data/raw/pitchers_clase_ortiz.parquet"), COLS),
              SLIM / "pitchers_clase_ortiz.parquet")
    else:
        cols = [c for c in COLS if c != "player_name"]
        write(slim(pd.read_parquet(f"data/raw/statcast_{arg}.parquet"), cols), SLIM / f"statcast_{arg}.parquet")
