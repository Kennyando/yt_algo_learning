import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output

from utils.data_loader import load_data, data_as_of
from utils.helpers import (
    METRIC_LABELS, TYPE_OPTIONS, pct_change, filter_group, metric_dropdown, kpi_card,
)
from theme import (
    YEAR_A_COLOR, YEAR_B_COLOR, SURFACE,
    graph, finish, empty_fig, compact, rgba, nice_log_ticks,
)

# year vs year: both years are laid over the same Jan-Dec axis so months line up
dash.register_page(__name__, path="/compare", name="Compare Years")

all_dfs = load_data()

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
YEARS = sorted((int(y) for y in all_dfs["all"]["upload_time"].dt.year.unique()), reverse=True)
YEAR_OPTIONS = [{"label": str(y), "value": y} for y in YEARS]


def _in_progress_year():
    """
    The year the data was pulled in (if it isn't finished) and how many of its months are complete.
    Used to stop a half-finished year being compared against a full one.
    """
    asof = data_as_of()
    complete = asof.month if asof.day >= asof.days_in_month else asof.month - 1
    return (asof.year, complete) if complete < 12 else (None, 12)


PARTIAL_YEAR, COMPLETE_MONTHS = _in_progress_year()

layout = html.Div([
    html.H3("Compare Years"),

    html.Div([
        filter_group("Content", dcc.RadioItems(
            id="compare_content_type", options=TYPE_OPTIONS, value="videos",
            inline=True, className="pill_group")),
        filter_group("Metric", metric_dropdown("compare_metric")),
        filter_group("Year A", dcc.Dropdown(
            id="compare_year_a", options=YEAR_OPTIONS, value=YEARS[min(1, len(YEARS) - 1)], clearable=False)),
        filter_group("Year B", dcc.Dropdown(
            id="compare_year_b", options=YEAR_OPTIONS, value=YEARS[0], clearable=False)),
        filter_group("Months", dcc.Checklist(
            id="compare_match", options=[{"label": "Same months only", "value": "match"}],
            value=["match"], inline=True, className="pill_group")),
    ], className="filter_bar"),

    html.Div(id="compare_kpis", className="kpi_row"),

    html.Div([
        graph("compare_total"),
        graph("compare_median"),
        graph("compare_uploads"),
        graph("compare_like_rate"),
        graph("compare_cumulative"),
        graph("compare_spread"),
    ], className="graph_grid"),

    html.Div(id="compare_insights", className="insights_card"),
])


def _month_cap(year, other_year, match):
    """Last month of `year` that should be shown (12, or fewer for a year still in progress)."""
    cap = COMPLETE_MONTHS if year == PARTIAL_YEAR else 12
    if match and other_year == PARTIAL_YEAR:
        cap = min(cap, COMPLETE_MONTHS)  # trim the finished year to the same months
    return cap


def _monthly(df, cap, how):
    """One value per month 1..cap. Sums/counts give 0 for quiet months, medians give a gap."""
    g = df.groupby("month")
    if how == "count":
        s = g.size()
    elif how == "sum":
        s = g["value"].sum()
    else:
        s = g["value"].median()
    s = s.reindex(range(1, cap + 1))
    return s.fillna(0) if how in ("count", "sum") else s


def _line_fig(title, series, colors, hover, yfmt=None, ytitle=""):
    fig = go.Figure()
    for label, s in series.items():
        fig.add_trace(go.Scatter(
            x=[MONTHS[m - 1] for m in s.index], y=s.values, name=label, mode="lines+markers",
            line=dict(color=colors[label], width=2),
            marker=dict(size=7, color=colors[label], line=dict(width=2, color=SURFACE)),
            hovertemplate=hover + "<extra>%{fullData.name}</extra>", connectgaps=False,
        ))
    shown = max((len(s) for s in series.values()), default=12)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(categoryorder="array", categoryarray=MONTHS[:shown], showspikes=True)
    return finish(fig, title, ytitle=ytitle, yfmt=yfmt)


@callback(
    Output("compare_kpis", "children"),
    Output("compare_total", "figure"),
    Output("compare_median", "figure"),
    Output("compare_uploads", "figure"),
    Output("compare_like_rate", "figure"),
    Output("compare_cumulative", "figure"),
    Output("compare_spread", "figure"),
    Output("compare_insights", "children"),
    Input("compare_content_type", "value"),
    Input("compare_metric", "value"),
    Input("compare_year_a", "value"),
    Input("compare_year_b", "value"),
    Input("compare_match", "value"),
)
def update_compare(content_type, metric, year_a, year_b, match_values):
    label = METRIC_LABELS[metric]
    low = label.lower()
    titles = [
        f"Total {low} by month",
        f"Median {low} per upload by month",
        "Uploads per month",
        "Like rate (likes per 100 views)",
        f"Running total of {low} through the year",
        f"How {low} per upload are spread",
    ]
    if year_a == year_b:
        return [], *[empty_fig(t, "Pick two different years") for t in titles], "Pick two different years to compare."

    match = bool(match_values)
    base = all_dfs[content_type]
    base = base.assign(
        year=base["upload_time"].dt.year, month=base["upload_time"].dt.month, value=base[metric],
        like_rate=np.where(base["views"] > 0, base["likes"] / base["views"] * 100, np.nan),
    )
    cap_a, cap_b = _month_cap(year_a, year_b, match), _month_cap(year_b, year_a, match)
    # (label, colour, rows) per year; the label is the year itself so legends read "2020" / "2025"
    picks = [
        (str(year_a), YEAR_A_COLOR, base[(base["year"] == year_a) & (base["month"] <= cap_a)], cap_a),
        (str(year_b), YEAR_B_COLOR, base[(base["year"] == year_b) & (base["month"] <= cap_b)], cap_b),
    ]
    colors = {name: color for name, color, _, _ in picks}
    if all(d.empty for _, _, d, _ in picks):
        return [], *[empty_fig(t) for t in titles], "No uploads of this type in either year."

    # ---------- KPI tiles: year B's numbers, change measured against year A ----------
    (name_a, _, a, _), (name_b, _, b, _) = picks

    def rate(frame):
        return frame["likes"].sum() / frame["views"].sum() * 100 if len(frame) and frame["views"].sum() else np.nan

    def change(fn):
        return pct_change(fn(b), fn(a)) if len(a) and len(b) else None

    vs = f"{name_a}"
    kpis = [
        kpi_card(f"Uploads in {name_b}", f"{len(b):,}", change(len), up_is_good=None, compare_phrase=vs),
        kpi_card(f"Total {low} in {name_b}", compact(b["value"].sum()),
                 change(lambda d: d["value"].sum()), compare_phrase=vs),
        kpi_card(f"Median {low} per upload in {name_b}", compact(b["value"].median()),
                 change(lambda d: d["value"].median()), compare_phrase=vs),
        kpi_card(f"Like rate in {name_b}", f"{rate(b):.1f}%" if len(b) else "–",
                 (rate(b) - rate(a)) if len(a) and len(b) and not np.isnan(rate(a)) else None,
                 delta_kind="pts", compare_phrase=vs),
    ]

    # ---------- monthly charts ----------
    totals = {n: _monthly(d, cap, "sum") for n, _, d, cap in picks}
    medians = {n: _monthly(d, cap, "median") for n, _, d, cap in picks}
    counts = {n: _monthly(d.assign(value=1), cap, "count") for n, _, d, cap in picks}
    rates = {n: _monthly(d.dropna(subset=["like_rate"]).assign(value=lambda x: x["like_rate"]), cap, "median")
             for n, _, d, cap in picks}

    total_fig = _line_fig(titles[0], totals, colors, "%{y:,.0f}", yfmt="~s")
    median_fig = _line_fig(titles[1], medians, colors, "%{y:,.0f}", yfmt="~s")
    rate_fig = _line_fig(titles[3], rates, colors, "%{y:.2f}%")
    rate_fig.update_yaxes(ticksuffix="%", tickformat=".1f", rangemode="tozero")

    uploads_fig = go.Figure()
    for n, s in counts.items():
        uploads_fig.add_trace(go.Bar(
            x=[MONTHS[m - 1] for m in s.index], y=s.values, name=n, marker_color=colors[n],
            marker_line=dict(width=2, color=SURFACE),
            hovertemplate="%{y:,.0f} uploads<extra>%{fullData.name}</extra>",
        ))
    uploads_fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08, hovermode="x unified")
    uploads_fig.update_xaxes(categoryorder="array", categoryarray=MONTHS[:max(len(s) for s in counts.values())])
    finish(uploads_fig, titles[2], yfmt=",d")

    cumulative = {n: s.cumsum() for n, s in totals.items()}
    cum_fig = _line_fig(titles[4], cumulative, colors, "%{y:,.0f}", yfmt="~s")

    # ---------- spread: box plot of per-upload values, log scale because a few uploads dwarf the rest ----------
    spread_fig = go.Figure()
    positives = [d[d["value"] > 0] for _, _, d, _ in picks]
    for (n, color, _, _), d in zip(picks, positives):
        if d.empty:
            continue
        spread_fig.add_trace(go.Box(
            y=d["value"], name=n, boxpoints="outliers", marker=dict(color=color, size=4, opacity=0.6),
            line=dict(color=color, width=1.5), fillcolor=rgba(color, 0.25),
            hovertemplate="%{y:,.0f}<extra>%{fullData.name}</extra>",
        ))
    all_pos = pd.concat(positives)
    if not all_pos.empty:
        vals = nice_log_ticks(all_pos["value"].min(), all_pos["value"].max())
        spread_fig.update_yaxes(type="log", tickvals=vals, ticktext=[compact(v) for v in vals])
    finish(spread_fig, titles[5] + " (log scale)", legend=False)

    # ---------- written read ----------
    def top_upload(frame, name):
        row = frame.loc[frame["value"].idxmax()]
        return f"Top upload in {name}: “{row['title']}” with {compact(row['value'])} {low}."

    def best_month(series):
        return MONTHS[int(series.idxmax()) - 1] if series.notna().any() and series.max() > 0 else None

    lines = []
    up = pct_change(len(b), len(a)) if len(a) else None
    lines.append(f"{name_b} has {len(b):,} uploads against {len(a):,} in {name_a}"
                 + (f" ({'+' if up > 0 else '−'}{abs(up):.0f}%)." if up is not None else "."))
    if len(a) and len(b):
        lines.append(f"Median {low} per upload went from {compact(a['value'].median())} in {name_a} "
                     f"to {compact(b['value'].median())} in {name_b}.")
    for n, _, d, _ in picks:
        if not d.empty:
            lines.append(top_upload(d, n))
    bm = {n: best_month(s) for n, s in totals.items()}
    if all(bm.values()):
        lines.append(f"Best month for total {low}: {bm[name_a]} in {name_a}, {bm[name_b]} in {name_b}.")

    notes = []
    if PARTIAL_YEAR in (year_a, year_b):
        last = MONTHS[COMPLETE_MONTHS - 1] if COMPLETE_MONTHS else "the start"
        notes.append(f"{PARTIAL_YEAR} only has complete data through {last}"
                     + (", so both years are limited to the same months." if match
                        else f"; {PARTIAL_YEAR} is shown as it stands and will look smaller than a full year."))
    notes.append("Months with no uploads show as gaps in the median and like-rate lines.")

    return kpis, total_fig, median_fig, uploads_fig, rate_fig, cum_fig, spread_fig, [
        html.H4(f"{name_a} vs {name_b}"),
        html.Ul([html.Li(line) for line in lines]),
        html.P(" ".join(notes), className="footnote"),
    ]
