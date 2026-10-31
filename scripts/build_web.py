"""Bake every number the web page shows into docs/index.html (single self-contained file).

Reads the scored data and the eval outputs; writes nothing that is not computed here or in eval/.
Run after eval/within_pitcher.py and eval/league_monitor.py.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pim.monitor import monthly  # noqa: E402
from pim.score import baseline_spiked_ball, prepare, score  # noqa: E402

CLASE, ORTIZ = 661403, 682847
KEY = ["game_pk", "at_bat_number", "pitch_number"]


def r(x, n=3):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def embed_images(html: str) -> str:
    """Inline web/img/<name>.jpg as data URIs; drop the <!--IMG:name--> block when the photo is absent."""
    import base64
    import re
    credits = {}
    cpath = ROOT / "web/img/CREDITS.md"
    if cpath.exists():  # lines like: - hero.jpg: "Title" by Author, CC BY-SA 4.0, https://commons...
        for line in cpath.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*[-*]\s*`?(\w+)\.jpg`?\s*[:|]\s*(.+)", line)
            if m:
                credits[m.group(1)] = re.sub(r"https?://\S+", "", m.group(2)).strip(" ,|")
    for name in ["hero", "pitcher", "plate", "ball"]:
        img = ROOT / f"web/img/{name}.jpg"
        block = re.compile(rf"<!--IMG:{name}-->(.*?)<!--/IMG:{name}-->", re.S)
        if img.exists():
            uri = "data:image/jpeg;base64," + base64.b64encode(img.read_bytes()).decode()
            html = block.sub(lambda m: m.group(1), html)
            html = html.replace(f"__IMG_{name}__", uri).replace(f"__CREDIT_{name}__", "Photo: " + credits.get(name, "Wikimedia Commons"))
        else:
            html = block.sub("", html)
    return html


def main():
    d = score(pd.read_parquet(ROOT / "data/slim/pitchers_clase_ortiz.parquet"))
    lab = pd.read_csv(ROOT / "data/labels/matched.csv")
    lab = lab[lab["match_status"] == "matched"][["label_id", "batter_name"] + KEY]
    c = d[d["pitcher"] == CLASE].merge(lab, on=KEY, how="left").reset_index(drop=True)
    c["rank_v1"] = c["pim_score"].rank(ascending=False, method="first").fillna(len(c)).astype(int)
    c["rank_b1"] = pd.Series(baseline_spiked_ball(c)).rank(ascending=False, method="first").astype(int)

    pitches = [{
        "d": row.game_date.strftime("%Y-%m-%d"), "t": row.pitch_type, "v": r(row.release_speed, 1),
        "x": r(row.plate_x, 2), "z": r(row.plate_z, 2), "top": r(row.sz_top, 2), "bot": r(row.sz_bot, 2),
        "fp": int(row.pitch_number == 1), "res": row.description, "inn": int(row.inning),
        "c": f"{int(row.balls)}-{int(row.strikes)}",
        "r1": int(row.rank_v1), "rb": int(row.rank_b1),
        **({"id": int(row.label_id), "bat": row.batter_name, "pl": r(row.p_location, 4), "pc": r(row.p_choice, 3),
            "pv": r(row.p_velocity, 3)} if pd.notna(row.label_id) else {}),
    } for row in c.itertuples()]

    out = {"pitches": pitches}
    within = ROOT / "results/within_clase.json"
    out["within"] = json.loads(within.read_text()) if within.exists() else None

    league = ROOT / "results/league_monitor.json"
    out["league"] = json.loads(league.read_text()) if league.exists() else None
    nm = ROOT / "results/named_pitcher_months.csv"
    if nm.exists():
        months = pd.read_csv(nm)
    else:  # fall back to the two-pitcher file; flagged in the page as provisional
        months = monthly(prepare(d[d["pitcher"].isin([CLASE, ORTIZ])]))
        months["pitcher"] = months["pitcher"].map({CLASE: "Emmanuel Clase", ORTIZ: "Luis L. Ortiz"})
        months["league_pct_audit"] = np.nan
    named_months = set(c.loc[c["label_id"].notna(), "game_date"].dt.to_period("M").astype(str))
    out["months"] = [{"p": row.pitcher, "m": row.month, "n": int(row.n), "k": int(row.k), "rate": r(row.rate, 4),
                      "base": r(row.base_audit, 4), "s": r(row.score_audit, 3), "sl": r(row.score_live, 3),
                      "pct": r(row.league_pct_audit, 2),
                      "named": int(row.pitcher == "Emmanuel Clase" and row.month in named_months)}
                     for row in months.itertuples()]
    cells = ROOT / "results/league_cells_anon.csv"
    if cells.exists():
        cl = pd.read_csv(cells)
        out["cells"] = {"s": [r(v, 2) for v in cl["score_audit"]], "named": cl["is_named"].astype(int).tolist(),
                        "label": cl["label"].astype(int).tolist(), "n_months": int(cl["month"].nunique())}
    else:
        out["cells"] = None

    html = (ROOT / "web/template.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(out, separators=(",", ":")))
    html = html.replace("/*__D3__*/", (ROOT / "web/vendor/d3.min.js").read_text(encoding="utf-8"))  # d3 v7.9.0, ISC
    html = embed_images(html)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/index.html").write_text(html, encoding="utf-8")
    print(f"docs/index.html: {len(html)/1e3:.0f} kB, league={'yes' if out['league'] else 'pending'}")


if __name__ == "__main__":
    main()
