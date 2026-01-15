# Home.py
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Age-It: Prodotti scientifici", layout="wide")

# --- Paths ---
LOGO_PATH = Path(__file__).parent / "logo.jpg"

# --- Clean layout + light cards ---
st.markdown(
    """
    <style>
      /* Force Streamlit button containers to take full width */
        div[data-testid="stVerticalBlock"] > div:has(> div.stButton) {
          width: 100% !important;
        }

        div.stButton {
          width: 100% !important;
        }

        div.stButton > button {
          width: 100% !important;
          height: 40px !important;
          font-size: 1rem !important;
          font-weight: 700 !important;
          background: #FFD401 !important;
          color: #111 !important;
          border: 1px solid #E6C200 !important;
          border-radius: 10px !important;
          padding: 0 14px !important;
        }

        div.stButton > button:hover {
          background: #FFDD2E !important;
          border-color: #E6C200 !important;
        }

        div.stButton > button:focus {
          outline: none !important;
          box-shadow: 0 0 0 3px rgba(255, 212, 1, 0.35) !important;
        }
      .block-container {
        padding-top: 1.4rem !important;
        max-width: 1200px;
      }

      .choice-box {
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 12px;
        padding: 26px 28px;
        height: 100%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
      }

      .choice-box h3 {
        margin-top: 0;
        color: #111;
      }

      .choice-box p {
        color: #444;
        margin-bottom: 0;
      }

      /* ----------------------------
         BUTTONS (full width + Age-It yellow)
      ---------------------------- */
      div.stButton > button {
        width: 100% !important;        /* full card width */
        height: 52px !important;       /* slightly taller */
        font-size: 1rem !important;
        font-weight: 700 !important;
        background: #FFD401 !important;
        color: #111 !important;
        border: 1px solid #E6C200 !important;
        border-radius: 10px !important;
      }

      div.stButton > button:hover {
        background: #FFDD2E !important; /* slightly lighter on hover */
        border-color: #E6C200 !important;
        color: #111 !important;
      }

      div.stButton > button:focus {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(255, 212, 1, 0.35) !important;
      }

      div.stButton > button:active {
        transform: translateY(1px);
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
        "<div style='color:#777;'>Analizza i prodotti scientifici di Age-It attraverso tre prospettive: temi di ricerca, reti di collaborazione e tracce narrative.</div>",
        unsafe_allow_html=True,
    )

st.write("")

# --- Three main choices (1 row, 3 columns) ---
c1, c2, c3 = st.columns(3, gap="large")

with c1:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Topics</h3>
          <p>Paper per topic.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_topics"):
        st.switch_page("pages/1_Topics.py")

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

with c3:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Tracce Narrative</h3>
          <p>Distribuzione di 8 categorie narrative.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_tracce"):
        st.switch_page("pages/3_Tracce_Narrative.py")