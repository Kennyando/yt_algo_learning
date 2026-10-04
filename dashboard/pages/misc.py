import dash
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, callback, Input, Output

from utils.data_loader import load_data
from utils.helpers import combine_types, filter_period, filter_group, type_checklist, period_radio
from theme import (
    TYPE_COLORS, TYPE_ORDER, SURFACE, MUTED, HEAT_SCALE, duration_axis_ticks, needs_log_duration,
    graph, finish, empty_fig, compact, fmt_duration,
)

# register page
dash.register_page(__name__, path="/misc", name="Miscellaneous Stats")

all_dfs = load_data()

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOUR_BLOCKS = [f"{h:02d}:00" for h in range(0, 24, 3)]  # 3-hour bins, UTC
GAP_CAP = 21  # days; anything longer is lumped into the last bar

layout = html.Div([
    html.H3("Miscellaneous statistics"),

    html.Div([
        filter_group("Content", type_checklist("misc_content_type_filter")),
        filter_group("Period", period_radio("misc_time_period_filter")),
    ], className="filter_bar"),

    html.Div([
        graph("misc_hour_day_heatmap"),
        graph("misc_weekday_views"),
        graph("misc_duration_dist"),
        graph("misc_views_dist"),
        graph("misc_views_likes_scatter"),
        graph("misc_views_duration_scatter"),
        graph("misc_upload_gap_hist", wide=True),
    ], className="graph_grid"),
])

TITLES = [
    "When uploads go out (UTC)",
    "Median views by upload day",
    "How long uploads are",
    "How many views uploads get",
    "Views vs likes",
    "Views vs length",
    "Days between uploads",
]


def _log_axis_ticks(fig, axis, tick_pairs):
    """Put readable labels on a log10 axis (values given in real units)."""
    vals = [np.log10(v) for v, _ in tick_pairs]
    text = [t for _, t in tick_pairs]
    getattr(fig, f"update_{axis}axes")(tickvals=vals, ticktext=text)


def _trend_lines(fig, df, x, y):
    """Straight best-fit line per content type, drawn on log-log data."""
    for ctype, g in df.groupby("content_type"):
        if len(g) < 10:
            continue
        lx, ly = np.log10(g[x]), np.log10(g[y])
        slope, intercept = np.polyfit(lx, ly, 1)
        xs = np.linspace(lx.min(), lx.max(), 20)
        fig.add_trace(go.Scatter(
            x=xs, y=slope * xs + intercept, mode="lines", showlegend=False, hoverinfo="skip",
            line=dict(color=TYPE_COLORS[ctype], width=2),
        ))


@callback(
    Output("misc_hour_day_heatmap", "figure"),
    Output("misc_weekday_views", "figure"),
    Output("misc_duration_dist", "figure"),
    Output("misc_views_dist", "figure"),
    Output("misc_views_likes_scatter", "figure"),
    Output("misc_views_duration_scatter", "figure"),
    Output("misc_upload_gap_hist", "figure"),
    Input("misc_content_type_filter", "value"),
    Input("misc_time_period_filter", "value"),
)
def update_misc_graphs(selected_types, time_period):
    full = combine_types(all_dfs, selected_types)
    latest = all_dfs["all"]["upload_time"].max()
    df = filter_period(full, time_period, latest)
    if df.empty:
        return tuple(empty_fig(t) for t in TITLES)

    df = df.assign(
        day_of_week=df["upload_time"].dt.day_name(),
        hour_block=(df["upload_hour"] // 3 * 3).map(lambda h: f"{h:02d}:00"),
    )
    common = dict(color="content_type", color_discrete_map=TYPE_COLORS,
                  category_orders={"content_type": TYPE_ORDER})

    # ---------- upload timing heatmap: how many uploads per weekday x 3-hour block ----------
    grid = (df.groupby(["day_of_week", "hour_block"]).size()
              .unstack(fill_value=0).reindex(index=DAYS, columns=HOUR_BLOCKS, fill_value=0))
    heatmap_fig = go.Figure(go.Heatmap(
        z=grid.values, x=HOUR_BLOCKS, y=DAYS, colorscale=HEAT_SCALE, zmin=0,
        xgap=2, ygap=2, showscale=False,
        text=[[str(v) if v else "" for v in row] for row in grid.values],  # count in the cell, blanks for zero
        texttemplate="%{text}", textfont=dict(size=11, color="#e8eaed"),
        hovertemplate="%{y}, from %{x} UTC<br>%{z} uploads<extra></extra>",
    ))
    heatmap_fig.update_yaxes(autorange="reversed")
    finish(heatmap_fig, TITLES[0], xtitle="Start of 3-hour block (UTC)", legend=False)

    # ---------- median views by upload weekday ----------
    wk = df.groupby(["day_of_week", "content_type"])["views"].median().reset_index()
    weekday_fig = px.bar(wk, x="day_of_week", y="views", barmode="group", **common)
    weekday_fig.update_traces(marker_line=dict(width=2, color=SURFACE),
                              hovertemplate="%{x}: %{y:,.0f} median views<extra>%{fullData.name}</extra>")
    weekday_fig.update_xaxes(categoryorder="array", categoryarray=DAYS,
                             ticktext=[d[:3] for d in DAYS], tickvals=DAYS)
    weekday_fig.update_layout(bargap=0.3, bargroupgap=0.08)
    finish(weekday_fig, TITLES[1], yfmt="~s")

    # ---------- length distribution ----------
    # linear minutes normally; log only when shorts share the chart with longer content
    log_len = needs_log_duration(df["content_type"])
    d = df[df["duration_minutes"] > 0]
    ticks = duration_axis_ticks(d["duration_minutes"], log_len)
    if log_len:
        d = d.assign(length=np.log10(d["duration_minutes"]))
        tick_pairs = [(np.log10(v), t) for v, t in ticks]
    else:
        d = d.assign(length=d["duration_minutes"])
        tick_pairs = ticks
    duration_fig = px.histogram(d, x="length", nbins=30, barmode="stack", **common)
    duration_fig.update_traces(marker_line=dict(width=1, color=SURFACE),
                               hovertemplate="%{y} uploads<extra>%{fullData.name}</extra>")
    duration_fig.update_xaxes(tickvals=[v for v, _ in tick_pairs], ticktext=[t for _, t in tick_pairs])
    duration_fig.update_layout(bargap=0.15)
    finish(duration_fig, TITLES[2], ytitle="Uploads")

    # ---------- views distribution (views are very skewed, so log10 again) ----------
    v = df[df["views"] > 0].assign(log_views=lambda x: np.log10(x["views"]))
    views_fig = px.histogram(v, x="log_views", nbins=40, barmode="stack", **common)
    views_fig.update_traces(marker_line=dict(width=1, color=SURFACE),
                            hovertemplate="%{y} uploads<extra>%{fullData.name}</extra>")
    lo, hi = int(np.floor(v["log_views"].min())), int(np.ceil(v["log_views"].max()))
    _log_axis_ticks(views_fig, "x", [(10 ** p, compact(10 ** p)) for p in range(max(lo, 1), hi + 1)])
    views_fig.update_layout(bargap=0.15)
    finish(views_fig, TITLES[3], ytitle="Uploads")

    # ---------- views vs likes (log-log, one fit line per type) ----------
    vl = df[(df["views"] > 0) & (df["likes"] > 0)]
    if vl.empty:
        likes_fig = empty_fig(TITLES[4])
    else:
        likes_fig = go.Figure()
        for ctype in TYPE_ORDER:
            g = vl[vl["content_type"] == ctype]
            if g.empty:
                continue
            likes_fig.add_trace(go.Scatter(
                x=np.log10(g["views"]), y=np.log10(g["likes"]), mode="markers", name=ctype,
                customdata=np.stack([g["title"], g["views"], g["likes"]], axis=-1),
                marker=dict(size=6, opacity=0.55, color=TYPE_COLORS[ctype], line=dict(width=1, color=SURFACE)),
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,.0f} views · %{customdata[2]:,.0f} likes<extra>%{fullData.name}</extra>",
            ))
        _trend_lines(likes_fig, vl, "views", "likes")
        lo, hi = int(np.floor(np.log10(vl["views"].min()))), int(np.ceil(np.log10(vl["views"].max())))
        _log_axis_ticks(likes_fig, "x", [(10 ** p, compact(10 ** p)) for p in range(max(lo, 1), hi + 1)])
        lo, hi = int(np.floor(np.log10(vl["likes"].min()))), int(np.ceil(np.log10(vl["likes"].max())))
        _log_axis_ticks(likes_fig, "y", [(10 ** p, compact(10 ** p)) for p in range(max(lo, 0), hi + 1)])
        finish(likes_fig, TITLES[4], xtitle="Views", ytitle="Likes")

    # ---------- views vs length ----------
    vd = df[(df["views"] > 0) & (df["duration_minutes"] > 0)]
    if vd.empty:
        length_fig = empty_fig(TITLES[5])
    else:
        ticks = duration_axis_ticks(vd["duration_minutes"], log_len)
        to_x = np.log10 if log_len else (lambda m: m)
        length_fig = go.Figure()
        for ctype in TYPE_ORDER:
            g = vd[vd["content_type"] == ctype]
            if g.empty:
                continue
            length_fig.add_trace(go.Scatter(
                x=to_x(g["duration_minutes"]), y=np.log10(g["views"]), mode="markers", name=ctype,
                customdata=np.stack([g["title"], g["duration_minutes"].map(fmt_duration), g["views"]], axis=-1),
                marker=dict(size=6, opacity=0.55, color=TYPE_COLORS[ctype], line=dict(width=1, color=SURFACE)),
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]:,.0f} views<extra>%{fullData.name}</extra>",
            ))
        length_fig.update_xaxes(tickvals=[to_x(v) for v, _ in ticks], ticktext=[t for _, t in ticks])
        lo, hi = int(np.floor(np.log10(vd["views"].min()))), int(np.ceil(np.log10(vd["views"].max())))
        _log_axis_ticks(length_fig, "y", [(10 ** p, compact(10 ** p)) for p in range(max(lo, 1), hi + 1)])
        finish(length_fig, TITLES[5], xtitle="Length", ytitle="Views")

    # ---------- gap between uploads of the same type ----------
    gaps = []
    for ctype, g in df.sort_values("upload_time").groupby("content_type"):
        gap = g["upload_time"].diff().dt.total_seconds() / 86400
        gaps.append(pd.DataFrame({"content_type": ctype, "days": gap.dropna().clip(upper=GAP_CAP)}))
    gaps = pd.concat(gaps) if gaps else pd.DataFrame(columns=["content_type", "days"])
    if gaps.empty:
        gap_fig = empty_fig(TITLES[6])
    else:
        gap_fig = px.histogram(gaps, x="days", barmode="stack", **common)
        gap_fig.update_traces(xbins=dict(start=0, end=GAP_CAP, size=1), marker_line=dict(width=1, color=SURFACE),
                              hovertemplate="%{x} days apart: %{y} times<extra>%{fullData.name}</extra>")
        gap_fig.update_xaxes(range=[0, GAP_CAP], dtick=3)
        gap_fig.update_layout(bargap=0.15)
        finish(gap_fig, f"{TITLES[6]} (same content type, {GAP_CAP}+ days grouped)", xtitle="Days", ytitle="Times")

    return heatmap_fig, weekday_fig, duration_fig, views_fig, likes_fig, length_fig, gap_fig
