"""Extract the real numbers the video draws into build/data.json (Statcast + results/)."""
import json
import numpy as np
import pandas as pd
from common import ROOT, BUILD

CLASE = 661403
raw = pd.read_parquet(ROOT / "data/raw/pitchers_clase_ortiz.parquet")
c = raw[(raw.pitcher == CLASE) & raw.game_type.isin(list("RFDLW"))].copy()
c["game_date"] = pd.to_datetime(c["game_date"]).dt.strftime("%Y-%m-%d")
K = ["release_pos_x", "release_pos_y", "release_pos_z", "vx0", "vy0", "vz0", "ax", "ay", "az",
     "plate_x", "plate_z", "sz_top", "sz_bot", "release_speed"]
kin = lambda r: {k: float(r[k]) for k in K}

v = c[(c.game_date == "2024-10-05") & (c.inning == 9) & (c.pitch_number == 1) & (c.batter == 663837)]
assert len(v) == 1
fp = c[(c.pitch_number == 1) & (c.pitch_type == "SL")].dropna(subset=K)
ghosts = [kin(r) for _, r in fp.sample(40, random_state=7).iterrows()]

m = pd.read_csv(ROOT / "data/labels/matched.csv", dtype={"label_id": str})
m = m[~m.label_id.str.contains("alt")]
named = m[["label_id", "game_date", "batter_name", "pitch_type", "release_speed", "description",
           "plate_x", "plate_z", "sz_bot", "sz_top"]].to_dict("records")

tracked = c.dropna(subset=["pitch_type"]).sort_values(["game_date", "game_pk", "at_bat_number", "pitch_number"])
keys = set(zip(m.game_pk.astype(int), m.at_bat_number.astype(int), m.pitch_number.astype(int)))
flags = [(int(a), int(b), int(p)) in keys for a, b, p in zip(tracked.game_pk, tracked.at_bat_number, tracked.pitch_number)]
not_ball = set(m[m.description != "ball"].game_pk.astype(int).astype(str) + "_" + m[m.description != "ball"].at_bat_number.astype(int).astype(str))
nb = [f"{int(a)}_{int(b)}" in not_ball and f for a, b, f in zip(tracked.game_pk, tracked.at_bat_number, flags)]

months = pd.read_csv(ROOT / "results/named_pitcher_months.csv")
cm = months[months.pitcher == "Emmanuel Clase"][["month", "n", "k", "rate", "base_audit", "label"]].to_dict("records")

cells = pd.read_csv(ROOT / "results/league_cells_anon.csv")
cells = cells.sort_values("score_audit", ascending=False).reset_index(drop=True)
league = {"scores": cells.score_audit.round(3).tolist(), "named": cells.is_named.astype(bool).tolist(),
          "label": cells.label.astype(int).tolist()}

lm = json.loads((ROOT / "results/league_monitor.json").read_text())
wc = json.loads((ROOT / "results/within_clase.json").read_text())

rng = np.random.default_rng(3)
sc = pd.read_parquet(ROOT / "data/slim/statcast_2025.parquet", columns=["plate_x", "plate_z"]).dropna()
cloud = sc.sample(9000, random_state=1)[["plate_x", "plate_z"]].round(3).values.tolist()

out = {"vierling": kin(v.iloc[0]), "ghosts": ghosts, "named": named, "waffle_flags": flags, "waffle_notball": nb,
       "clase_months": cm, "league": league, "league_monitor": lm, "within_clase": wc, "cloud": cloud}
BUILD.mkdir(exist_ok=True, parents=True)
(BUILD / "data.json").write_text(json.dumps(out))
print("waffle", len(flags), sum(flags), sum(nb), "| cells", len(cells), "| clase months", len(cm),
      "| rank of named", [i + 1 for i, n in enumerate(league["named"]) if n and league["label"][i]][:8])
