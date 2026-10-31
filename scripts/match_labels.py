"""Match each court-named pitch label to exactly one Statcast row."""
import unicodedata
import pandas as pd
import pybaseball as pb

pb.cache.enable()
CLASE, ORTIZ = 661403, 682847
COLS = ["game_pk", "at_bat_number", "pitch_number", "pitch_type", "release_speed",
        "plate_x", "plate_z", "sz_top", "sz_bot", "balls", "strikes", "description",
        "events", "inning", "outs_when_up", "home_score", "away_score", "bat_score", "fld_score"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return s.replace(".", "").replace(" jr", "").strip()


sc = pd.read_parquet("data/raw/pitchers_clase_ortiz.parquet")
sc["game_date"] = pd.to_datetime(sc["game_date"]).dt.strftime("%Y-%m-%d")
ids = pb.playerid_reverse_lookup(sc["batter"].dropna().unique().tolist(), key_type="mlbam")
ids["batter_name"] = (ids["name_first"] + " " + ids["name_last"]).map(norm)
sc = sc.merge(ids[["key_mlbam", "batter_name"]], left_on="batter", right_on="key_mlbam", how="left")

labels = pd.read_csv("data/labels/court_named_pitches.csv", dtype=str)
rows = []
for _, L in labels[labels.pitcher == "Emmanuel Clase"].iterrows():
    pa = sc[(sc.pitcher == CLASE) & (sc.game_date == L.game_date)
            & (sc.inning == int(L.inning)) & (sc.batter_name == norm(L.batter_name))]
    n_pa = pa["at_bat_number"].nunique()
    hit = pa[pa.pitch_number == int(L.pitch_number_in_pa)]
    status = "matched" if len(hit) == 1 else ("not matched" if len(hit) == 0 else "ambiguous")
    rec = {"label_id": L.label_id, "game_date": L.game_date, "batter_name": L.batter_name,
           "labeled_pitch": L.pitch_number_in_pa, "match_status": status,
           "pitches_in_pa": len(pa), "n_pa_found": n_pa}
    if len(hit) == 1:
        rec.update(hit.iloc[0][COLS + ["batter", "game_type"]].to_dict())
    rows.append(rec)
    # Vavra is reported as "p2": also record pitch 1 of that PA for comparison
    if L.label_id == "3":
        alt = pa[pa.pitch_number == 1]
        if len(alt) == 1:
            r2 = dict(rec, label_id="3-alt-p1", labeled_pitch="1", match_status="alt (pitch 1 check)")
            r2.update(alt.iloc[0][COLS + ["batter", "game_type"]].to_dict())
            rows.append(r2)

m = pd.DataFrame(rows)
m["below_zone_bottom"] = m["plate_z"] < m["sz_bot"]
m.to_csv("data/labels/matched.csv", index=False)
pd.set_option("display.width", 250)
print(m[["label_id", "game_date", "batter_name", "labeled_pitch", "match_status", "pitches_in_pa",
         "game_type", "pitch_type", "release_speed", "description", "plate_z", "sz_bot",
         "below_zone_bottom", "balls", "strikes"]].to_string(index=False))

c = sc[(sc.pitcher == CLASE) & sc.game_type.isin(["R", "F", "D", "L", "W"])]
print("\nClase pitches 2023-25 (reg+post):", len(c), "| first pitches of PA:", (c.pitch_number == 1).sum())
print(c.groupby("game_year").agg(pitches=("pitch_number", "size"), first=("pitch_number", lambda s: (s == 1).sum())))

o = sc[(sc.pitcher == ORTIZ) & sc.game_date.isin(["2025-06-15", "2025-06-27"])]
o.to_csv("data/labels/ortiz_games.csv", index=False)
print("\nOrtiz games:", o.groupby("game_date").agg(team=("home_team", "first"), away=("away_team", "first"),
                                                pitches=("pitch_number", "size"), balls_called=("type", lambda s: (s == "B").sum())))
ob = o[o.type == "B"].sort_values(["game_date", "at_bat_number", "pitch_number"])
print(ob[["game_date", "inning", "at_bat_number", "pitch_number", "batter_name", "balls", "strikes", "pitch_type",
          "release_speed", "description", "plate_x", "plate_z", "sz_bot"]].to_string(index=False))
