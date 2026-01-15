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
# Home UI below will render only for the landing.
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
        max-width: 1400px;   /* a bit wider for 4 cards */
      }

      .choice-box {
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 12px;
        padding: 26px 28px;
        height: 100%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
      }

      /* --- Make the "Apri" button full-width and yellow --- */
      div[data-testid="stButton"] > button {
        width: 100% !important;
        height: 56px !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        background: #FFD401 !important;
        color: #111 !important;
        border: 1px solid rgba(0,0,0,0.15) !important;
        border-radius: 12px !important;
      }

      div[data-testid="stButton"] > button:hover {
        filter: brightness(0.98);
        border-color: rgba(0,0,0,0.25) !important;
      }

      div[data-testid="stButton"] > button:active {
        filter: brightness(0.96);
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

# Cards (4 columns)
c1, c2, c3, c4 = st.columns(4, gap="large")

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
        pg = st.navigation(
            [
                st.Page("Home.py", title="Home", icon="🏠"),
                st.Page("pages/1_Topics.py", title="Topics"),
                st.Page("pages/2_Collaborazioni_tra_aree_scientifiche.py", title="Collaborazioni"),
                st.Page("pages/3_Tracce_Narrative.py", title="Tracce Narrative"),
                st.Page("pages/4_Keyword_Analysis.py", title="Keyword Analysis"),
            ]
        )
        st.switch_page("pages/1_Topics.py")  # optional; see note below

with c2:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Collaborazioni</h3>
          <p>Collaborazioni tra aree scientifiche, derivate dalle co-autorialità.</p>
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
          <p>Distribuzione delle categorie narrative con grafico a torta/donut.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_tracce"):
        st.switch_page("pages/3_Tracce_Narrative.py")

with c4:
    st.markdown(
        """
        <div class="choice-box">
          <h3>Keyword Analysis</h3>
          <p>Word cloud delle parole chiave basata su frequenza e filtri.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Apri", key="go_keywords"):
        st.switch_page("pages/4_Keyword_Analysis.py")