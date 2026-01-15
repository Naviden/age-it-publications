# Home.py
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Age-It: Prodotti scientifici", layout="wide")

# --- Paths ---
LOGO_PATH = Path(__file__).parent / "logo.jpg"

# --- CSS for cards + buttons ---
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.4rem !important; max-width: 1200px; }

      .choice-box {
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 12px;
        padding: 26px 28px;
        height: 100%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
      }
      .choice-box h3 { margin-top: 0; color: #111; }
      .choice-box p { color: #444; margin-bottom: 0; }

      /* Buttons full width + yellow theme */
      div[data-testid="column"] div.stButton { width: 100% !important; }
      div.stButton > button {
        width: 100% !important;
        height: 52px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        background: #FFD401 !important;
        color: #111 !important;
        border: 1px solid #E6C200 !important;
        border-radius: 10px !important;
      }
      div.stButton > button:hover {
        background: #FFDD2E !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header with logo ---
col_logo, col_title = st.columns([1, 6], vertical_alignment="center")

with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=140)

with col_title:
    st.title("Age-It: Prodotti scientifici")
    st.markdown(
        "<div style='color:#777;'>Esplora pubblicazioni e relazioni nei prodotti scientifici Age-It.</div>",
        unsafe_allow_html=True,
    )

st.write("")

# --- Four analysis choices (in two rows if needed) ---
c1, c2, c3, c4 = st.columns(4, gap="large")

# ---- Topics ----
with c1:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Topics</h3>
          <p>Analisi delle pubblicazioni suddivise per principali temi di ricerca.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_topics"):
        st.switch_page("pages/1_Topics.py")

# ---- Collaborazioni ----
with c2:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Collaborazioni tra ricercatori</h3>
          <p>Visualizzazione delle collaborazioni tra aree scientifiche tramite diagramma chord.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_collab"):
        st.switch_page("pages/2_Collaborazioni_tra_aree_scientifiche.py")

# ---- Tracce Narrative ----
with c3:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Tracce Narrative</h3>
          <p>Distribuzione di 8 categorie narrative tramite diagramma a torta/donut.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_tracce"):
        st.switch_page("pages/3_Tracce_Narrative.py")

# ---- Keyword Analysis ----
with c4:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Keyword Analysis</h3>
          <p>Visualizzazione delle parole chiave tramite word cloud basata su frequenza.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_keywords"):
        st.switch_page("pages/4_Keyword_Analysis.py")