# app.py
import json
from itertools import combinations
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # .../src
REPO_DIR = BASE_DIR.parent                          # repo root

DF_PATH  = REPO_DIR / "data" / "processed" / "chord_authors.csv"
CEN_PATH = REPO_DIR / "data" / "processed" / "chord_area.csv"

UPDATE_STR = datetime.now().strftime("%d/%m/%Y")


# ----------------------------
# Utilities
# ----------------------------
def normalise_name(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = " ".join(s.split())
    return s.lower()


def parse_authors(authors_full: str) -> list[str]:
    """
    Parse a co-author string into a list of author names.
    Accepts separators like ';' or ','.
    """
    if pd.isna(authors_full):
        return []
    s = str(authors_full).strip()
    if not s:
        return []
    # Try split on ';' first, fallback to ','
    if ";" in s:
        parts = [p.strip() for p in s.split(";")]
    else:
        parts = [p.strip() for p in s.split(",")]
    parts = [p for p in parts if p]
    return parts


def build_name_to_field(cen_df: pd.DataFrame) -> dict:
    """
    Build name -> field mapping from the census file.
    Expects columns: full_name, Area_desc
    """
    name_to_field: dict[str, str] = {}
    for _, r in cen_df.iterrows():
        name = normalise_name(r.get("full_name", ""))
        field = str(r.get("Area_desc", "")).strip()
        if name and field:
            name_to_field[name] = field
    return name_to_field


def collaboration_matrix_paper_level(df_papers: pd.DataFrame, cen_df: pd.DataFrame) -> pd.DataFrame:
    name_to_field = build_name_to_field(cen_df)

    # collect all areas seen in census
    all_fields = sorted(
        {
            str(x).strip()
            for x in cen_df["Area_desc"].dropna().unique()
            if str(x).strip()
        }
    )
    mat = pd.DataFrame(0, index=all_fields, columns=all_fields, dtype=int)

    # Identify the column in df_papers that stores co-authors
    candidate_cols = ["authors_full", "authors", "coauthors", "co_authors", "Authors", "Authors_full"]
    authors_col = next((c for c in candidate_cols if c in df_papers.columns), None)
    if authors_col is None:
        raise ValueError(
            f"Cannot find an authors column in chord_authors.csv. "
            f"Tried: {candidate_cols}. Found columns: {list(df_papers.columns)}"
        )

    for _, row in df_papers.iterrows():
        authors = parse_authors(row.get(authors_col, ""))

        # map to areas (drop missing)
        areas = []
        for a in authors:
            key = normalise_name(a)
            field = name_to_field.get(key, "")
            if field:
                areas.append(field)

        # unique areas in this paper
        uniq = sorted(set(areas))
        if len(uniq) < 2:
            continue

        # increment each unordered pair once per paper
        for a, b in combinations(uniq, 2):
            mat.loc[a, b] += 1
            mat.loc[b, a] += 1

    return mat

def collaboration_matrix_paper_level(df_papers: pd.DataFrame, cen_df: pd.DataFrame) -> pd.DataFrame:
    name_to_field = build_name_to_field(cen_df)

    # collect all areas seen in census
    all_fields = sorted({str(x).strip() for x in cen_df["Area_desc"].dropna().unique() if str(x).strip()})
    mat = pd.DataFrame(0, index=all_fields, columns=all_fields, dtype=int)

    # Identify the column in df_papers that stores co-authors
    # We will try common names. If none found, raise.
    candidate_cols = ["authors_full", "authors", "coauthors", "co_authors", "Authors", "Authors_full"]
    authors_col = None
    for c in candidate_cols:
        if c in df_papers.columns:
            authors_col = c
            break
    if authors_col is None:
        raise ValueError(
            f"Cannot find an authors column in chord_authors.csv. "
            f"Tried: {candidate_cols}. Found columns: {list(df_papers.columns)}"
        )

    for _, row in df_papers.iterrows():
        authors = parse_authors(row.get(authors_col, ""))

        # map to areas (drop missing)
        areas = []
        for a in authors:
            key = normalise_name(a)
            field = name_to_field.get(key, "")
            if field:
                areas.append(field)

        # unique areas in this paper
        uniq = sorted(set(areas))
        if len(uniq) < 2:
            continue

        # increment each unordered pair once per paper
        for a, b in combinations(uniq, 2):
            mat.loc[a, b] += 1
            mat.loc[b, a] += 1

    return mat


def apply_threshold(mat: pd.DataFrame, min_value: int) -> pd.DataFrame:
    if min_value <= 1:
        return mat
    out = mat.copy()
    out[out < min_value] = 0
    return out


def filter_fields(mat: pd.DataFrame, include_fields: list[str]) -> pd.DataFrame:
    if not include_fields:
        return mat
    include_fields = [x for x in include_fields if x in mat.index]
    if not include_fields:
        return mat.iloc[0:0, 0:0]
    return mat.loc[include_fields, include_fields]


def chord_html(
    labels: list[str],
    matrix: list[list[int]],
    palette: str,
    sort_mode: str,
    label_font_px: int,
    max_label_chars: int,
    show_labels: bool,
) -> str:
    palettes = {
        "tableau10": ["#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F","#EDC948","#B07AA1","#FF9DA7","#9C755F","#BAB0AC"],
        "set3": ["#8DD3C7","#FFFFB3","#BEBADA","#FB8072","#80B1D3","#FDB462","#B3DE69","#FCCDE5","#D9D9D9","#BC80BD","#CCEBC5","#FFED6F"],
        "paired": ["#A6CEE3","#1F78B4","#B2DF8A","#33A02C","#FB9A99","#E31A1C","#FDBF6F","#FF7F00","#CAB2D6","#6A3D9A","#FFFF99","#B15928"],
    }
    colors = palettes.get(palette, palettes["tableau10"])

    payload = {
        "labels": labels,
        "matrix": matrix,
        "colors": colors,
        "sort_mode": sort_mode,
        "label_font_px": int(label_font_px),
        "max_label_chars": int(max_label_chars),
        "show_labels": bool(show_labels),
    }
    data_json = json.dumps(payload)

    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://d3js.org/d3.v6.min.js"></script>
  <style>
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      background: white;
    }
    #wrap {
      width: 100%;
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .tooltip {
      position: absolute;
      pointer-events: none;
      background: rgba(0,0,0,0.78);
      color: #fff;
      padding: 8px 10px;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.25;
      opacity: 0;
      transition: opacity 0.08s ease-in-out;
      max-width: 520px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.22);
      white-space: nowrap;
    }
    .label {
      font-weight: 600;
      fill: #111;
    }
  </style>
</head>
<body>
<div id="wrap"></div>
<div class="tooltip" id="tt"></div>

<script>
  const data = """ + data_json + """;
  const labels = data.labels;
  const matrix = data.matrix;
  const colors = data.colors;
  const sortMode = data.sort_mode;
  const labelFont = data.label_font_px;
  const maxLabelChars = data.max_label_chars;
  const showLabels = data.show_labels;

  const container = document.getElementById("wrap");
  const tooltip = d3.select("#tt");

  const W = Math.min(window.innerWidth, 1180);
  const H = Math.min(window.innerHeight, 760);
  const outerRadius = Math.min(W, H) * 0.40;
  const innerRadius = outerRadius - 26;

  const chordGen = d3.chord()
    .padAngle(0.03)
    .sortSubgroups(sortMode === "desc" ? d3.descending : null);

  const chords = chordGen(matrix);

  // Totals per area (row sums) for percentage tooltips
  const totals = matrix.map(row => d3.sum(row));
  const grandTotal = d3.sum(totals);

  const arc = d3.arc()
    .innerRadius(innerRadius)
    .outerRadius(outerRadius);

  const ribbon = d3.ribbon()
    .radius(innerRadius);

  const svg = d3.select(container)
    .append("svg")
    .attr("width", W)
    .attr("height", H)
    .append("g")
    .attr("transform", `translate(${W/2},${H/2})`);

  const color = d3.scaleOrdinal()
    .domain(d3.range(labels.length))
    .range(colors);

  const group = svg.append("g")
    .selectAll("g")
    .data(chords.groups)
    .join("g");

  const ribbons = svg.append("g")
    .attr("fill-opacity", 0.75)
    .selectAll("path")
    .data(chords)
    .join("path")
      .attr("d", ribbon)
      .attr("fill", d => color(d.source.index))
      .attr("stroke", d => d3.color(color(d.source.index)).darker(0.6))
      .on("mousemove", (event, d) => {
        const src = labels[d.source.index];
        const tgt = labels[d.target.index];
        const v = d.source.value;
        const pctSrc = totals[d.source.index] ? (v / totals[d.source.index]) * 100 : 0;

        tooltip
          .style("opacity", 1)
          .html(
            `<div><b>${src}</b> → <b>${tgt}</b></div>` +
            `<div>Valore: ${v} <span style="opacity:.85;">(${pctSrc.toFixed(1)}%)</span></div>`
          )
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      })
      .on("mouseout", () => tooltip.style("opacity", 0));

  group.append("path")
    .attr("d", arc)
    .attr("fill", d => color(d.index))
    .attr("stroke", d => d3.color(color(d.index)).darker(0.6))
    .on("mousemove", (event, d) => {
      const area = labels[d.index];
      const pctAll = grandTotal ? (d.value / grandTotal) * 100 : 0;

      tooltip
        .style("opacity", 1)
        .html(
          `<div><b>${area}</b></div>` +
          `<div>Totale: ${d.value} <span style="opacity:.85;">(${pctAll.toFixed(1)}%)</span></div>`
        )
        .style("left", (event.pageX + 12) + "px")
        .style("top", (event.pageY + 12) + "px");
    })
    .on("mouseout", () => tooltip.style("opacity", 0))
    .on("mouseenter", (event, d) => {
      const idx = d.index;
      ribbons.attr("opacity", r => (r.source.index === idx || r.target.index === idx) ? 0.9 : 0.06);
    })
    .on("mouseleave", () => {
      ribbons.attr("opacity", 0.75);
    });

  function truncLabel(s) {
    if (!s) return "";
    if (s.length <= maxLabelChars) return s;
    return s.slice(0, maxLabelChars - 1) + "…";
  }

  if (showLabels) {
    group.append("text")
      .each(d => d.angle = (d.startAngle + d.endAngle) / 2)
      .attr("dy", "0.35em")
      .attr("transform", d => `
        rotate(${d.angle * 180 / Math.PI - 90})
        translate(${outerRadius + 18})
        ${d.angle > Math.PI ? "rotate(180)" : ""}
      `)
      .attr("text-anchor", d => d.angle > Math.PI ? "end" : "start")
      .style("font-size", labelFont + "px")
      .style("fill", "#111")
      .text(d => truncLabel(labels[d.index]));
  }
</script>
</body>
</html>
"""

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Collaborazioni tra aree scientifiche", layout="wide")

st.markdown("<h1 style='margin-bottom:0.2rem;'>Collaborazioni tra aree scientifiche</h1>", unsafe_allow_html=True)

# Load data
df_papers = pd.read_csv(DF_PATH)
cen_df = pd.read_csv(CEN_PATH)

total_papers = len(df_papers)

st.markdown(
    f"<div style='font-size: 0.95rem; color: #666;'>Corpus analizzato: <b>{total_papers}</b> paper &nbsp;&nbsp;|&nbsp;&nbsp; Collaborazioni tra aree (basate su <b>co-autori</b>) &nbsp;&nbsp;|&nbsp;&nbsp; Aggiornamento: <b>{UPDATE_STR}</b></div>",
    unsafe_allow_html=True,
)

st.write("")

with st.sidebar:
    st.header("Filtri")

    # Build matrix once (paper-level collaboration)
    base_mat = collaboration_matrix_paper_level(df_papers, cen_df)

    fields_all = base_mat.index.tolist()
    include_fields = st.multiselect("Aree incluse", options=fields_all, default=fields_all)

    min_value = st.slider("Soglia minima collaborazione (link)", min_value=1, max_value=20, value=1, step=1)

    palette = st.selectbox("Palette", ["tableau10", "set3", "paired"], index=0)
    sort_mode = st.selectbox("Ordinamento sottogruppi", ["none", "desc"], index=1)
    label_font_px = st.slider("Dimensione font etichette", min_value=8, max_value=22, value=12, step=1)
    max_label_chars = st.slider("Max caratteri etichetta", min_value=8, max_value=60, value=28, step=1)
    show_labels = st.checkbox("Mostra etichette", value=True)

# Apply filters
mat = base_mat.copy()
mat = filter_fields(mat, include_fields)
mat = apply_threshold(mat, min_value)

# Remove all-zero rows/cols to keep only connected nodes
nonzero = (mat.sum(axis=1) > 0)
mat = mat.loc[nonzero, nonzero]

labels = mat.index.tolist()
matrix = mat.values.tolist()

if not labels:
    st.info("Nessun collegamento da visualizzare con i filtri correnti. Prova ad includere più aree e/o abbassare la soglia.")
else:
    components.html(
        chord_html(
            labels=labels,
            matrix=matrix,
            palette=palette,
            sort_mode=sort_mode,
            label_font_px=label_font_px,
            max_label_chars=max_label_chars,
            show_labels=show_labels,
        ),
        height=760,
        scrolling=False,
    )