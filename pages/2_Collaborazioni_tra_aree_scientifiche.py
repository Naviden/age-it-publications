# pages/2_Collaborazioni_tra_aree_scientifiche.py
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Collaborazioni", layout="wide")

# ----------------------------
# Paths (NON CAMBIATI)
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent          # .../pages
REPO_DIR = BASE_DIR.parent                          # repo root

DF_PATH = REPO_DIR / "data" / "processed" / "chord_authors.csv"
CEN_PATH = REPO_DIR / "data" / "processed" / "chord_area.csv"
LOGO_PATH = REPO_DIR / "logo.jpg"                   # come nel tuo progetto (se diverso, lascia il tuo)

UPDATE_STR = "08/01/2026"


# ----------------------------
# Load data
# ----------------------------
if not DF_PATH.exists():
    st.error(f"File non trovato: {DF_PATH}")
    st.stop()
if not CEN_PATH.exists():
    st.error(f"File non trovato: {CEN_PATH}")
    st.stop()

df = pd.read_csv(DF_PATH)   # deve contenere: authors_full
cen = pd.read_csv(CEN_PATH) # deve contenere: full_name, Area_desc


# ----------------------------
# Data utilities
# ----------------------------
def normalise_name(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = " ".join(s.split())
    return s


def parse_authors(authors_full: str) -> list[str]:
    if pd.isna(authors_full):
        return []
    out = [normalise_name(a) for a in str(authors_full).split(",")]
    return [a for a in out if a]


def build_name_to_field(cen_df: pd.DataFrame) -> dict:
    c = cen_df.copy()
    c["full_name"] = c["full_name"].astype(str).map(normalise_name)
    c["Area_desc"] = c["Area_desc"].astype(str).map(lambda x: " ".join(str(x).split()))

    c = c.dropna(subset=["full_name", "Area_desc"])
    c = c[c["full_name"].ne("") & c["Area_desc"].ne("")]
    c = c.drop_duplicates(subset=["full_name"], keep="first")

    return c.set_index("full_name")["Area_desc"].to_dict()


def collaboration_matrix_paper_level(df_papers: pd.DataFrame, cen_df: pd.DataFrame) -> pd.DataFrame:
    """
    Paper-based: per ogni paper conta una sola volta ogni coppia area-area (unica).
    """
    required_df = {"authors_full"}
    required_cen = {"full_name", "Area_desc"}
    if not required_df.issubset(df_papers.columns):
        raise ValueError(f"df non contiene: {required_df - set(df_papers.columns)}")
    if not required_cen.issubset(cen_df.columns):
        raise ValueError(f"cen non contiene: {required_cen - set(cen_df.columns)}")

    name_to_field = build_name_to_field(cen_df)

    fields_per_paper: list[list[str]] = []
    for s in df_papers["authors_full"]:
        authors = parse_authors(s)
        fields = [name_to_field.get(a, np.nan) for a in authors]
        fields = [f for f in fields if pd.notna(f)]
        fields_per_paper.append(fields)

    counts: dict[tuple[str, str], int] = {}
    for fields in fields_per_paper:
        if len(fields) < 2:
            continue
        uniq = sorted(set(fields))
        for f1, f2 in combinations(uniq, 2):
            counts[(f1, f2)] = counts.get((f1, f2), 0) + 1

    fields_all = sorted({x for pair in counts.keys() for x in pair})
    mat = pd.DataFrame(0, index=fields_all, columns=fields_all, dtype=int)

    for (a, b), v in counts.items():
        mat.loc[a, b] += v
        mat.loc[b, a] += v

    return mat


def apply_threshold(mat: pd.DataFrame, min_value: int) -> pd.DataFrame:
    m = mat.copy()
    m.values[m.values < min_value] = 0
    return m


def filter_fields(mat: pd.DataFrame, include_fields: list[str]) -> pd.DataFrame:
    if not include_fields:
        return mat.iloc[0:0, 0:0]
    include_fields = [f for f in include_fields if f in mat.index]
    return mat.loc[include_fields, include_fields]


def reorder(mat: pd.DataFrame, mode: str) -> pd.DataFrame:
    if mat.empty:
        return mat
    if mode == "alphabetical":
        order = sorted(mat.index)
        return mat.loc[order, order]
    if mode == "degree":
        deg = mat.sum(axis=1).sort_values(ascending=False)
        order = deg.index.tolist()
        return mat.loc[order, order]
    return mat


# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.header("Parametri")

min_value = st.sidebar.slider(
    "Soglia minima (filtra i collegamenti deboli)",
    min_value=1,
    max_value=25,
    value=2,
    step=1,
)

palette = st.sidebar.selectbox(
    "Palette colori",
    ["tableau10", "set3", "category10"],
    index=0,
)

ordering = st.sidebar.selectbox(
    "Ordinamento",
    ["none", "alphabetical", "degree"],
    index=0,
)

st.sidebar.divider()
st.sidebar.subheader("Etichette")

show_labels = st.sidebar.checkbox("Mostra etichette", value=True)

label_font_size = st.sidebar.slider(
    "Dimensione etichette (px)",
    min_value=7,
    max_value=16,
    value=9,
    step=1,
)

wrap_chars = st.sidebar.slider(
    "Caratteri per riga (wrap)",
    min_value=10,
    max_value=40,
    value=18,
    step=1,
)

# ----------------------------
# Compute matrix
# ----------------------------
mat_full = collaboration_matrix_paper_level(df, cen)
total_papers = len(df)

# include/exclude aree
all_fields = mat_full.index.tolist()
selected_fields = st.sidebar.multiselect(
    "Includi/Escludi aree (se vuoto: nessuna)",
    options=all_fields,
    default=all_fields,
)

mat = filter_fields(mat_full, selected_fields)
mat = apply_threshold(mat, min_value=min_value)
mat = reorder(mat, ordering)

# ----------------------------
# Header
# ----------------------------
col_logo, col_title = st.columns([1, 6], vertical_alignment="center")
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=160)

with col_title:
    st.title("Collaborazioni tra aree scientifiche")
    st.markdown(
        f"<div style='color:#777; margin-top:-6px;'>Totale paper: <b>{total_papers}</b> &nbsp;|&nbsp; Aggiornamento: <b>{UPDATE_STR}</b></div>",
        unsafe_allow_html=True,
    )

st.write("")


# ----------------------------
# D3 chord (HTML)
# ----------------------------
def chord_html(matrix: pd.DataFrame, labels: list[str]) -> str:
    payload = {
        "labels": labels,
        "matrix": matrix.values.tolist(),
        "show_labels": bool(show_labels),
        "label_font_size": int(label_font_size),
        "wrap_chars": int(wrap_chars),
        "palette": palette,
    }
    data_json = json.dumps(payload, ensure_ascii=False)

    # NOTE: NON usare f-string qui dentro (evitiamo casini con { } di JS)
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #fff;
    }
    #wrap {
      width: 100%;
      height: 900px;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    svg { width: 100%; height: 100%; display: block; }
    .tooltip {
      position: absolute;
      padding: 8px 10px;
      background: rgba(0,0,0,0.82);
      color: #fff;
      border-radius: 8px;
      font-size: 12px;
      pointer-events: none;
      line-height: 1.2;
    }
  </style>
</head>
<body>
  <div id="wrap"></div>

  <script>
    const payload = __DATA_JSON__;

    const labels = payload.labels || [];
    const matrix = payload.matrix || [];
    const showLabels = payload.show_labels;
    const labelFontSize = payload.label_font_size || 10;
    const wrapChars = payload.wrap_chars || 18;
    const paletteName = payload.palette || "tableau10";

    const container = document.getElementById("wrap");
    const width = container.clientWidth || 1100;
    const height = container.clientHeight || 900;

    // extra padding to avoid clipping labels
    const outerPad = 140;

    const svg = d3.select(container).append("svg")
      .attr("viewBox", [0, 0, width, height]);

    const g = svg.append("g")
      .attr("transform", `translate(${width/2},${height/2})`);

    const outerRadius = Math.min(width, height) / 2 - outerPad;
    const innerRadius = outerRadius - 22;

    const chord = d3.chord()
      .padAngle(0.03)
      .sortSubgroups(d3.descending);

    const arc = d3.arc()
      .innerRadius(innerRadius)
      .outerRadius(outerRadius);

    const ribbon = d3.ribbon()
      .radius(innerRadius);

    const color = (paletteName === "set3")
      ? d3.scaleOrdinal(d3.schemeSet3)
      : (paletteName === "category10" ? d3.scaleOrdinal(d3.schemeCategory10)
                                      : d3.scaleOrdinal(d3.schemeTableau10));

    const chords = chord(matrix);

    const tooltip = d3.select("body").append("div")
      .attr("class", "tooltip")
      .style("opacity", 0);

    // ---- Label wrapping (NO TRUNCATION) ----
    function wrapLabel(text, maxCharsPerLine) {
      const words = (text || "").split(/\\s+/).filter(Boolean);
      const lines = [];
      let line = "";
      for (const w of words) {
        const candidate = line ? (line + " " + w) : w;
        if (candidate.length <= maxCharsPerLine) {
          line = candidate;
        } else {
          if (line) lines.push(line);
          line = w;
        }
      }
      if (line) lines.push(line);
      return lines; // no truncation
    }

    // Groups (outer arcs)
    const group = g.append("g")
      .selectAll("g")
      .data(chords.groups)
      .join("g");

    group.append("path")
      .attr("fill", d => color(d.index))
      .attr("stroke", d => d3.color(color(d.index)).darker(0.3))
      .attr("d", arc);

    // Ribbons (links)
    g.append("g")
      .attr("fill-opacity", 0.65)
      .selectAll("path")
      .data(chords)
      .join("path")
      .attr("d", ribbon)
      .attr("fill", d => color(d.target.index))
      .attr("stroke", d => d3.color(color(d.target.index)).darker(0.3))
      .on("mousemove", (event, d) => {
        const a = labels[d.source.index] ?? "";
        const b = labels[d.target.index] ?? "";
        tooltip
          .style("opacity", 1)
          .html(`<b>${a}</b> → <b>${b}</b><br/>Co-paper: ${d.source.value}`)
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      })
      .on("mouseout", () => tooltip.style("opacity", 0));

    // Labels
    // Labels (fixed orientation)
    if (showLabels) {
      const labelRadius = outerRadius + 18;

      const labelG = group.append("g")
        .attr("transform", d => {
          const a = (d.startAngle + d.endAngle) / 2;
          const rotate = (a * 180 / Math.PI) - 90;
          return `rotate(${rotate}) translate(${labelRadius},0)`;
        });

      // small leader line
      labelG.append("line")
        .attr("x1", 0).attr("x2", 14)
        .attr("y1", 0).attr("y2", 0)
        .attr("stroke", "#999");

      labelG.each(function(d) {
        const a = (d.startAngle + d.endAngle) / 2;
        const isLeftSide = a > Math.PI;              // left half of circle
        const txt = labels[d.index] ?? "";
        const lines = wrapLabel(txt, wrapChars);

        const text = d3.select(this).append("text")
          .attr("x", 20)
          .attr("y", 0)
          .style("font-size", labelFontSize + "px")
          .style("font-weight", 500)
          .style("fill", "#111")
          .attr("text-anchor", isLeftSide ? "end" : "start")
          // IMPORTANT: rotate(180) for left side (not scale), keeps direction consistent
          .attr("transform", isLeftSide ? "rotate(180)" : null);

        // Multi-line wrap (no truncation)
        // We centre vertically around the anchor by starting at negative offset
        const lineHeightEm = 1.12;
        const y0 = -((lines.length - 1) * lineHeightEm) / 2;

        lines.forEach((line, i) => {
          text.append("tspan")
            .attr("x", 20)
            .attr("dy", (i === 0 ? `${y0}em` : `${lineHeightEm}em`))
            .text(line);
        });
      });
    }
  </script>
</body>
</html>
"""
    return html.replace("__DATA_JSON__", data_json)


# ----------------------------
# Render
# ----------------------------
if mat.empty or mat.shape[0] < 2:
    st.warning("Dopo filtri/soglia non ci sono abbastanza aree per costruire il diagramma.")
else:
    html = chord_html(mat, mat.index.tolist())
    components.html(html, height=900, scrolling=True)

st.caption(
    "Il diagramma chord mostra le collaborazioni tra aree scientifiche ricavate dalle co-autorialità. "
    "Ogni collegamento indica il numero di paper (paper-based) in cui compaiono autori di entrambe le aree."
)