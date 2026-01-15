# pages/1_Analisi_A.py
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Topics: Pubblicazioni per Spoke", layout="wide")


# ----------------------------
# Paths (repo-relative, Streamlit Cloud safe)
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent        # .../pages
REPO_DIR = BASE_DIR.parent                       # repo root

DATA_PATH = REPO_DIR / "data" / "processed" / "papers_per_spoke.csv"
LOGO_PATH = REPO_DIR / "logo.jpg"


# ----------------------------
# Load data
# ----------------------------
if not DATA_PATH.exists():
    st.error(f"File non trovato: {DATA_PATH}")
    st.stop()

df = pd.read_csv(DATA_PATH)   # columns: spoke, n_papers, spoke_label


required_cols = {"spoke", "n_papers", "spoke_label"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Colonne mancanti nel CSV: {missing}")
    st.stop()


# ----------------------------
# Header (same style as landing)
# ----------------------------
col_logo, col_title = st.columns([1, 6], vertical_alignment="center")

with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=140)

with col_title:
    st.title("Pubblicazioni per Spoke")
    st.markdown(
        "<div style='color:#777;'>Distribuzione del numero di pubblicazioni per ciascuno spoke</div>",
        unsafe_allow_html=True,
    )

st.write("")


# ----------------------------
# D3 bar chart (HTML generator)
# ----------------------------
def barplot_html(labels, values, spokes):
    payload = {
        "labels": labels,
        "values": values,
        "spokes": spokes,
    }
    data_json = json.dumps(payload)

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #fff;
    }}
    .wrap {{
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    svg {{
      width: 100%;
      height: 100%;
    }}
    .tooltip {{
      position: absolute;
      padding: 6px 10px;
      background: rgba(0,0,0,0.8);
      color: #fff;
      border-radius: 6px;
      font-size: 12px;
      pointer-events: none;
    }}
  </style>
</head>
<body>
  <div class="wrap" id="chart"></div>

  <script>
    const payload = {data_json};
    const labels = payload.labels;
    const values = payload.values;
    const spokes = payload.spokes;

    const container = document.getElementById("chart");
    const width = container.clientWidth || 1100;
    const height = 560;

    // Increased bottom margin to avoid label truncation
    const margin = {{ top: 30, right: 30, bottom: 160, left: 60 }};
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const svg = d3.select(container)
      .append("svg")
      .attr("viewBox", [0, 0, width, height]);

    const g = svg.append("g")
      .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

    const x = d3.scaleBand()
      .domain(labels)
      .range([0, w])
      .padding(0.25);

    const y = d3.scaleLinear()
      .domain([0, d3.max(values)]).nice()
      .range([h, 0]);

    const xAxis = d3.axisBottom(x);
    const yAxis = d3.axisLeft(y).ticks(6);

    g.append("g")
      .attr("transform", `translate(0,${{h}})`)
      .call(xAxis)
      .selectAll("text")
      .style("text-anchor", "end")
      .attr("dx", "-0.8em")
      .attr("dy", "0.25em")
      .attr("transform", "rotate(-55)");

    g.append("g")
      .call(yAxis);

    const tooltip = d3.select("body")
      .append("div")
      .attr("class", "tooltip")
      .style("opacity", 0);

    const barData = labels.map((d, i) => ({{ label: d, value: values[i], spoke: spokes[i] }}));

    g.selectAll("rect")
      .data(barData)
      .join("rect")
      .attr("x", d => x(d.label))
      .attr("y", d => y(d.value))
      .attr("width", x.bandwidth())
      .attr("height", d => h - y(d.value))
      .attr("fill", "#4E79A7")
      .on("mousemove", (event, d) => {{
        tooltip
          .style("opacity", 1)
          .html(`<b>${{d.label}}</b><br/>Spoke: ${{d.spoke}}<br/>Pubblicazioni: ${{d.value}}`)
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY + 10) + "px");
      }})
      .on("mouseout", () => tooltip.style("opacity", 0));

    // --- Value labels above bars ---
    g.selectAll("text.bar-value")
      .data(barData)
      .join("text")
      .attr("class", "bar-value")
      .attr("x", d => x(d.label) + x.bandwidth() / 2)
      .attr("y", d => y(d.value) - 6)
      .attr("text-anchor", "middle")
      .style("font-size", "14px")
      .style("font-weight", "600")
      .style("fill", "#111")
      .text(d => d.value);

  </script>
</body>
</html>
"""


# ----------------------------
# Prepare data for D3
# ----------------------------
labels = df["spoke_label"].astype(str).tolist()
values = df["n_papers"].astype(int).tolist()
spokes = df["spoke"].astype(int).tolist()  # used in tooltip


# ----------------------------
# Render chart
# ----------------------------
components.html(barplot_html(labels, values, spokes), height=600, scrolling=False)


# ----------------------------
# Description
# ----------------------------
st.caption(
    "Il grafico mostra il numero di pubblicazioni associate a ciascuno spoke. "
    "Ogni barra rappresenta uno spoke e la sua altezza è proporzionale al numero totale di paper."
)