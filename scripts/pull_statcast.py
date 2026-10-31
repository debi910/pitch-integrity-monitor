"""Pull full-league Statcast pitch data (regular season + postseason) month by month.

Politeness: one month at a time, days within a month fetched by at most 3 worker
threads (pybaseball's default pool is ~cpu+4 threads). Monthly chunks are saved so
the pull is resumable. Final output: data/raw/statcast_{year}.parquet
"""
import concurrent.futures as cf
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pybaseball as pb
from pybaseball.statcast import _small_request

pb.cache.enable()
RAW = Path("data/raw")
CHUNKS = RAW / "chunks"
CHUNKS.mkdir(parents=True, exist_ok=True)

SEASONS = {  # opening day (incl. international openers) -> last WS game
    2023: (date(2023, 3, 30), date(2023, 11, 1)),
    2024: (date(2024, 3, 20), date(2024, 10, 30)),
    2025: (date(2025, 3, 18), date(2025, 11, 1)),
}
KEEP_GAME_TYPES = {"R", "F", "D", "L", "W"}  # regular, wild card, DS, CS, WS
WORKERS = 3


def fetch_day(d):
    for attempt in range(4):
        try:
            return _small_request(d.isoformat(), d.isoformat())
        except Exception as e:  # network hiccup / Savant 5xx
            print(f"  {d} attempt {attempt + 1} failed: {e!r}", flush=True)
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"giving up on {d}")


def months(start, end):
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield cur, min(nxt - timedelta(days=1), end)
        cur = nxt


def pull_season(year):
    start, end = SEASONS[year]
    parts = []
    for m_start, m_end in months(start, end):
        out = CHUNKS / f"{year}_{m_start:%m}.parquet"
        if out.exists():
            parts.append(pd.read_parquet(out))
            continue
        t = time.time()
        days = [m_start + timedelta(n) for n in range((m_end - m_start).days + 1)]
        with cf.ThreadPoolExecutor(WORKERS) as ex:
            frames = [f for f in ex.map(fetch_day, days) if f is not None and len(f)]
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if len(df):
            df = df[df["game_type"].isin(KEEP_GAME_TYPES)]
        df.to_parquet(out, index=False)
        parts.append(df)
        print(f"{year}-{m_start:%m}: {len(df):,} rows in {time.time() - t:.0f}s", flush=True)
    season = pd.concat(parts, ignore_index=True)
    season = season.drop_duplicates(["game_pk", "at_bat_number", "pitch_number"])
    season = season.sort_values(["game_date", "game_pk", "at_bat_number", "pitch_number"])
    season.to_parquet(RAW / f"statcast_{year}.parquet", index=False)
    print(f"== {year}: {len(season):,} rows", flush=True)


if __name__ == "__main__":
    for y in map(int, sys.argv[1:] or SEASONS):
        pull_season(y)
