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
from pim.monitor import monthly, template_events  # noqa: E402
from pim.score import baseline_spiked_ball, prepare, score  # noqa: E402

CLASE, ORTIZ = 661403, 682847
KEY = ["game_pk", "at_bat_number", "pitch_number"]


def r(x, n=3):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def embed_images(html: str) -> str:
    """Inline web/img/<name>.jpg as data URIs; drop the <!--IMG:name--> block when the photo is absent."""
    import base64
    import re
    credits, footer = {}, []
    cpath = ROOT / "web/img/CREDITS.md"
    if cpath.exists():  # "## hero.jpg (...)" then "- Author: ...", "- Licence: X (url)", "- Source: url"
        for sec in re.split(r"^## ", cpath.read_text(encoding="utf-8"), flags=re.M)[1:]:
            name = sec.split(".jpg")[0].strip()
            f = dict(re.findall(r"^- (\w+): (.+)$", sec, flags=re.M))
            lic = re.sub(r"\s*\(.*\)", "", f.get("Licence", ""))
            credits[name] = f"{f.get('Author', '?')}, {lic}, Wikimedia Commons"
            footer.append(f'<a href="{f.get("Source", "#")}" target="_blank" rel="noopener">{f.get("File", name)}</a> '
                          f'by {f.get("Author", "?")} ({lic})')
    html = html.replace("<!--__CREDITS__-->", "Photos: " + " · ".join(footer) if footer else "")
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

    # The case file an integrity desk would have opened when the LIVE monitor fired (data through May 31 2025)
    ev = template_events(prepare(d[d["pitcher"] == CLASE]))
    ev = ev[(ev["month"] == "2025-05") & (ev["event"] == 1)].merge(lab, on=KEY, how="left")
    cm = next(x for x in out["months"] if x["p"] == "Emmanuel Clase" and x["m"] == "2025-05")
    out["case"] = {"month": "2025-05", "issued": "2025-06-01", "n": cm["n"], "k": cm["k"], "score_live": cm["sl"],
                   "events": [{"d": e.game_date.strftime("%Y-%m-%d"), "g": int(e.game_pk), "inn": int(e.inning),
                               "t": e.pitch_type, "v": r(e.release_speed, 1), "z": r(e.z_rel, 2),
                               "res": e.description, "lead": int(e.fld_score - e.bat_score),
                               "opp": e.away_team if e.inning_topbot == "Top" else e.home_team,
                               "named": int(pd.notna(e.label_id))} for e in ev.itertuples()]}
    live = pd.read_csv(ROOT / "results/league_cells_anon.csv") if (ROOT / "results/league_cells_anon.csv").exists() else None
    if live is not None and "score_live" in live:
        out["case"]["same_day_alerts"] = int(((live["month"] == "2025-05") & (live["score_live"] >= 3)).sum())
    tf = ROOT / "results/threshold_free.json"
    out["tfree"] = json.loads(tf.read_text()) if tf.exists() else None
    pw = ROOT / "results/power.json"
    out["power"] = json.loads(pw.read_text()) if pw.exists() else None
    rob = ROOT / "results/robustness.json"
    out["robust"] = json.loads(rob.read_text()) if rob.exists() else None

    html = (ROOT / "web/template.html").read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(out, separators=(",", ":")))
    html = html.replace("/*__D3__*/", (ROOT / "web/vendor/d3.min.js").read_text(encoding="utf-8"))  # d3 v7.9.0, ISC
    html = embed_images(html)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/index.html").write_text(html, encoding="utf-8")
    print(f"docs/index.html: {len(html)/1e3:.0f} kB, league={'yes' if out['league'] else 'pending'}")


if __name__ == "__main__":
    main()
