"""Pitch Integrity Monitor: Streamlit host for the story page (docs/index.html).

Run:  streamlit run app.py      (rebuild the page with: python scripts/build_web.py)
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Pitch Integrity Monitor", page_icon="⚾", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown("""<style>
  header[data-testid="stHeader"], [data-testid="stToolbar"], footer {display:none !important}
  .block-container, [data-testid="stMainBlockContainer"] {padding:0 !important; max-width:100% !important}
  [data-testid="stAppViewContainer"], .stApp {background:#F7F4EE}
  iframe {height:100vh !important; border:0; display:block}
  [data-testid="stVerticalBlock"] {gap:0 !important}
</style>""", unsafe_allow_html=True)

page = Path(__file__).parent / "docs" / "index.html"
if page.exists():
    components.html(page.read_text(encoding="utf-8"), height=900, scrolling=True)
else:
    st.error("docs/index.html is missing. Run: python scripts/build_web.py")
