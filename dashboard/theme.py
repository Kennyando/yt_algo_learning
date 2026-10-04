"""
Shared look for every chart on the dashboard.

Import this module once (each page does `from theme import ...`) and every
Plotly figure picks up the dark template automatically, so the pages only
have to worry about the data and not about colours / fonts / gridlines.

Colour rules used here:
  * one fixed colour per content type (Videos / Shorts / Streams) so a
    filter never repaints the survivors
  * the three colours were checked for colour-blind separation on the
    dashboard surface (#171a21)
  * single-series charts use ACCENT, heatmaps use one blue ramp
"""
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from dash import dcc

# ---------- colours (mirror the tokens in assets/style.css) ----------
SURFACE = "#171a21"
SURFACE_RAISED = "#1e222b"
BORDER = "#2a2f3a"
GRID = "#242935"
TEXT = "#e8eaed"
SECONDARY = "#c3c7d0"
MUTED = "#9aa2b1"

ACCENT = "#3987e5"
TYPE_COLORS = {"Videos": "#3987e5", "Shorts": "#d95926", "Streams": "#199e70"}
TYPE_ORDER = ["Videos", "Shorts", "Streams"]

# low -> high, one hue, starts near the card surface so "nothing" recedes
SEQ_SCALE = [[0.0, "#1c2535"], [0.35, "#184f95"], [0.7, "#3987e5"], [1.0, "#9ec5f4"]]

# heatmap cells carry white numbers, so the ramp stops at a blue that white text still reads on
HEAT_SCALE = [[0.0, "#1c2535"], [0.5, "#184f95"], [1.0, "#3987e5"]]

FONT = '"Segoe UI", Roboto, Helvetica, Arial, sans-serif'

GRAPH_CONFIG = {"displayModeBar": False}  # the toolbar covers the legend


def _build_template():
    axis = dict(
        gridcolor=GRID,
        gridwidth=1,
        linecolor=GRID,
        zeroline=False,
        ticks="",
        tickfont=dict(size=11, color=MUTED),
        title=dict(font=dict(size=12, color=MUTED), standoff=10),
        automargin=True,
    )
    template = go.layout.Template()
    template.layout = dict(
        font=dict(family=FONT, size=12, color=MUTED),
        paper_bgcolor="rgba(0,0,0,0)",  # the card (.dash-graph) supplies the surface
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[TYPE_COLORS[t] for t in TYPE_ORDER],
        title=dict(
            x=0, xanchor="left", y=0.965, yanchor="top",
            font=dict(size=14, color=TEXT), pad=dict(l=4),
        ),
        margin=dict(l=52, r=20, t=78, b=40),
        legend=dict(
            orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom",
            bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=SECONDARY),
            title=dict(text=""), itemsizing="constant",
        ),
        xaxis=axis,
        yaxis=axis,
        hoverlabel=dict(
            bgcolor=SURFACE_RAISED, bordercolor=BORDER,
            font=dict(family=FONT, size=12, color=TEXT),
        ),
        bargap=0.4,
        barcornerradius=4,
    )
    return template


pio.templates["yt_dark"] = _build_template()
pio.templates.default = "yt_dark"


# ---------- small helpers ----------
def graph(graph_id, wide=False, height=360):
    """A dcc.Graph with the dashboard's size / config. wide=True spans both grid columns."""
    return dcc.Graph(
        id=graph_id,
        config=GRAPH_CONFIG,
        className="span_2" if wide else "",
        style={"height": f"{height}px"},
    )


def finish(fig, title, xtitle="", ytitle="", legend=None, yfmt=None):
    """
    Last-step formatting every figure shares.
    legend=None -> only show one when there is more than one series (a single series is named by the title)
    """
    if legend is None:
        legend = sum(1 for t in fig.data if t.showlegend is not False) > 1
    fig.update_layout(title_text=title, showlegend=legend, legend_title_text="",
                      margin=dict(t=78 if legend else 58))
    fig.update_xaxes(title_text=xtitle)
    fig.update_yaxes(title_text=ytitle)
    if yfmt:
        fig.update_yaxes(tickformat=yfmt)
    return fig


def empty_fig(title, message="No uploads match this selection"):
    fig = go.Figure()
    fig.add_annotation(
        text=message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5,
        font=dict(size=14, color=MUTED),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(title_text=title, showlegend=False)
    return fig


def style_lines(fig, n_points):
    """2px lines; end markers only when there are few enough points to read."""
    fig.update_traces(line=dict(width=2))
    if n_points <= 36:
        fig.update_traces(
            mode="lines+markers",
            marker=dict(size=7, line=dict(width=2, color=SURFACE)),
        )
    else:
        fig.update_traces(mode="lines")
    return fig


# ---------- duration axis (minutes, log scale so 30s shorts and 4h streams both fit) ----------
_DURATION_CANDIDATES = [
    (0.25, "15s"), (0.5, "30s"), (1, "1m"), (2, "2m"), (5, "5m"), (10, "10m"), (15, "15m"),
    (20, "20m"), (30, "30m"), (45, "45m"), (60, "1h"), (90, "90m"), (120, "2h"), (180, "3h"),
    (240, "4h"), (360, "6h"), (480, "8h"),
]


def duration_ticks(lo, hi):
    """Readable (minutes, label) ticks that sit inside the data range, at least three of them."""
    lo, hi = max(lo, 0.05), max(hi, lo)
    def thin(candidates):
        # log axis: keep ticks at least ~2x apart so labels never touch
        kept = []
        for v, t in candidates:
            if not kept or v >= kept[-1][0] * 1.9:
                kept.append((v, t))
        return kept

    ticks = thin([(v, t) for v, t in _DURATION_CANDIDATES if lo / 1.3 <= v <= hi * 1.3])
    if len(ticks) < 3:  # widen until we have something to read
        ticks = thin([(v, t) for v, t in _DURATION_CANDIDATES if lo / 3 <= v <= hi * 3])
    return ticks


def fmt_duration(minutes):
    seconds = minutes * 60
    if seconds < 90:
        return f"{seconds:.0f}s"
    if minutes < 60:
        return f"{minutes:.0f}m"
    hrs, mins = int(minutes // 60), int(round(minutes % 60))
    if mins == 60:
        hrs, mins = hrs + 1, 0
    return f"{hrs}h {mins}m" if mins else f"{hrs}h"


def log_ticks(lo, hi, base=2, suffix="×"):
    """Powers of `base` that cover [lo, hi] -> (tickvals, ticktext) for a log axis."""
    if np.log2(max(hi, 1e-9) / max(lo, 1e-9)) > 7:  # wide range: step by 4x instead of 2x
        base = base ** 2
    lo_p = int(np.floor(np.log(max(lo, 1e-9)) / np.log(base)))
    hi_p = int(np.ceil(np.log(max(hi, 1e-9)) / np.log(base)))
    vals = [base ** p for p in range(lo_p, hi_p + 1)]
    text = [(f"{v:g}{suffix}") for v in vals]
    return vals, text


def compact(n):
    """1234 -> 1.2K, 3_400_000 -> 3.4M. Used in tooltips, cards and KPI tiles."""
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "–"
    n = float(n)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= limit:
            value = n / limit
            text = f"{value:.1f}" if abs(value) < 100 else f"{value:.0f}"
            return text.removesuffix(".0") + suffix
    return f"{n:.0f}"
