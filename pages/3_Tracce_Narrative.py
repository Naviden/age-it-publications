# pages/3_Tracce_Narrative.py
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Tracce Narrative", layout="wide")


# ----------------------------
# Paths (repo-relative, Streamlit Cloud safe)
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent

DATA_PATH = REPO_DIR / "data" / "processed" / "tracce_narrative.csv"
LOGO_PATH = REPO_DIR / "logo.jpg"


# ----------------------------
# Load data
# ----------------------------
if not DATA_PATH.exists():
    st.error(f"File non trovato: {DATA_PATH}")
    st.stop()

df = pd.read_csv(DATA_PATH)

required_cols = {"orig_label", "count", "short_label"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Colonne mancanti nel CSV: {missing}")
    st.stop()

df = df.copy()
df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)
df["orig_label"] = df["orig_label"].astype(str)
df["short_label"] = df["short_label"].astype(str)

# Keep top 8 by count (if more exist)
df = df.sort_values("count", ascending=False).head(8)


# ----------------------------
# Header
# ----------------------------
col_logo, col_title = st.columns([1, 7], vertical_alignment="center")

with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=140)

with col_title:
    st.title("Tracce Narrative")
    st.markdown(
        "<div style='color:#777;'>Distribuzione delle categorie narrative</div>",
        unsafe_allow_html=True,
    )

st.write("")


# ----------------------------
# Sidebar controls
# ----------------------------
st.sidebar.header("Parametri")

label_choice = st.sidebar.radio(
    "Etichette da usare",
    options=["Etichetta originale", "Etichetta breve"],
    index=1,
    help=(
        "Scegli quale colonna usare come etichetta nel grafico. "
        "Etichetta originale = 'orig_label'. Etichetta breve = 'short_label'."
    ),
)
label_col = "short_label" if label_choice == "Etichetta breve" else "orig_label"

show_percent = st.sidebar.checkbox(
    "Mostra percentuali in tooltip",
    value=True,
    help="Se attivo, nel tooltip vengono mostrate anche le percentuali sul totale.",
)

palette = st.sidebar.selectbox(
    "Palette colori",
    ["set3", "tableau10", "paired"],
    index=0,
    help="Palette colori per le fette del diagramma.",
)

inner_radius_ratio = st.sidebar.slider(
    "Dimensione foro (donut)",
    min_value=0.0,
    max_value=0.8,
    value=0.55,
    step=0.05,
    help="0 = torta piena, valori maggiori = foro più grande (donut).",
)


# ----------------------------
# Prepare payload for D3
# ----------------------------
labels = df[label_col].tolist()
values = df["count"].astype(float).tolist()
total = float(sum(values)) if sum(values) > 0 else 1.0


# ----------------------------
# D3 donut / pie HTML
# (safe for Python f-strings: no JS template literals with ${...})
# ----------------------------
def donut_html(labels, values, total, show_percent, palette, inner_ratio):
    payload = {
        "labels": labels,
        "values": values,
        "total": total,
        "show_percent": show_percent,
        "palette": palette,
        "inner_ratio": inner_ratio,
    }
    data_json = json.dumps(payload)

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    background: #fff;
  }}
  #chart {{ width: 100%; }}
  svg {{ width: 100%; height: auto; }}

  .tooltip {{
    position: absolute;
    padding: 6px 10px;
    background: rgba(0,0,0,0.7);
    color: white;
    border-radius: 6px;
    font-size: 12px;
    pointer-events: none;
    line-height: 1.25;
    max-width: 340px;
  }}

  .label-line {{
    stroke: #888;
    stroke-width: 1px;
    fill: none;
    opacity: 0.9;
  }}

  text.label {{
    fill: #222;
    font-size: 11px;
  }}
</style>
</head>
<body>
<div id="chart"></div>

<script>
const payload = {data_json};
const labels = payload.labels;
const values = payload.values;
const total = payload.total;
const showPercent = payload.show_percent;
const palette = payload.palette;
const innerRatio = payload.inner_ratio;

// Base canvas (for the donut itself)
const width = 1100, height = 560;

// Extra padding around the drawing area (prevents clipping of donut + labels)
const padL = 280, padR = 280, padT = 110, padB = 120;

const margin = 30;
const radius = Math.min(width, height) / 2 - margin;

// Create responsive SVG with expanded viewBox
const svg = d3.select("#chart")
  .append("svg")
  .attr("viewBox",
        (-padL) + " " + (-padT) + " " + (width + padL + padR) + " " + (height + padT + padB))
  .attr("preserveAspectRatio", "xMidYMid meet");

// Center group
const g = svg.append("g")
  .attr("transform", "translate(" + (width/2) + "," + (height/2) + ")");

// palettes
const palettes = {{
  set3: d3.schemeSet3,
  tableau10: d3.schemeTableau10,
  paired: d3.schemePaired
}};
const colors = palettes[palette] || d3.schemeSet3;

const color = d3.scaleOrdinal()
  .domain(labels)
  .range(colors.length >= labels.length
    ? colors
    : d3.range(labels.length).map(i => colors[i % colors.length])
  );

const pie = d3.pie()
  .value(d => d.value)
  .sort(null);

const dataReady = pie(labels.map((d, i) => ({{ name: d, value: values[i] }})));

// Make donut a bit smaller to ensure safe margins
const arc = d3.arc()
  .innerRadius(radius * innerRatio)
  .outerRadius(radius * 0.80);

const outerArc = d3.arc()
  .innerRadius(radius * 1.03)
  .outerRadius(radius * 1.03);

// slices
const slices = g.selectAll("path.slice")
  .data(dataReady)
  .join("path")
  .attr("class", "slice")
  .attr("d", arc)
  .attr("fill", d => color(d.data.name))
  .attr("stroke", d => d3.color(color(d.data.name)).darker(0.6))
  .attr("fill-opacity", 0.85);

// tooltip
const tooltip = d3.select("body").append("div")
  .attr("class", "tooltip")
  .style("opacity", 0);

function pct(v) {{
  return (100 * v / total).toFixed(1) + "%";
}}

slices
  .on("mousemove", (event, d) => {{
    const name = d.data.name;
    const value = d.data.value;
    const extra = showPercent ? "<br/>Percentuale: " + pct(value) : "";
    tooltip
      .style("opacity", 1)
      .html("<b>" + name + "</b><br/>Valore: " + value + extra)
      .style("left", (event.pageX + 12) + "px")
      .style("top", (event.pageY + 12) + "px");
  }})
  .on("mouseout", () => tooltip.style("opacity", 0));

// polylines and labels
const labelOffset = radius * 1.38;

g.selectAll("polyline.label-line")
  .data(dataReady)
  .join("polyline")
  .attr("class", "label-line")
  .attr("points", d => {{
    const posA = arc.centroid(d);
    const posB = outerArc.centroid(d);
    const posC = outerArc.centroid(d);
    posC[0] = labelOffset * (d.endAngle < Math.PI ? 1 : -1);
    return [posA, posB, posC];
  }});

const labelSel = g.selectAll("text.label")
  .data(dataReady)
  .join("text")
  .attr("class", "label")
  .attr("transform", d => {{
    const pos = outerArc.centroid(d);
    pos[0] = (labelOffset + 12) * (d.endAngle < Math.PI ? 1 : -1);
    return "translate(" + pos[0] + "," + pos[1] + ")";
  }})
  .style("text-anchor", d => d.endAngle < Math.PI ? "start" : "end")
  .text(d => d.data.name);

// Wrap long labels into multiple lines
wrapLabels(labelSel, 270);

function wrapLabels(textSelection, width) {{
  textSelection.each(function() {{
    const text = d3.select(this);
    const words = text.text().split(/\\s+/).reverse();
    let word;
    let line = [];
    let lineNumber = 0;
    const lineHeight = 1.05; // em
    const y = 0;
    const dy = 0;

    let tspan = text.text(null)
      .append("tspan")
      .attr("x", 0)
      .attr("y", y)
      .attr("dy", dy + "em");

    while ((word = words.pop())) {{
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > width) {{
        line.pop();
        tspan.text(line.join(" "));
        line = [word];
        tspan = text.append("tspan")
          .attr("x", 0)
          .attr("y", y)
          .attr("dy", (++lineNumber * lineHeight + dy) + "em")
          .text(word);
      }}
    }}
  }});
}}
</script>
</body>
</html>
"""


# ----------------------------
# Render chart
# ----------------------------
components.html(
    donut_html(labels, values, total, show_percent, palette, inner_radius_ratio),
    height=720,
    scrolling=False,
)


# ----------------------------
# Description
# ----------------------------
label_desc = "etichette brevi" if label_col == "short_label" else "etichette originali"
st.caption(
    f"Il grafico mostra la distribuzione delle 8 categorie delle Tracce Narrative. "
    f"Le etichette visualizzate sono basate su {label_desc}. "
    "Passa il mouse su una fetta per vedere valore (e percentuale, se attivata)."
)