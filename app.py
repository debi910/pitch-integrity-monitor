"""Pitch Integrity Monitor: Streamlit app.

Run:  streamlit run app.py
"""
import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pim.monitor import monthly
from pim.score import prepare

ROOT = Path(__file__).parent
ORTIZ = 682847

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


# ---------------------------------------------------------------- story page (docs/index.html)
import streamlit.components.v1 as components  # noqa: E402

st.markdown("""<style>
  header[data-testid="stHeader"]{display:none}
  .block-container{padding:0 !important;max-width:100% !important}
  [data-testid="stTabs"] [role="tablist"]{padding:0 24px;gap:8px;border-bottom:1px solid #232830}
  iframe{height:calc(100vh - 56px) !important;border:0}
  [data-testid="stTabs"] [role="tabpanel"]{padding:0 max(24px, calc((100% - 1120px)/2))}
  [data-testid="stTabs"] [role="tabpanel"]:has(iframe){padding:0}
</style>""", unsafe_allow_html=True)

story_tab, try_tab = st.tabs(["Story", "Run it on any pitcher"])
with story_tab:
    page = ROOT / "docs/index.html"
    if page.exists():
        components.html(page.read_text(encoding="utf-8"), height=900, scrolling=True)
    else:
        st.error("docs/index.html missing: run python scripts/build_web.py")

# ---------------------------------------------------------------- tab 4
with try_tab:
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

