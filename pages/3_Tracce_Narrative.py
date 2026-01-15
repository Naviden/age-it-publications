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
# Paths
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent

DATA_PATH = REPO_DIR / "data" / "processed" / "donut_data.csv"
LOGO_PATH = REPO_DIR / "logo.png"

# ----------------------------
# Load data
# ----------------------------
if not DATA_PATH.exists():
    st.error(f"File non trovato: {DATA_PATH}")
    st.stop()

df = pd.read_csv(DATA_PATH)

if "category" not in df.columns or "value" not in df.columns:
    st.error("Il CSV deve avere colonne: category, value")
    st.stop()

labels = df["category"].astype(str).tolist()
values = df["value"].astype(float).tolist()

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
# Donut / pie HTML (D3)
# ----------------------------
def donut_html(labels, values):
    payload = {"labels": labels, "values": values}
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
  .tooltip {{
    position: absolute;
    padding: 6px 10px;
    background: rgba(0,0,0,0.7);
    color: white;
    border-radius: 4px;
    font-size: 12px;
    pointer-events: none;
  }}
  .label-line {{
    stroke: #888;
    stroke-width: 1px;
  }}
</style>
</head>
<body>
<div id="chart"></div>

<script>
const payload = {data_json};
const labels = payload.labels;
const values = payload.values;

const width = 700, height = 500, margin = 40;
const radius = Math.min(width, height) / 2 - margin;

const svg = d3.select("#chart")
  .append("svg")
  .attr("width", width)
  .attr("height", height)
  .append("g")
  .attr("transform", `translate(${{width/2}},${{height/2}})`);

const color = d3.scaleOrdinal()
  .domain(labels)
  .range(d3.schemeSet3);

const pie = d3.pie()
  .value(d => d.value)
  .sort(null);

const data_ready = pie(labels.map((d,i) => ({{ name: d, value: values[i] }})));

const arc = d3.arc()
  .innerRadius(radius * 0.6)
  .outerRadius(radius * 0.9);

const outerArc = d3.arc()
  .innerRadius(radius * 1.0)
  .outerRadius(radius * 1.0);

svg.selectAll('slices')
  .data(data_ready)
  .join('path')
  .attr('d', arc)
  .attr('fill', d => color(d.data.name))
  .style("opacity", 0.7);

const tooltip = d3.select("body").append("div")
  .attr("class", "tooltip")
  .style("opacity", 0);

svg.selectAll('path')
  .on("mousemove", (event, d) => {{
    tooltip
      .style("opacity", 1)
      .html(`<b>${{d.data.name}}</b><br/>Valore: ${{d.data.value}}`)
      .style("left", (event.pageX + 10) + "px")
      .style("top", (event.pageY + 10) + "px");
  }})
  .on("mouseout", () => tooltip.style("opacity", 0));

// add polylines between chart and labels
svg.selectAll('allPolylines')
  .data(data_ready)
  .join('polyline')
  .attr('class','label-line')
  .attr('points', d => {{
    const posA = arc.centroid(d); 
    const posB = outerArc.centroid(d);
    const posC = outerArc.centroid(d);
    posC[0] = radius * 1.15 * (d.endAngle < Math.PI ? 1 : -1);
    return [posA, posB, posC];
  }});

// add labels
svg.selectAll('allLabels')
  .data(data_ready)
  .join('text')
  .text(d => d.data.name)
  .attr('transform', d => {{
    const pos = outerArc.centroid(d);
    pos[0] = radius * 1.17 * (d.endAngle < Math.PI ? 1 : -1);
    return `translate(${{pos}})`;
  }})
  .style('text-anchor', d => d.endAngle < Math.PI ? 'start' : 'end');

</script>
</body>
</html>
    """

# ----------------------------
# Render chart
# ----------------------------
components.html(donut_html(labels, values), height=560, scrolling=False)

# ----------------------------
# Description
# ----------------------------
st.caption(
    "Diagramma a torta/donut con linee di collegamento alle etichette. "
    "Passa il mouse sopra ogni fetta per vedere i dettagli."
)