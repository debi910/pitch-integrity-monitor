"""Pull pitch-level Statcast for the two named pitchers (fast, per-player queries)."""
import time
import pandas as pd
import pybaseball as pb

pb.cache.enable()
IDS = {661403: "Emmanuel Clase", 682847: "Luis L. Ortiz"}
frames = []
for pid in IDS:
    for y in (2023, 2024, 2025):
        for attempt in range(4):
            try:
                d = pb.statcast_pitcher(f"{y}-03-01", f"{y}-11-30", pid)
                break
            except Exception as e:
                print(f"{pid} {y} attempt {attempt + 1}: {e!r}", flush=True)
                time.sleep(10 * 2 ** attempt)
        frames.append(d)
        print(pid, y, len(d), flush=True)
df = pd.concat(frames, ignore_index=True)
df.to_parquet("data/raw/pitchers_clase_ortiz.parquet", index=False)
