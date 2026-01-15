# app.py
import json
from itertools import combinations

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ----------------------------
# Data prep utilities
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


def build_name_to_field(cen: pd.DataFrame) -> dict:
    cen2 = cen.copy()
    cen2["full_name"] = cen2["full_name"].astype(str).map(normalise_name)
    cen2["Area_desc"] = cen2["Area_desc"].astype(str).map(lambda x: " ".join(str(x).split()))

    cen2 = cen2.dropna(subset=["full_name", "Area_desc"])
    cen2 = cen2[cen2["full_name"].ne("") & cen2["Area_desc"].ne("")]

    # If duplicates exist, keep first. Adjust policy if needed.
    cen2 = cen2.drop_duplicates(subset=["full_name"], keep="first")

    return cen2.set_index("full_name")["Area_desc"].to_dict()


def collaboration_matrix(df: pd.DataFrame, cen: pd.DataFrame, mode: str = "pairwise") -> pd.DataFrame:
    """
    mode:
      - pairwise: counts all co-author pairs (field-field counts grow with team size)
      - paper_level: each field-field pair counts at most once per paper
    """
    name_to_field = build_name_to_field(cen)

    if "authors_full" not in df.columns:
        raise ValueError("df must contain a column named 'authors_full'.")
    if not {"full_name", "Area_desc"}.issubset(set(cen.columns)):
        raise ValueError("cen must contain columns: 'full_name' and 'Area_desc'.")

    fields_per_paper = []
    for s in df["authors_full"]:
        authors = parse_authors(s)
        fields = [name_to_field.get(a, np.nan) for a in authors]
        fields = [f for f in fields if pd.notna(f)]
        fields_per_paper.append(fields)

    counts: dict[tuple[str, str], int] = {}

    for fields in fields_per_paper:
        if len(fields) < 2:
            continue

        if mode == "pairwise":
            for f1, f2 in combinations(fields, 2):
                a, b = sorted((f1, f2))
                counts[(a, b)] = counts.get((a, b), 0) + 1

        elif mode == "paper_level":
            uniq = sorted(set(fields))
            for f1, f2 in combinations(uniq, 2):
                counts[(f1, f2)] = counts.get((f1, f2), 0) + 1

        else:
            raise ValueError("mode must be 'pairwise' or 'paper_level'")

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


# ----------------------------
# D3 chord HTML generator
# ----------------------------
def chord_html(labels: list[str], matrix: list[list[int]], palette: str, sort_mode: str) -> str:
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
    }
    data_json = json.dumps(payload)

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://d3js.org/d3.v6.min.js"></script>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
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
    .label {{
      font-size: 11px;
      fill: #222;
    }}
    .tooltip {{
      position: absolute;
      padding: 8px 10px;
      background: rgba(0,0,0,0.78);
      color: #fff;
      border-radius: 6px;
      pointer-events: none;
      font-size: 12px;
      line-height: 1.25;
    }}
  </style>
</head>
<body>
  <div class="wrap" id="chart"></div>

  <script>
    const payload = {data_json};
    const labels = payload.labels;
    const matrix = payload.matrix;
    const colors = payload.colors;
    const sortMode = payload.sort_mode;

    const container = document.getElementById("chart");
    const w = container.clientWidth || 900;
    const h = 700;

    const outerRadius = Math.min(w, h) * 0.38;
    const innerRadius = outerRadius - 18;

    const color = d3.scaleOrdinal()
      .domain(d3.range(labels.length))
      .range(colors.length >= labels.length
            ? colors
            : d3.range(labels.length).map(i => colors[i % colors.length]));

    const chordGen = d3.chord()
      .padAngle(0.03);

    if (sortMode === "groups_desc") {{
      chordGen.sortGroups(d3.descending);
    }} else if (sortMode === "subgroups_desc") {{
      chordGen.sortSubgroups(d3.descending);
    }} else if (sortMode === "chords_desc") {{
      chordGen.sortChords(d3.descending);
    }}

    const chords = chordGen(matrix);

    const arc = d3.arc()
      .innerRadius(innerRadius)
      .outerRadius(outerRadius);

    const ribbon = d3.ribbon()
      .radius(innerRadius);

    const svg = d3.select(container)
      .append("svg")
      .attr("viewBox", [-w/2, -h/2, w, h]);

    const tooltip = d3.select("body")
      .append("div")
      .attr("class", "tooltip")
      .style("opacity", 0);

    const group = svg.append("g")
      .selectAll("g")
      .data(chords.groups)
      .join("g");

    group.append("path")
      .attr("d", arc)
      .attr("fill", d => color(d.index))
      .attr("stroke", d => d3.color(color(d.index)).darker(0.6))
      .on("mousemove", (event, d) => {{
        tooltip
          .style("opacity", 1)
          .html(`<div><b>${{labels[d.index]}}</b></div><div>Total: ${{d.value}}</div>`)
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      }})
      .on("mouseout", () => tooltip.style("opacity", 0))
      .on("mouseenter", (event, d) => {{
        const idx = d.index;
        ribbons.attr("opacity", r => (r.source.index === idx || r.target.index === idx) ? 0.9 : 0.08);
      }})
      .on("mouseleave", () => {{
        ribbons.attr("opacity", 0.75);
      }});

    group.append("text")
      .each(d => d.angle = (d.startAngle + d.endAngle) / 2)
      .attr("class", "label")
      .attr("dy", "0.35em")
      .attr("transform", d => {{
        const rotate = d.angle * 180 / Math.PI - 90;
        const translate = outerRadius + 22;
        const flip = d.angle > Math.PI ? " rotate(180)" : "";
        return `rotate(${{rotate}}) translate(${{translate}})${{flip}}`;
      }})
      .attr("text-anchor", d => d.angle > Math.PI ? "end" : "start")
      .text(d => labels[d.index]);

    const ribbons = svg.append("g")
      .attr("fill-opacity", 0.75)
      .selectAll("path")
      .data(chords)
      .join("path")
      .attr("d", ribbon)
      .attr("fill", d => color(d.source.index))
      .attr("stroke", d => d3.color(color(d.source.index)).darker(0.6))
      .on("mousemove", (event, d) => {{
        const src = labels[d.source.index];
        const tgt = labels[d.target.index];
        const v = d.source.value;
        tooltip
          .style("opacity", 1)
          .html(`<div><b>${{src}}</b> → <b>${{tgt}}</b></div><div>Value: ${{v}}</div>`)
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      }})
      .on("mouseout", () => tooltip.style("opacity", 0));
  </script>
</body>
</html>
"""


# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(layout="wide")
st.title("Scientific field collaboration chord diagram")

st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Counting mode", ["pairwise", "paper_level"], index=0)
min_value = st.sidebar.slider("Minimum value threshold", min_value=0, max_value=50, value=1, step=1)
palette = st.sidebar.selectbox("Colour palette", ["tableau10", "set3", "paired"], index=0)
sort_mode = st.sidebar.selectbox("Sorting", ["none", "groups_desc", "subgroups_desc", "chords_desc"], index=0)


# --- Load CSVs here ---
# df must have: authors_full
# cen must have: full_name, Area_desc

df = pd.read_csv("/Users/navid/Documents/1_Projects/0_Age-It/Our Tasks/Mario_report/data/processed/chord_authors.csv")          # must contain authors_full
cen = pd.read_csv("/Users/navid/Documents/1_Projects/0_Age-It/Our Tasks/Mario_report/data/processed/chord_area.csv")        

# Optional: enforce required columns early
required_df = {"authors_full"}
required_cen = {"full_name", "Area_desc"}
if not required_df.issubset(df.columns):
    raise ValueError(f"df is missing columns: {required_df - set(df.columns)}")
if not required_cen.issubset(cen.columns):
    raise ValueError(f"cen is missing columns: {required_cen - set(cen.columns)}")



# Expect df and cen to exist, or load them here.
if "df" not in globals() or "cen" not in globals():
    st.warning("This app expects `df` (column `authors_full`) and `cen` (columns `full_name`, `Area_desc`) to be defined or loaded.")
    st.stop()

mat = collaboration_matrix(df=df, cen=cen, mode=mode)
mat = apply_threshold(mat, min_value=min_value)

# Remove all-zero rows/cols after thresholding
nonzero = (mat.sum(axis=1) > 0)
mat = mat.loc[nonzero, nonzero]

labels = mat.index.tolist()
matrix = mat.values.tolist()

col1, col2 = st.columns([2, 1], vertical_alignment="top")

with col1:
    if not labels:
        st.info("No collaborations remain after thresholding. Lower the threshold.")
    else:
        components.html(chord_html(labels, matrix, palette, sort_mode), height=720, scrolling=False)

with col2:
    st.subheader("Matrix preview")
    st.write(f"Fields: {len(labels)}")
    st.dataframe(mat)