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
        "<div style='color:#777;'>Visualizzazione delle parole chiave tramite una word cloud basata su frequenza.</div>",
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
    help=(
        "Come separare le parole chiave presenti nella colonna. "
        "'Auto' gestisce virgola, punto e virgola e nuove righe."
    ),
)

min_freq = st.sidebar.slider(
    "Frequenza minima per visualizzare",
    min_value=1,
    max_value=50,
    value=2,
    step=1,
    help="Mostra keyword solo se la frequenza è >= soglia.",
)

max_words = st.sidebar.slider(
    "Numero massimo di keyword",
    min_value=10,
    max_value=200,
    value=80,
    step=10,
    help="Limita quante keyword visualizzare (ordinate per frequenza).",
)

max_phrase_words = st.sidebar.slider(
    "Lunghezza massima keyword (in parole)",
    min_value=1,
    max_value=10,
    value=4,
    step=1,
    help="Rimuove keyword troppo lunghe (es. frasi intere) per evitare output poco leggibile.",
)

palette = st.sidebar.selectbox(
    "Palette colori",
    ["set3", "tableau10", "paired"],
    index=0,
    help="Palette colori per la word cloud.",
)

rotate_mode = st.sidebar.selectbox(
    "Rotazione",
    ["Solo orizzontale", "0° / 90°"],
    index=0,
    help="Se attivo 0°/90°, alcune keyword verranno ruotate di 90°.",
)


# ----------------------------
# Build word frequency table
# ----------------------------
# Choose split regex
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
    .str.replace(r"\\s+", " ", regex=True)          # normalise whitespace
    .str.split(split_re, regex=True)               # split into tokens
    .explode()
    .astype(str)
    .str.strip()
)

# Remove empties
tokens = tokens[tokens != ""]

# Remove pure punctuation
tokens = tokens[~tokens.str.fullmatch(r"[\\W_]+", na=False)]

# Filter too-long "keywords" that are actually whole sentences
tokens = tokens[tokens.str.split().str.len() <= max_phrase_words]

# Count
count_df = tokens.value_counts().reset_index()
count_df.columns = ["text", "count"]

# Apply min frequency and cap number of words
count_df = count_df[count_df["count"] >= min_freq].head(max_words)

if count_df.empty:
    st.warning("Nessuna keyword soddisfa i filtri selezionati.")
    st.stop()

words = count_df.to_dict(orient="records")


# ----------------------------
# D3 Word Cloud HTML
# ----------------------------
def wordcloud_html(words, palette, rotate_mode):
    payload = {"words": words, "palette": palette, "rotate_mode": rotate_mode}
    data_json = json.dumps(payload)

    return f\"\"\"
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
    background: #fff;
  }}
  #wc {{
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
  }}
  .tooltip {{
    position: absolute;
    padding: 6px 10px;
    background: rgba(0,0,0,0.75);
    color: #fff;
    border-radius: 6px;
    font-size: 12px;
    pointer-events: none;
    line-height: 1.25;
    max-width: 340px;
  }}
</style>
</head>
<body>
<div id="wc"></div>

<script>
const payload = {data_json};
const wordsIn = payload.words;
const palette = payload.palette;
const rotateMode = payload.rotate_mode;

// palettes
const palettes = {{
  set3: d3.schemeSet3,
  tableau10: d3.schemeTableau10,
  paired: d3.schemePaired
}};
const colors = palettes[palette] || d3.schemeSet3;

const colorScale = d3.scaleOrdinal().range(colors);

// Size: responsive-ish via viewBox; actual layout uses fixed numbers
const width = 1100;
const height = 520;

// Scale font size by count
const maxCount = d3.max(wordsIn, d => d.count);
const minCount = d3.min(wordsIn, d => d.count);

const fontScale = d3.scaleSqrt()
  .domain([minCount, maxCount])
  .range([14, 72]);

const words = wordsIn.map(d => {{
  return {{
    text: d.text,
    count: d.count,
    size: fontScale(d.count)
  }};
}});

// Tooltip
const tooltip = d3.select("body")
  .append("div")
  .attr("class", "tooltip")
  .style("opacity", 0);

// Rotation
function rot() {{
  if (rotateMode === "0° / 90°") {{
    return (Math.random() < 0.25) ? 90 : 0;  // 25% rotated
  }}
  return 0;
}}

const layout = d3.layout.cloud()
  .size([width, height])
  .words(words)
  .padding(4)
  .rotate(rot)
  .font("Helvetica")
  .fontSize(d => d.size)
  .on("end", draw);

layout.start();

function draw(words) {{
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
    .on("mousemove", (event, d) => {{
      tooltip
        .style("opacity", 1)
        .html("<b>" + d.text + "</b><br/>Frequenza: " + d.count)
        .style("left", (event.pageX + 12) + "px")
        .style("top", (event.pageY + 12) + "px");
    }})
    .on("mouseout", () => tooltip.style("opacity", 0));
}}
</script>
</body>
</html>
\"\"\"


# ----------------------------
# Render
# ----------------------------
components.html(
    wordcloud_html(words, palette, rotate_mode),
    height=650,
    scrolling=False,
)

# ----------------------------
# Description
# ----------------------------
st.caption(
    "La word cloud mostra le keyword estratte dalla colonna 'keywords'. "
    "Ogni keyword viene separata in base al separatore scelto, aggregata per frequenza e visualizzata con dimensione proporzionale alla frequenza. "
    "Passa il mouse su una keyword per vedere la frequenza."
)
