# Home.py
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Age-It: Prodotti scientifici", layout="wide")

# ----------------------------
# Navigation (flat list) - WORKING PATTERN
# ----------------------------
pg = st.navigation(
    [
        st.Page("Home.py", title="Home", icon="🏠"),
        st.Page("pages/1_Topics.py", title="Topics"),
        st.Page("pages/2_Collaborazioni_tra_aree_scientifiche.py", title="Collaborazioni"),
        st.Page("pages/3_Tracce_Narrative.py", title="Tracce Narrative"),
        st.Page("pages/4_Keyword_Analysis.py", title="Keyword Analysis"),
    ]
)

# If the selected page is NOT Home, run it and stop.
if pg.title != "Home":
    pg.run()
    st.stop()

# ----------------------------
# Home (landing) UI
# ----------------------------
LOGO_PATH = Path(__file__).parent / "logo.jpg"

st.markdown(
    """
    <style>
      .block-container {
        padding-top: 1.4rem !important;
        max-width: 1400px;
      }

      /* Make ALL Streamlit buttons full width + yellow */
      div[data-testid="stButton"] > button {
        width: 100% !important;
        height: 56px !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        background: #FFD401 !important;
        color: #111 !important;
        border: 1px solid rgba(0,0,0,0.18) !important;
        border-radius: 12px !important;
      }

      div[data-testid="stButton"] > button:hover {
        filter: brightness(0.98);
        border-color: rgba(0,0,0,0.28) !important;
      }

      div[data-testid="stButton"] > button:active {
        filter: brightness(0.96);
      }

      /* Make container borders look more like your cards */
      div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        border: 1px solid #e1e4e8 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        background: #fff !important;
      }

      /* Slightly tighter spacing inside bordered containers */
      div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding-top: 8px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header with logo
col_logo, col_title = st.columns([1, 6], vertical_alignment="center")

with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=140)

with col_title:
    st.title("Age-It: Prodotti scientifici")
    st.markdown(
        """
        <div style='color:#777; line-height:1.35;'>
          In questa sezione puoi esplorare i prodotti scientifici di Age-It attraverso diverse chiavi di lettura:
          temi di ricerca, collaborazioni tra ricercatori, tracce narrative e parole chiave.
          Seleziona un’analisi per iniziare.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# Cards (4 columns) - IMPORTANT: button stays INSIDE the same container
c1, c2, c3, c4 = st.columns(4, gap="large")

with c1:
    with st.container(border=True):
        st.markdown("<div style='font-size:34px; font-weight:800; margin: 4px 0 10px 0;'>Topics</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#444; font-size:18px; line-height:1.45; margin-bottom:18px;'>"
            "Analisi delle pubblicazioni suddivise per principali temi di ricerca."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Apri", key="go_topics", use_container_width=True):
            st.switch_page("pages/1_Topics.py")

with c2:
    with st.container(border=True):
        st.markdown("<div style='font-size:34px; font-weight:800; margin: 4px 0 10px 0;'>Collaborazioni</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#444; font-size:18px; line-height:1.45; margin-bottom:18px;'>"
            "Collaborazioni tra aree scientifiche, derivate dalle co-autorialità."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Apri", key="go_collab", use_container_width=True):
            st.switch_page("pages/2_Collaborazioni_tra_aree_scientifiche.py")

with c3:
    with st.container(border=True):
        st.markdown("<div style='font-size:34px; font-weight:800; margin: 4px 0 10px 0;'>Tracce Narrative</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#444; font-size:18px; line-height:1.45; margin-bottom:18px;'>"
            "Distribuzione delle categorie narrative con grafico a torta/donut."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Apri", key="go_tracce", use_container_width=True):
            st.switch_page("pages/3_Tracce_Narrative.py")

with c4:
    with st.container(border=True):
        st.markdown("<div style='font-size:34px; font-weight:800; margin: 4px 0 10px 0;'>Keyword Analysis</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#444; font-size:18px; line-height:1.45; margin-bottom:18px;'>"
            "Word cloud delle parole chiave basata su frequenza e filtri."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Apri", key="go_keywords", use_container_width=True):
            st.switch_page("pages/4_Keyword_Analysis.py")