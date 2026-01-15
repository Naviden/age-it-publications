# pages/4_Keyword_Analysis.py
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Keyword Analysis", layout="wide")


# ----------------------------
# Paths (repo-relative, Streamlit Cloud safe)
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent

DATA_PATH = REPO_DIR / "data" / "processed" / "keyword_data.csv"
LOGO_PATH = REPO_DIR / "logo.jpg"


# ----------------------------
# Load data
# ----------------------------
if not DATA_PATH.exists():
    st.error(f"File non trovato: {DATA_PATH}")
    st.stop()

df = pd.read_csv(DATA_PATH)

if "keywords" not in df.columns:
    st.error("Il CSV deve contenere una colonna chiamata 'keywords'.")
    st.stop()


# ----------------------------
# Header
# ----------------------------
col_logo, col_title = st.columns([1, 7], vertical_alignment="center")
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=140)

with col_title:
    st.title("Keyword Analysis")
    st.markdown(
        "<div style='color:#777;'>Word cloud delle parole chiave (dimensione proporzionale alla frequenza).</div>",
        unsafe_allow_html=True,
    )

st.write("")


# ----------------------------
# Sidebar controls
# ----------------------------
st.sidebar.header("Parametri")

split_mode = st.sidebar.selectbox(
    "Separatore parole chiave",
    options=["Auto (consigliato)", "Virgola (,)", "Punto e virgola (;)", "Nuova riga"],
    index=0,
    help="Come separare le parole chiave presenti nella colonna 'keywords'.",
)

min_freq = st.sidebar.slider(
    "Frequenza minima",
    min_value=1,
    max_value=50,
    value=2,
    step=1,
    help="Mostra solo keyword con frequenza >= soglia.",
)

max_words = st.sidebar.slider(
    "Numero massimo di keyword",
    min_value=10,
    max_value=250,
    value=100,
    step=10,
    help="Limita il numero di keyword visualizzate (ordinate per frequenza).",
)

max_phrase_words = st.sidebar.slider(
    "Lunghezza massima keyword (in parole)",
    min_value=1,
    max_value=12,
    value=4,
    step=1,
    help="Filtra keyword troppo lunghe (es. frasi intere).",
)

palette = st.sidebar.selectbox(
    "Palette colori",
    ["set3", "tableau10", "paired"],
    index=0,
)

rotate_mode = st.sidebar.selectbox(
    "Rotazione",
    ["Solo orizzontale", "0° / 90°"],
    index=0,
    help="Se 0°/90°, una parte delle keyword viene ruotata di 90°.",
)

exclude_text = st.sidebar.text_area(
    "Escludi keyword (una per riga)",
    value="",
    help="Inserisci le keyword da escludere. Il confronto è case-insensitive.",
)
exclude_set = {
    x.strip().lower()
    for x in exclude_text.splitlines()
    if x.strip()
}


# ----------------------------
# Build keyword frequency table
# ----------------------------
if split_mode == "Auto (consigliato)":
    split_re = r"[,\n;]+"
elif split_mode == "Virgola (,)":
    split_re = r"[,]+"
elif split_mode == "Punto e virgola (;)":
    split_re = r"[;]+"
else:
    split_re = r"[\n]+"

series = df["keywords"].fillna("").astype(str)

tokens = (
    series
    .str.replace(r"\s+", " ", regex=True)
    .str.split(split_re, regex=True)
    .explode()
    .astype(str)
    .str.strip()
    .str.lower()   # <-- normalise case
)
if exclude_set:
    tokens = tokens[~tokens.isin(exclude_set)]
    
tokens = tokens[tokens != ""]
tokens = tokens[~tokens.str.fullmatch(r"[\W_]+", na=False)]
tokens = tokens[tokens.str.split().str.len() <= max_phrase_words]

count_df = tokens.value_counts().reset_index()
count_df.columns = ["text", "count"]
count_df = count_df[count_df["count"] >= min_freq].head(max_words)

if count_df.empty:
    st.warning("Nessuna keyword soddisfa i filtri selezionati.")
    st.stop()

words = count_df.to_dict(orient="records")


# ----------------------------
# D3 Word Cloud HTML (NO f-string)
# ----------------------------
def wordcloud_html(words_list, palette_name, rotate_choice) -> str:
    payload = {
        "words": words_list,
        "palette": palette_name,
        "rotate_mode": rotate_choice,
    }
    data_json = json.dumps(payload, ensure_ascii=False)

    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/d3-cloud@1.2.5/build/d3.layout.cloud.js"></script>
  <style>
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #fff;
    }
    #wc {
      width: 100%;
      display: flex;
      justify-content: center;
    }
    .tooltip {
      position: absolute;
      padding: 6px 10px;
      background: rgba(0,0,0,0.78);
      color: #fff;
      border-radius: 6px;
      font-size: 12px;
      pointer-events: none;
      line-height: 1.25;
      max-width: 360px;
    }
  </style>
</head>
<body>
<div id="wc"></div>

<script>
  const payload = __PAYLOAD__;
  const wordsIn = payload.words;
  const palette = payload.palette;
  const rotateMode = payload.rotate_mode;

  const palettes = {
    set3: d3.schemeSet3,
    tableau10: d3.schemeTableau10,
    paired: d3.schemePaired
  };
  const colors = palettes[palette] || d3.schemeSet3;
  const colorScale = d3.scaleOrdinal().range(colors);

  const width = 1100;
  const height = 520;

  const maxCount = d3.max(wordsIn, d => d.count);
  const minCount = d3.min(wordsIn, d => d.count);

  const fontScale = d3.scaleSqrt()
    .domain([minCount, maxCount])
    .range([14, 72]);

  const words = wordsIn.map(d => ({
    text: d.text,
    count: d.count,
    size: fontScale(d.count)
  }));

  const tooltip = d3.select("body")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

  function rot() {
    if (rotateMode === "0° / 90°") {
      return (Math.random() < 0.25) ? 90 : 0;
    }
    return 0;
  }

  const layout = d3.layout.cloud()
    .size([width, height])
    .words(words)
    .padding(4)
    .rotate(rot)
    .font("Helvetica")
    .fontSize(d => d.size)
    .on("end", draw);

  layout.start();

  function draw(words) {
    const svg = d3.select("#wc").append("svg")
      .attr("viewBox", "0 0 " + width + " " + height)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .style("width", "100%")
      .style("height", "auto");

    const g = svg.append("g")
      .attr("transform", "translate(" + (width/2) + "," + (height/2) + ")");

    g.selectAll("text")
      .data(words)
      .join("text")
      .style("font-size", d => d.size + "px")
      .style("fill", (d, i) => colorScale(i))
      .style("font-family", "Helvetica")
      .attr("text-anchor", "middle")
      .attr("transform", d => "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")")
      .text(d => d.text)
      .on("mousemove", (event, d) => {
        tooltip
          .style("opacity", 1)
          .html("<b>" + d.text + "</b><br/>Frequenza: " + d.count)
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      })
      .on("mouseout", () => tooltip.style("opacity", 0));
  }
</script>
</body>
</html>
"""
    return html.replace("__PAYLOAD__", data_json)


# ----------------------------
# Render
# ----------------------------
components.html(
    wordcloud_html(words, palette, rotate_mode),
    height=650,
    scrolling=False,
)

st.caption(
    "La word cloud mostra le keyword estratte dalla colonna 'keywords'. "
    "Le keyword vengono separate secondo il separatore scelto, aggregate per frequenza e visualizzate con dimensione proporzionale alla frequenza. "
    "Passa il mouse su una keyword per vedere la frequenza."
)