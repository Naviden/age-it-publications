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

DATA_PATH = REPO_DIR / "data" / "processed" / "donut_data.csv"
LOGO_PATH = REPO_DIR / "logo.jpg"


# ----------------------------
# Load data (NORMAL loading)
# ----------------------------
if not DATA_PATH.exists():
    st.error(f"File non trovato: {DATA_PATH}")
    st.stop()

df = pd.read_csv(DATA_PATH)

required_cols = {"orig_label", "count", "short_label", "TN"}
missing = required_cols - set(df.columns)
if missing:
    st.error(
        "Il CSV deve contenere le colonne: "
        + ", ".join(sorted(required_cols))
        + f". Mancanti: {', '.join(sorted(missing))}"
    )
    st.stop()

# Basic cleaning
df["orig_label"] = df["orig_label"].fillna("").astype(str)
df["short_label"] = df["short_label"].fillna("").astype(str)
df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)

# Normalize TN (still standard cleaning, not a custom loader)
df["TN"] = (
    df["TN"]
    .astype(str)
    .str.strip()
    .str.replace(r"[^\d]", "", regex=True)
)
df["TN"] = pd.to_numeric(df["TN"], errors="coerce").astype("Int64")


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
        "<div style='color:#777;'>Distribuzione delle categorie narrative.</div>",
        unsafe_allow_html=True,
    )

st.write("")


# ----------------------------
# Sidebar controls
# ----------------------------
st.sidebar.header("Parametri")

label_choice = st.sidebar.selectbox(
    "Etichette",
    options=[
        ("Etichette brevi", "short_label"),
        ("Etichette originali", "orig_label"),
    ],
    index=0,
    format_func=lambda x: x[0],
    help="Scegli quale colonna usare come etichetta nel grafico.",
)
label_col = label_choice[1]

show_percent_on_labels = st.sidebar.checkbox(
    "Mostra percentuali sulle etichette",
    value=False,
    help="Aggiunge la percentuale accanto alle etichette (il tooltip include sempre percentuale).",
)

label_font_px = st.sidebar.slider(
    "Dimensione etichette (px)",
    min_value=10,
    max_value=26,
    value=14,
    step=1,
)

wrap_chars = st.sidebar.slider(
    "Larghezza testo etichette (caratteri per riga)",
    min_value=12,
    max_value=36,
    value=20,
    step=1,
    help="Riduci per andare a capo prima (come restringere una casella di testo).",
)

wrap_lines = st.sidebar.slider(
    "Numero massimo righe per etichetta",
    min_value=1,
    max_value=4,
    value=2,
    step=1,
    help="Se il testo eccede, viene aggiunta un’ellissi (…).",
)

inner_radius_ratio = st.sidebar.slider(
    "Foro centrale (donut)",
    min_value=0.35,
    max_value=0.80,
    value=0.62,
    step=0.01,
    help="Valori più alti = foro più grande.",
)

palette = st.sidebar.selectbox(
    "Palette colori",
    ["set3", "tableau10", "paired"],
    index=0,
)


# ----------------------------
# D3 Donut (SVG only, no title/subtitle inside the iframe)
# ----------------------------
def donut_svg_html(
    labels,
    values,
    palette_name,
    inner_ratio,
    label_font,
    show_percent_labels,
    max_chars_per_line,
    max_lines,
):
    total = int(sum(values)) if values else 0

    payload = {
        "labels": labels,
        "values": values,
        "palette": palette_name,
        "inner_ratio": float(inner_ratio),
        "label_font": int(label_font),
        "show_percent_labels": bool(show_percent_labels),
        "max_chars_per_line": int(max_chars_per_line),
        "max_lines": int(max_lines),
        "total": total,
    }
    data_json = json.dumps(payload, ensure_ascii=False)

    return f"""<!doctype html>
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
    #chart {{
      width: 100%;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .tooltip {{
      position: absolute;
      padding: 8px 10px;
      background: rgba(0,0,0,0.78);
      color: #fff;
      border-radius: 8px;
      font-size: 12px;
      pointer-events: none;
      line-height: 1.25;
      max-width: 420px;
    }}
    .label-text {{ fill: #111; }}
    .leader {{
      stroke: rgba(0,0,0,0.35);
      stroke-width: 1;
      fill: none;
    }}
  </style>
</head>
<body>
  <div id="chart"></div>

  <script>
    const payload = {data_json};

    const labels = payload.labels;
    const values = payload.values;
    const palette = payload.palette;
    const innerRatio = payload.inner_ratio;
    const labelFont = payload.label_font;
    const showPercentLabels = payload.show_percent_labels;
    const total = payload.total;

    const maxCharsPerLine = payload.max_chars_per_line;
    const maxLines = payload.max_lines;

    const containerNode = document.getElementById("chart");
    const width = Math.max(520, containerNode.clientWidth || 700);  // responsive to column width
    const height = 620; // enough space for top/bottom labels in 2-col layout

    const margin = {{ top: 20, right: 170, bottom: 40, left: 170 }};
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    const outerRadius = Math.min(w, h) * 0.48;
    const innerRadius = outerRadius * innerRatio;

    const palettes = {{
      set3: d3.schemeSet3,
      tableau10: d3.schemeTableau10,
      paired: d3.schemePaired
    }};
    const colors = palettes[palette] || d3.schemeSet3;
    const color = d3.scaleOrdinal().range(colors);

    const svg = d3.select(containerNode).append("svg")
      .attr("viewBox", [0, 0, width, height])
      .attr("preserveAspectRatio", "xMidYMid meet");

    // centred group (no title/subtitle inside iframe, so we can centre reliably)
    const g = svg.append("g")
      .attr("transform", "translate(" + (margin.left + w/2) + "," + (margin.top + h/2) + ")");

    const data = labels.map((l, i) => ({{ label: l, value: values[i] }}));

    const pie = d3.pie()
      .sort(null)
      .value(d => d.value);

    const arc = d3.arc()
      .innerRadius(innerRadius)
      .outerRadius(outerRadius);

    const arcOuter = d3.arc()
      .innerRadius(outerRadius * 1.08)
      .outerRadius(outerRadius * 1.08);

    // Tooltip ALWAYS shows value + percent
    const tooltip = d3.select("body")
      .append("div")
      .attr("class", "tooltip")
      .style("opacity", 0);

    g.selectAll("path.slice")
      .data(pie(data))
      .join("path")
      .attr("class", "slice")
      .attr("d", arc)
      .attr("fill", (d, i) => color(i))
      .attr("stroke", "#fff")
      .attr("stroke-width", 1)
      .on("mousemove", (event, d) => {{
        const pct = (total > 0) ? ((d.data.value / total) * 100) : 0;
        tooltip
          .style("opacity", 1)
          .html(
            "<b>" + d.data.label + "</b><br/>" +
            "Valore: " + d.data.value + "<br/>" +
            "Percentuale: " + pct.toFixed(1) + "%"
          )
          .style("left", (event.pageX + 12) + "px")
          .style("top", (event.pageY + 12) + "px");
      }})
      .on("mouseout", () => tooltip.style("opacity", 0));

    // Leader lines
    g.selectAll("polyline.leader")
      .data(pie(data))
      .join("polyline")
      .attr("class", "leader")
      .attr("points", d => {{
        const p1 = arc.centroid(d);
        const p2 = arcOuter.centroid(d);
        const p3 = arcOuter.centroid(d);
        const mid = (d.startAngle + d.endAngle) / 2;
        p3[0] = outerRadius * 1.25 * (mid < Math.PI ? 1 : -1);
        return [p1, p2, p3];
      }});

    // Wrap helper (PowerPoint-like)
    function wrapLabel(text) {{
    const words = (text || "").split(/\\s+/).filter(Boolean);
    const lines = [];
    let line = "";

    for (const w of words) {{
      const candidate = line ? (line + " " + w) : w;
      if (candidate.length <= maxCharsPerLine) {{
        line = candidate;
      }} else {{
        if (line) lines.push(line);
        line = w;
      }}
    }}
    if (line) lines.push(line);

    // No truncation: return all lines (PowerPoint-like wrap)
    return lines;
  }}

    // Labels as <tspan> lines (wrapped)
    const labelSel = g.selectAll("text.label-text")
      .data(pie(data))
      .join("text")
      .attr("class", "label-text")
      .style("font-size", labelFont + "px")
      .style("font-weight", 500)
      .style("text-anchor", d => {{
        const mid = (d.startAngle + d.endAngle) / 2;
        return mid < Math.PI ? "start" : "end";
      }})
      .attr("transform", d => {{
        const pos = arcOuter.centroid(d);
        const mid = (d.startAngle + d.endAngle) / 2;
        pos[0] = outerRadius * 1.28 * (mid < Math.PI ? 1 : -1);
        return "translate(" + pos + ")";
      }});

    labelSel.each(function(d) {{
      const pct = (total > 0) ? ((d.data.value / total) * 100) : 0;
      const base = showPercentLabels
        ? (d.data.label + " (" + pct.toFixed(1) + "%)")
        : d.data.label;

      const lines = wrapLabel(base);

      const textEl = d3.select(this);
      textEl.text(null);

      const lineHeightEm = 1.2;
      const startDy = -(lines.length - 1) * 0.55; // vertically centre multi-line label

      lines.forEach((line, i) => {{
        textEl.append("tspan")
          .attr("x", 0)
          .attr("dy", (i === 0 ? startDy : lineHeightEm) + "em")
          .text(line);
      }});
    }});
  </script>
</body>
</html>"""


# ----------------------------
# Prepare subsets (TN=1 and TN=2)
# ----------------------------
def prepare_subset(tn_value: int):
    sub = df[df["TN"] == tn_value].copy()

    # Keep only non-empty labels
    sub[label_col] = sub[label_col].fillna("").astype(str)
    sub = sub[sub[label_col].str.strip() != ""]

    # Aggregate (safe)
    sub = sub.groupby(label_col, as_index=False)["count"].sum()
    sub = sub.sort_values("count", ascending=False)

    labels = sub[label_col].tolist()
    values = sub["count"].astype(int).tolist()
    return labels, values


TITLE_TN1 = "Dalla ricerca scientifica alla vita quotidiana"
TITLE_TN2 = "Dalla società che invecchia alle politiche per la longevità sostenibile"

labels1, values1 = prepare_subset(1)
labels2, values2 = prepare_subset(2)

if not labels1 and not labels2:
    st.warning("Nessun record trovato per TN=1 o TN=2.")
    st.stop()


# ----------------------------
# Render charts side-by-side (titles OUTSIDE iframe)
# ----------------------------
left, right = st.columns(2, gap="large")

with left:
    st.subheader(TITLE_TN1)
    st.caption(f"Totale record: {sum(values1)}")
    if labels1:
        components.html(
            donut_svg_html(
                labels1,
                values1,
                palette,
                inner_radius_ratio,
                label_font_px,
                show_percent_on_labels,
                wrap_chars,
                wrap_lines,
            ),
            height=660,
            scrolling=False,
        )
    else:
        st.info("Nessun record per TN=1.")

with right:
    st.subheader(TITLE_TN2)
    st.caption(f"Totale record: {sum(values2)}")
    if labels2:
        components.html(
            donut_svg_html(
                labels2,
                values2,
                palette,
                inner_radius_ratio,
                label_font_px,
                show_percent_on_labels,
                wrap_chars,
                wrap_lines,
            ),
            height=660,
            scrolling=False,
        )
    else:
        st.info("Nessun record per TN=2.")


st.caption(
    """Per rendere più intuitiva la scoperta e l’esplorazione dei contenuti della piattaforma, è stato progettato un sistema di navigazione basato sulle Tracce Narrative.
Questo approccio consente non solo di esplorare ciascun Percorso (Spoke) in modo autonomo, ma anche di seguire itinerari tematici che attraversano trasversalmente le diverse aree del progetto.
Le Tracce Narrative costruiscono una vera e propria narrazione tematica, permettendo all’utente di collegare contenuti affini che, altrimenti, resterebbero frammentati all’interno delle singole sezioni. In questo modo, la navigazione diventa più coerente, guidata e orientata alla comprensione complessiva delle attività di ricerca, favorendo una visione integrata dell’impatto scientifico e sociale del progetto."""
)