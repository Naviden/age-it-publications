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
LOGO_PATH = BASE_DIR / "logo.jpg"                   # logo next to app.py

df = pd.read_csv(DF_PATH)
cen = pd.read_csv(CEN_PATH)


# ----------------------------
# Caricamento dati (come richiesto)
# ----------------------------
# DF_PATH = "/Users/navid/Documents/1_Projects/0_Age-It/Our Tasks/Mario_report/data/processed/chord_authors.csv"
# CEN_PATH = "/Users/navid/Documents/1_Projects/0_Age-It/Our Tasks/Mario_report/data/processed/chord_area.csv"

df = pd.read_csv(DF_PATH)   # deve contenere: authors_full
cen = pd.read_csv(CEN_PATH) # deve contenere: full_name, Area_desc

# Modalità fissa: paper-based
COUNT_MODE = "paper_level"

# Data aggiornamento (impostata come richiesto)
UPDATE_STR = "08/01/2026"


# ----------------------------
# Utility di preparazione dati
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
    # Se ci sono duplicati, mantieni la prima occorrenza (modifica qui se preferisci altra logica)
    c = c.drop_duplicates(subset=["full_name"], keep="first")

    return c.set_index("full_name")["Area_desc"].to_dict()


def collaboration_matrix_paper_level(df_papers: pd.DataFrame, cen_df: pd.DataFrame) -> pd.DataFrame:
    """
    Paper-based: per ogni paper conta una sola volta ogni coppia area-area.
    """
    required_df = {"authors_full"}
    required_cen = {"full_name", "Area_desc"}
    if not required_df.issubset(df_papers.columns):
        raise ValueError(f"df non contiene le colonne richieste: {required_df - set(df_papers.columns)}")
    if not required_cen.issubset(cen_df.columns):
        raise ValueError(f"cen non contiene le colonne richieste: {required_cen - set(cen_df.columns)}")

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


# ----------------------------
# Generatore HTML D3 chord
# ----------------------------
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
      overflow: hidden;
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
    const labelFontPx = payload.label_font_px ?? 8;
    const maxLabelChars = payload.max_label_chars ?? 22;
    const showLabels = payload.show_labels ?? true;

    function truncateLabel(s) {{
      if (!s) return "";
      return s.length > maxLabelChars ? (s.slice(0, maxLabelChars - 1) + "…") : s;
    }}

    const container = document.getElementById("chart");
    const w = container.clientWidth || 980;
    const h = 720;

    const outerRadius = Math.min(w, h) * 0.43;
    const innerRadius = outerRadius - 16;

    const color = d3.scaleOrdinal()
      .domain(d3.range(labels.length))
      .range(colors.length >= labels.length
            ? colors
            : d3.range(labels.length).map(i => colors[i % colors.length]));

    const chordGen = d3.chord()
      .padAngle(0.015);

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
          .html(`<div><b>${{src}}</b> → <b>${{tgt}}</b></div><div>Valore: ${{v}}</div>`)
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      }})
      .on("mouseout", () => tooltip.style("opacity", 0));

    group.append("path")
      .attr("d", arc)
      .attr("fill", d => color(d.index))
      .attr("stroke", d => d3.color(color(d.index)).darker(0.6))
      .on("mousemove", (event, d) => {{
        tooltip
          .style("opacity", 1)
          .html(`<div><b>${{labels[d.index]}}</b></div><div>Totale: ${{d.value}}</div>`)
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      }})
      .on("mouseout", () => tooltip.style("opacity", 0))
      .on("mouseenter", (event, d) => {{
        const idx = d.index;
        ribbons.attr("opacity", r => (r.source.index === idx || r.target.index === idx) ? 0.9 : 0.06);
      }})
      .on("mouseleave", () => {{
        ribbons.attr("opacity", 0.75);
      }});

    if (showLabels) {{
      group.append("text")
        .each(d => d.angle = (d.startAngle + d.endAngle) / 2)
        .attr("class", "label")
        .style("font-size", labelFontPx + "px")
        .attr("dy", "0.35em")
        .attr("transform", d => {{
          const rotate = d.angle * 180 / Math.PI - 90;
          const translate = outerRadius + 12;
          const flip = d.angle > Math.PI ? " rotate(180)" : "";
          return `rotate(${{rotate}}) translate(${{translate}})${{flip}}`;
        }})
        .attr("text-anchor", d => d.angle > Math.PI ? "end" : "start")
        .text(d => truncateLabel(labels[d.index]))
        .on("mousemove", (event, d) => {{
          tooltip
            .style("opacity", 1)
            .html(`<div><b>${{labels[d.index]}}</b></div>`)
            .style("left", (event.pageX + 12) + "px")
            .style("top", (event.pageY + 12) + "px");
        }})
        .on("mouseout", () => tooltip.style("opacity", 0));
    }}
  </script>
</body>
</html>
"""


# ----------------------------
# UI Streamlit (in italiano + tooltip help ovunque)
# ----------------------------
st.set_page_config(layout="wide")

# Logo in alto
# Nota: metti logo.png nella stessa cartella di app.py (src/) oppure passa un path assoluto
st.image(LOGO_PATH, use_container_width=False, width=180)

st.title("Collaborazioni tra aree scientifiche")

# Numero totale paper (righe del CSV) e data aggiornamento sotto al titolo
total_papers = int(len(df))
st.markdown(
    f"<div style='font-size: 0.95rem; color: #666;'>Totale paper: <b>{total_papers}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Aggiornamento: <b>{UPDATE_STR}</b></div>",
    unsafe_allow_html=True,
)

st.sidebar.header("Parametri")

min_value = st.sidebar.slider(
    "Soglia minima (filtra i collegamenti deboli)",
    min_value=0,
    max_value=50,
    value=2,
    step=1,
    help=(
        "Imposta a 0 tutti i valori sotto questa soglia per ridurre il disordine visivo "
        "(meno ribbon/collegamenti nel diagramma)."
    ),
)

palette = st.sidebar.selectbox(
    "Palette colori",
    ["tableau10", "set3", "paired"],
    index=0,
    help="Cambia i colori assegnati alle aree (archi esterni).",
)

sort_mode = st.sidebar.selectbox(
    "Ordinamento",
    ["none", "groups_desc", "subgroups_desc", "chords_desc"],
    index=0,
    help=(
        "none: nessun ordinamento. "
        "groups_desc: ordina gli archi per totale decrescente. "
        "subgroups_desc: ordina i sotto-flussi per area in modo decrescente. "
        "chords_desc: ordina i collegamenti (ribbon) per valore decrescente."
    ),
)

st.sidebar.divider()
st.sidebar.subheader("Etichette")

show_labels = st.sidebar.checkbox(
    "Mostra etichette",
    value=True,
    help="Mostra/nasconde le etichette testuali attorno al cerchio. In ogni caso il nome completo appare al passaggio del mouse.",
)

label_font_px = st.sidebar.slider(
    "Dimensione etichette (px)",
    6, 14, 8, 1,
    disabled=not show_labels,
    help="Dimensione del testo delle etichette. Riduci se i nomi sono lunghi o le aree sono molte.",
)

max_label_chars = st.sidebar.slider(
    "Lunghezza massima etichette",
    10, 80, 24, 1,
    disabled=not show_labels,
    help="Tronca le etichette oltre questo numero di caratteri (mostra '…'). Il nome completo resta disponibile in tooltip.",
)

st.sidebar.divider()
st.sidebar.subheader("Aree da includere/escludere")

# Matrice completa (paper-based)
mat_full = collaboration_matrix_paper_level(df_papers=df, cen_df=cen)
all_fields = mat_full.index.tolist()

selected_fields = st.sidebar.multiselect(
    "Seleziona le aree da includere",
    options=all_fields,
    default=all_fields,
    help="Seleziona le aree da visualizzare. Le aree non selezionate vengono escluse (righe/colonne).",
)

mat = filter_fields(mat_full, selected_fields)
mat = apply_threshold(mat, min_value=min_value)

# Rimuovi righe/colonne a somma zero dopo la soglia
if not mat.empty:
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
        height=780,
        scrolling=False,
    )

    st.caption(
        "Il diagramma mostra le collaborazioni tra aree scientifiche. "
        "Ogni arco esterno rappresenta un’area: la sua ampiezza è proporzionale al totale delle collaborazioni dell’area. "
        "I collegamenti interni (ribbon) indicano collaborazioni tra coppie di aree: lo spessore è proporzionale al numero di paper "
        "in cui co-occorrono autori appartenenti a quelle due aree (conteggio paper-based). "
        "Passa il mouse su un’area o su un collegamento per vedere i dettagli."
    )