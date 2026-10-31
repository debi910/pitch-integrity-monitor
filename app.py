"""Pitch Integrity Monitor: Streamlit app.

Run:  streamlit run app.py
"""
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pim.monitor import SPIKE_Z, monthly, template_events
from pim.score import baseline_spiked_ball, prepare, score

ROOT = Path(__file__).parent
CLASE, ORTIZ = 661403, 682847
NAMES = {CLASE: "Emmanuel Clase", ORTIZ: "Luis L. Ortiz"}

INK, PAPER, MUTED, AMBER, RED, TEAL, GRID = "#E8E4D8", "#14171C", "#8B9099", "#F2B33D", "#E5533D", "#4FB3A9", "#2A2F37"

st.set_page_config(page_title="Pitch Integrity Monitor", page_icon="⚾", layout="wide")
st.markdown(f"""
<style>
  .stApp {{ background:{PAPER}; color:{INK}; }}
  h1, h2, h3 {{ font-family: 'Georgia', serif; letter-spacing:.2px; }}
  .tag {{ display:inline-block; font-family:ui-monospace,Menlo,monospace; font-size:12px;
          padding:2px 8px; border:1px solid {AMBER}; color:{AMBER}; border-radius:3px; margin-right:6px; }}
  .allege {{ border-left:4px solid {AMBER}; background:#1C2028; padding:10px 14px; margin:6px 0 14px 0;
             font-size:14px; color:{INK}; }}
  .big {{ font-size:42px; font-family:Georgia,serif; line-height:1.05; color:{INK}; }}
  .sub {{ color:{MUTED}; font-size:14px; }}
  .card {{ background:#1C2028; border:1px solid {GRID}; border-radius:6px; padding:14px 16px; }}
  .mono {{ font-family:ui-monospace,Menlo,monospace; }}
  [data-testid="stMetricValue"] {{ font-family:Georgia,serif; }}
</style>""", unsafe_allow_html=True)

ALLEGATION = ("<div class='allege'><b>Allegations, not findings.</b> The 18 pitches are those named by federal "
              "prosecutors in a Sept 18 2026 court filing (EDNY 25-CR-346). Both pitchers have pleaded not guilty. "
              "This tool measures how <i>unusual</i> pitches are for a pitcher. Unusual is not proof of anything.</div>")


@st.cache_data
def load_named():
    raw = pd.read_parquet(ROOT / "data/slim/pitchers_clase_ortiz.parquet")
    d = score(raw)
    lab = pd.read_csv(ROOT / "data/labels/matched.csv")
    lab = lab[lab["match_status"] == "matched"][["label_id", "game_pk", "at_bat_number", "pitch_number"]]
    d = d.merge(lab, on=["game_pk", "at_bat_number", "pitch_number"], how="left")
    d["named"] = d["label_id"].notna()
    return d


@st.cache_data
def load_json(name):
    p = ROOT / "results" / name
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data
def load_csv(name):
    p = ROOT / "results" / name
    return pd.read_csv(p) if p.exists() else None


def zone_fig(df_cloud, df_mark, title, sz_top=3.4, sz_bot=1.6):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-0.83, x1=0.83, y0=sz_bot, y1=sz_top, line=dict(color=INK, width=2))
    fig.add_shape(type="line", x0=-1.6, x1=1.6, y0=0, y1=0, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_trace(go.Scatter(x=df_cloud["plate_x"], y=df_cloud["plate_z"], mode="markers",
                             marker=dict(size=5, color=TEAL, opacity=.28), name="his other first-pitch sliders",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df_mark["plate_x"], y=df_mark["plate_z"], mode="markers",
                             marker=dict(size=15, color=AMBER, line=dict(color=PAPER, width=2), symbol="x"),
                             name="court-named pitch",
                             text=df_mark["hover"], hoverinfo="text"))
    fig.add_annotation(x=1.45, y=0.08, text="ground", showarrow=False, font=dict(color=MUTED, size=11))
    fig.update_layout(title=title, height=460, paper_bgcolor=PAPER, plot_bgcolor=PAPER, font=dict(color=INK),
                      xaxis=dict(range=[-2.5, 2.5], title="feet from plate centre (catcher view)", gridcolor=GRID,
                                 zeroline=False),
                      yaxis=dict(range=[-1.5, 5], title="feet above ground", gridcolor=GRID, zeroline=False,
                                 scaleanchor="x"),
                      legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=50, b=10))
    return fig


def monthly_fig(m, named_months, title):
    fig = go.Figure()
    x = m["month"]
    fig.add_trace(go.Bar(x=x, y=m["rate"] * 100, name="first-pitch balls in the dirt (%)",
                         marker_color=[AMBER if mo in named_months else "#59606B" for mo in x],
                         hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=m["base_audit"] * 100, mode="lines", name="his own baseline",
                             line=dict(color=TEAL, width=2, dash="dash")))
    fig.update_layout(title=title, height=360, paper_bgcolor=PAPER, plot_bgcolor=PAPER, font=dict(color=INK),
                      yaxis=dict(title="% of first pitches", gridcolor=GRID), xaxis=dict(type="category"),
                      legend=dict(orientation="h", y=-0.25), margin=dict(l=10, r=10, t=50, b=10), bargap=.25)
    return fig


d = load_named()
clase = d[d["pitcher"] == CLASE]
within = load_json("within_clase.json")
league = load_json("league_monitor.json")
named_months_df = load_csv("named_pitcher_months.csv")
cells = load_csv("league_cells_anon.csv")

# ---------------------------------------------------------------- header
st.markdown("<span class='tag'>MLB · STATCAST 2023–25</span><span class='tag'>INTEGRITY DESK</span>",
            unsafe_allow_html=True)
st.markdown("<div class='big'>Can pitch data catch a rigged pitch?</div>", unsafe_allow_html=True)
st.markdown("<div class='sub'>A pitcher-relative monitor tested on the 18 pitches federal prosecutors say "
            "were sold to bettors, and on every MLB pitcher-month from 2023 to 2025.</div>", unsafe_allow_html=True)
st.write("")

tabs = st.tabs(["① The pitch", "② One pitch isn't enough", "③ The pattern monitor", "④ Try it", "⑤ Method & limits"])

# ---------------------------------------------------------------- tab 1
with tabs[0]:
    st.markdown(ALLEGATION, unsafe_allow_html=True)
    c1, c2 = st.columns([1.25, 1])
    named = clase[clase["named"]].copy()
    named["hover"] = (named["game_date"].dt.strftime("%b %d %Y") + " · inning " + named["inning"].astype(str) +
                      "<br>" + named["pitch_type"] + " " + named["release_speed"].round(1).astype(str) + " mph · " +
                      named["description"])
    cloud = clase[(clase["pitch_number"] == 1) & (clase["pitch_type"] == "SL") & ~clase["named"]]
    with c1:
        pick = st.selectbox("Court-named pitch", named["hover"].str.replace("<br>", " — ").tolist(),
                            index=int(np.argmax(named["game_date"].dt.strftime("%Y-%m-%d") == "2024-10-05")))
        row = named.iloc[named["hover"].str.replace("<br>", " — ").tolist().index(pick)]
        st.plotly_chart(zone_fig(cloud, named[named.index == row.name],
                                 "Where it crossed the plate vs his normal first-pitch sliders",
                                 float(row["sz_top"]), float(row["sz_bot"])), width="stretch", theme=None)
    with c2:
        st.markdown("#### Oct 5 2024 · ALDS Game 1 · 9th inning")
        st.markdown("Cleveland won 7–0. Clase's first pitch to Matt Vierling is a 93 mph slider that bounces in the dirt. "
                    "Nobody in the park blinks. Two years later it is on the prosecutors' list.")
        st.markdown(f"**Selected pitch evidence** <span class='mono'>(vs his own earlier games)</span>",
                    unsafe_allow_html=True)
        e1, e2, e3 = st.columns(3)
        e1.metric("Location", f"p = {row['p_location']:.3f}", help="How rare this spot is for this pitch type, "
                                                                     "to this batter side, in his earlier games.")
        e2.metric("Pitch choice", f"p = {row['p_choice']:.2f}", help="How often he picks this pitch in this count.")
        e3.metric("Velocity", f"p = {row['p_velocity']:.2f}", help="How unusual the speed is for this pitch type.")
        rk = int(clase["pim_score"].rank(ascending=False, method="min")[row.name])
        st.markdown(f"Rank among his {len(clase):,} pitches: **#{rk}**")
        n_not_ball = int((~named["description"].isin(["ball", "blocked_ball"])).sum())
        st.markdown(f"<div class='sub'>{n_not_ball} of the 18 named pitches were not balls at all "
                    "(called strikes, fouls, swinging strikes). Bets were also placed on pitch speed and type.</div>",
                    unsafe_allow_html=True)

# ---------------------------------------------------------------- tab 2
with tabs[1]:
    st.markdown("### Result 1: single pitches hide well")
    st.markdown("We froze our pitch-level model in git **before** looking at where the named pitches ranked. "
                "Then we ranked all of Clase's 2023–25 pitches. The simple rule won.")
    if within:
        rows = []
        for k, v in within["methods"].items():
            rows.append({"method": k, "avg precision": round(v["avg_precision"], 3),
                         "95% CI": f"{v['ap_95ci'][0]:.2f}–{v['ap_95ci'][1]:.2f}",
                         "named in top 18": v["hits_top18"], "in top 100": v["hits_top100"],
                         "median rank": v["median_rank"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(f"{within['n_labels']} named pitches among {within['n_pitches']:,} Clase pitches "
                   f"(base rate {within['prevalence']*100:.2f}%). Bootstrap 95% intervals, 2,000 resamples.")
    ranks = pd.DataFrame({
        "ours v1": clase["pim_score"].rank(ascending=False, method="min")[clase["named"]].values,
        "spiked-ball rule": pd.Series(baseline_spiked_ball(clase), index=clase.index).rank(
            ascending=False, method="min")[clase["named"]].values})
    fig = go.Figure()
    for col, colr in [("ours v1", AMBER), ("spiked-ball rule", TEAL)]:
        fig.add_trace(go.Scatter(x=ranks[col], y=[col] * len(ranks), name=col, mode="markers",
                                 marker=dict(color=colr, size=11, opacity=.85, line=dict(color=PAPER, width=1))))
    fig.update_layout(height=280, paper_bgcolor=PAPER, plot_bgcolor=PAPER, font=dict(color=INK),
                      xaxis=dict(type="log", title="rank among his pitches (1 = most suspicious; log scale)",
                                 gridcolor=GRID), yaxis=dict(gridcolor=GRID), showlegend=False,
                      margin=dict(l=140, r=20, t=10, b=60))
    st.plotly_chart(fig, width="stretch", theme=None)
    st.markdown("**What this means:** a rigged ball in the dirt looks like an ordinary miss, and a third of the "
                "named pitches were not balls at all. Asking *'is this one pitch suspicious?'* is the wrong question.")

# ---------------------------------------------------------------- tab 3
with tabs[2]:
    st.markdown("### Result 2: patterns show up")
    st.markdown("Instead of single pitches, watch a pitcher's **own rate** of the pattern prosecutors described: "
                "*first pitch of an at-bat, taken for a ball, in the dirt*. Alert when that rate jumps above his "
                "own baseline.")
    m_named = monthly(prepare(d[d["pitcher"] == CLASE]))
    named_m = set(clase.loc[clase["named"], "game_date"].dt.to_period("M").astype(str))
    if named_months_df is not None:
        mm = named_months_df[named_months_df["pitcher"] == "Emmanuel Clase"]
        m_named = m_named.drop(columns=["base_audit", "score_audit", "score_live"]).merge(
            mm[["month", "base_audit", "score_audit", "score_live", "league_pct_audit"]], on="month", how="left")
    st.plotly_chart(monthly_fig(m_named, named_m, "Emmanuel Clase: first-pitch balls in the dirt, by month "
                                                  "(amber = month with a court-named pitch)"),
                    width="stretch", theme=None)
    if league:
        st.markdown(f"#### League-wide test: {league['n_pitcher_months']:,} pitcher-months, "
                    f"{league['n_pitchers']:,} pitchers, {league['n_pitches']:,} pitches")
        rows = []
        for k, label in [("score_audit", "Ours: vs his own baseline"), ("baseline_rate", "Simple: raw rate"),
                         ("baseline_count", "Simple: raw count")]:
            v = league["methods"][k]
            pr = v["positive_ranks"]
            rows.append({"method": label, "avg precision": round(v["avg_precision"], 3),
                         "best named month rank": min(pr.values()) if pr else None,
                         "Clase May 2025 rank": pr.get("Emmanuel Clase 2025-05")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if cells is not None:
            thr = st.slider("Alert threshold (−log10 p)", 1.0, 5.0, 3.0, 0.25)
            flag = cells["score_audit"] >= thr
            n_months = cells["month"].nunique()
            a, b, c = st.columns(3)
            a.metric("Alerts league-wide", f"{int(flag.sum()):,}")
            b.metric("Alerts per month", f"{flag.sum()/n_months:.1f}")
            c.metric("Named months caught", f"{int((flag & (cells['label'] == 1)).sum())} of "
                                            f"{int(cells['label'].sum())}")
            st.caption("Other pitchers are never shown by name. A flag means 'look at the video', nothing more.")
    else:
        st.info("League-wide test is still running on the full 2023–25 Statcast pull.")

# ---------------------------------------------------------------- tab 4
with tabs[3]:
    st.markdown("### Run the monitor on any pitcher")
    st.markdown("Upload a Baseball Savant CSV for one pitcher (Statcast Search → pitcher → *Download CSV*), "
                "or load the sample.")
    up = st.file_uploader("Savant CSV", type=["csv"])
    sample = st.button("Load sample: Luis L. Ortiz 2023–25")
    raw = None
    if up is not None:
        raw = pd.read_csv(io.BytesIO(up.getvalue()))
    elif sample:
        raw = pd.read_parquet(ROOT / "data/slim/pitchers_clase_ortiz.parquet")
        raw = raw[raw["pitcher"] == ORTIZ]
    if raw is not None:
        need = {"pitcher", "game_date", "game_pk", "game_type", "at_bat_number", "pitch_number", "pitch_type",
                "plate_x", "plate_z", "sz_top", "sz_bot", "stand", "balls", "strikes", "release_speed", "description"}
        missing = need - set(raw.columns)
        if missing:
            st.error(f"This file is missing columns: {sorted(missing)}. Use a Statcast Search CSV.")
        else:
            pid = raw["pitcher"].mode().iloc[0]
            one = raw[raw["pitcher"] == pid]
            m = monthly(prepare(one))
            if m.empty:
                st.warning("Not enough first pitches (needs 20+ in a month) to run the monitor.")
            else:
                st.plotly_chart(monthly_fig(m, set(), f"Pitcher {pid}: first-pitch balls in the dirt by month"),
                                width="stretch", theme=None)
                top = m.sort_values("score_audit", ascending=False).head(5)
                st.dataframe(top[["month", "n", "k", "rate", "base_audit", "score_audit"]].round(3).rename(columns={
                    "n": "first pitches", "k": "in the dirt", "base_audit": "his baseline",
                    "score_audit": "alert score"}), hide_index=True, width="stretch")
                st.caption("League rate is unknown for a single upload, so the baseline is shrunk to this "
                           "pitcher's own overall rate. Alert score ≥ 3 means p ≤ 0.001 under his own baseline.")

# ---------------------------------------------------------------- tab 5
with tabs[4]:
    st.markdown("""
### How it works
1. **Data**: every MLB pitch 2023–25 from Baseball Savant (Statcast) via `pybaseball`.
2. **Labels**: 18 Clase pitches named in a Sept 18 2026 court filing, matched one-to-one to Statcast rows by date,
   inning, batter and pitch number. Two Ortiz games (June 15 and June 27 2025) from the DOJ release.
3. **v1 pitch model** (`pim/score.py`): location, pitch choice and velocity, each compared only with the same
   pitcher's earlier games, combined with Fisher's method. Frozen in git before evaluation.
4. **v2 pattern monitor** (`pim/monitor.py`): monthly rate of a template taken from the indictment's text
   (first pitch, ball in the dirt), compared with his own baseline using a binomial tail test.

### Where it stops
- It never says *rigged*. It ranks what is **unusual for this pitcher** and hands it to a human.
- Labels are allegations. Unnamed pitches may also have been rigged, so some "false alarms" may not be false.
- Bets on velocity or pitch type leave no trace in location, so the monitor can't see them.
- Other pitchers who trigger alerts are never named. Most will be slumps, injuries or new pitches.
""")
