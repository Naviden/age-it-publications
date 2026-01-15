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
# Paths (repo-relative)
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
    st.error("CSV deve avere una colonna chiamata 'keywords'.")
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
        "<div style='color:#777;'>Visualizzazione delle parole chiave tramite una word cloud.</div>",
        unsafe_allow_html=True,
    )

st.write("")

# ----------------------------
# Sidebar controls
# ----------------------------
st.sidebar.header("Parametri")

delimiter = st.sidebar.selectbox(
    "Separa parole con",
    options=[";", ",", " "],
    help="Seleziona come sono separate le parole chiave nella colonna.",
)

min_freq = st.sidebar.slider(
    "Frequenza minima per visualizzare",
    min_value=1,
    max_value=50,
    value=2,
    step=1,
    help="Mostra parole solo se la loro frequenza è >= soglia.",
)

palette = st.sidebar.selectbox(
    "Palette colori",
    ["set3", "tableau10", "paired"],
    index=0,
    help="Palette colori per la word cloud.",
)

# ----------------------------
# Build word count list
# ----------------------------
# Split all keywords and count frequency
all_words = (
    df["keywords"]
    .astype(str)
    .str.split(delimiter)
    .explode()
    .str.strip()
    .dropna()
)

count_df = all_words.value_counts().reset_index()
count_df.columns = ["text", "count"]

# Apply min frequency
count_df = count_df[count_df["count"] >= min_freq]

# Prepare data for D3
words = count_df.to_dict(orient="records")

if len(words) == 0:
    st.warning("Nessuna parola soddisfa la frequenza minima.")
    st.stop()

# ----------------------------
# D3 Word Cloud HTML
# ----------------------------
def wordcloud_html(words, palette):
    payload = {"words": words, "palette": palette}
    data_json = json.dumps(payload)

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-cloud@1.2.5/build/d3.layout.cloud.js"></script>
<style>
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  }}
</style>
</head>
<body>
<div id="wordcloud"></div>

<script>
const payload = {data_json};
const words = payload.words;
const palette = payload.palette;

// build a color scale
const colorSchemes = {{
  set3: d3.schemeSet3,
  tableau10: d3.schemeTableau10,
  paired: d3.schemePaired
}};
const colors = colorSchemes[palette] || d3.schemeSet3;
const colorScale = d3.scaleOrdinal().range(colors);

// convert to d3-cloud format
const layoutWords = words.map(d => {{
  return {{text: d.text, size: Math.sqrt(d.count) * 10}};
}});

const width = 900;
const height = 500;

const layout = d3.layout.cloud()
  .size([width, height])
  .words(layoutWords)
  .padding(5)
  .rotate(() => ~~(Math.random() * 2) * 90)
  .font("Helvetica")
  .fontSize(d => d.size)
  .on("end", draw);

layout.start();

// draw function
function draw(words) {{
  d3.select("#wordcloud").append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")")
    .selectAll("text")
    .data(words)
    .join("text")
    .style("font-size", d => d.size + "px")
    .style("fill", (d, i) => colorScale(i))
    .style("font-family", "Helvetica")
    .attr("text-anchor", "middle")
    .attr("transform", d => "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")")
    .text(d => d.text);
}}

</script>
</body>
</html>
"""


# ----------------------------
# Render word cloud
# ----------------------------
components.html(
    wordcloud_html(words, palette),
    height=600,
    scrolling=False,
)

# ----------------------------
# Description
# ----------------------------
st.caption(
    "La word cloud mostra le parole chiave più frequenti. "
    "Le dimensioni riflettono la frequenza relativa all’interno del dataset."
)