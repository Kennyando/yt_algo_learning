import dash
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, callback, Input, Output

from utils.data_loader import load_data  # function from data loader python file
from utils.helpers import (
    METRIC_LABELS, combine_types, filter_period, previous_window, drop_partial_month,
    add_multiples, period_texts, pct_change, filter_group, type_checklist, period_radio,
    metric_dropdown, kpi_card,
)
from theme import (
    TYPE_COLORS, TYPE_ORDER, SURFACE, MUTED, SECONDARY,
    duration_axis_ticks, needs_log_duration, graph, finish, empty_fig, style_lines, fmt_duration,
    log_ticks, compact,
)

# register python file as a page and make it available at the path "/" which is the root of the website, as overview
dash.register_page(__name__, path="/", name="Overview")  # / is also reserved for what you want to load by default

all_dfs = load_data()

BREAKOUT_AT = 3  # an upload this many times its usual (median of the last 20) counts as a breakout

layout = html.Div([
    html.H3("Channel Overview"),

    # one filter row above everything it controls
    html.Div([
        filter_group("Content", type_checklist("overview_content_type_filter")),
        filter_group("Metric", metric_dropdown("overview_metrics_dropdown")),
        filter_group("Period", period_radio("overview_time_period_filter")),
    ], className="filter_bar"),

    html.Div(id="overview_kpis", className="kpi_row"),

    # grid layout for graphs (the grid itself lives in style.css)
    html.Div([
        graph("overview_monthly_total"),
        graph("overview_monthly_avg"),
        graph("overview_monthly_uploads"),
        graph("overview_avg_duration"),
        graph("overview_like_rate"),
        graph("overview_breakouts"),
    ], className="graph_grid"),

    html.Div(id="overview_insights", className="insights_card"),
])


def _insights(df, prev, metric):
    """A few plain-english takeaways computed from whatever is currently selected."""
    label = METRIC_LABELS[metric].lower()
    lines = []

    median_now = df[metric].median()
    best = df.loc[df[metric].idxmax()]
    ratio = best[metric] / median_now if median_now else np.nan
    text = f"Top upload: “{best['title']}” with {compact(best[metric])} {label}"
    if not np.isnan(ratio) and ratio >= 1.5:
        text += f", {ratio:.1f}× the median upload in this period"
    lines.append(text + ".")

    if prev is not None and len(prev) > 0:
        change = pct_change(median_now, prev[metric].median())
        if change is not None:
            verb = "up" if change > 0 else "down"
            lines.append(
                f"Median {label} per upload is {verb} {abs(change):.0f}% on the previous period "
                f"({compact(prev[metric].median())} → {compact(median_now)})."
            )

    weeks = max((df["upload_time"].max() - df["upload_time"].min()).days / 7, 1)
    cadence = f"{len(df):,} uploads in this window, about {len(df) / weeks:.1f} per week."
    by_day = df.assign(day=df["upload_time"].dt.day_name()).groupby("day")[metric].agg(["median", "count"])
    by_day = by_day[by_day["count"] >= 5]
    if len(by_day) >= 2:
        day = by_day["median"].idxmax()
        cadence += (f" {day} uploads do best, with a median of {compact(by_day.loc[day, 'median'])} "
                    f"{label} (from {int(by_day.loc[day, 'count'])} uploads).")
    lines.append(cadence)

    if df["content_type"].nunique() > 1:
        share = df.groupby("content_type")[metric].sum()
        share = share / share.sum() * 100
        uploads = df["content_type"].value_counts(normalize=True) * 100
        top = share.idxmax()
        lines.append(f"{top} bring in {share[top]:.0f}% of all {label} from {uploads[top]:.0f}% of uploads.")

    return lines


@callback(
    Output("overview_kpis", "children"),
    Output("overview_monthly_total", "figure"),
    Output("overview_monthly_avg", "figure"),
    Output("overview_monthly_uploads", "figure"),
    Output("overview_avg_duration", "figure"),
    Output("overview_like_rate", "figure"),
    Output("overview_breakouts", "figure"),
    Output("overview_insights", "children"),
    Input("overview_content_type_filter", "value"),
    Input("overview_metrics_dropdown", "value"),
    Input("overview_time_period_filter", "value"),
)
# follows order of the callback, first input in callback = first input in function that its decorating
def update_overview(selected_types, metric, time_period):
    label = METRIC_LABELS[metric]
    low = label.lower()
    titles = [
        f"Total {low} by upload month",
        f"Median {low} per upload",
        "Uploads per month",
        "Typical length of uploads",
        "Like rate (likes per 100 views)",
        f"Breakout uploads: {low} vs usual ({BREAKOUT_AT}×+ highlighted)",
    ]

    full = combine_types(all_dfs, selected_types)
    full = full.assign(like_rate=np.where(full["views"] > 0, full["likes"] / full["views"] * 100, np.nan))
    latest = all_dfs["all"]["upload_time"].max()

    df = filter_period(full, time_period, latest)
    if df.empty:
        nothing = [empty_fig(t) for t in titles]
        return [], *nothing, "Pick at least one content type and a period with uploads."
    prev = previous_window(full, time_period, latest)

    # ---------- KPI tiles ----------
    def rate(frame):
        return frame["likes"].sum() / frame["views"].sum() * 100 if len(frame) and frame["views"].sum() else np.nan

    has_prev = prev is not None and len(prev) > 0
    cur_text, prev_text = period_texts(time_period, latest, all_dfs["all"]["upload_time"].min())

    def tile(name, now_text, then_text, change, **kw):
        """One KPI card: this period's number, the earlier period's number and both date ranges."""
        return kpi_card(name, now_text, change if has_prev else None, period=cur_text,
                        compare_value=then_text if has_prev else None,
                        compare_period=prev_text if has_prev else None, **kw)

    kpis = [
        tile("Uploads", f"{len(df):,}", f"{len(prev):,}" if has_prev else None,
             pct_change(len(df), len(prev)) if has_prev else None, up_is_good=None),
        tile(f"Total {low}", compact(df[metric].sum()),
             compact(prev[metric].sum()) if has_prev else None,
             pct_change(df[metric].sum(), prev[metric].sum()) if has_prev else None),
        tile(f"Median {low} per upload", compact(df[metric].median()),
             compact(prev[metric].median()) if has_prev else None,
             pct_change(df[metric].median(), prev[metric].median()) if has_prev else None),
        tile("Like rate", f"{rate(df):.1f}%",
             f"{rate(prev):.1f}%" if has_prev and not np.isnan(rate(prev)) else None,
             (rate(df) - rate(prev)) if has_prev and not np.isnan(rate(prev)) else None, delta_kind="pts"),
    ]

    # ---------- monthly charts (the half-finished current month is hidden) ----------
    monthly = drop_partial_month(df)
    group = ["upload_month", "content_type"]
    common = dict(x="upload_month", color="content_type",
                  color_discrete_map=TYPE_COLORS, category_orders={"content_type": TYPE_ORDER})

    def month_hover(fig, template):
        fig.update_traces(hovertemplate=template + "<extra>%{fullData.name}</extra>")
        fig.update_layout(hovermode="x unified")
        fig.update_xaxes(tickformat="%b %Y", hoverformat="%b %Y", showspikes=True)
        return fig

    if monthly.empty:
        total_fig, median_fig, uploads_fig, duration_fig, rate_fig = (
            empty_fig(titles[i], "Not enough complete months in this window") for i in range(5))
    else:
        n_months = monthly["upload_month"].nunique()

        total = monthly.groupby(group)[metric].sum().reset_index()
        total_fig = month_hover(style_lines(px.line(total, y=metric, **common), n_months), "%{y:,.0f}")
        finish(total_fig, titles[0], yfmt="~s")

        med = monthly.groupby(group)[metric].median().reset_index()
        median_fig = month_hover(style_lines(px.line(med, y=metric, **common), n_months), "%{y:,.0f}")
        finish(median_fig, titles[1], yfmt="~s")

        uploads = monthly.groupby(group)["video_id"].count().reset_index(name="uploads")
        uploads_fig = px.bar(uploads, y="uploads", barmode="stack", **common)
        uploads_fig.update_traces(marker_line=dict(width=2, color=SURFACE))  # 2px gap between stacked segments
        month_hover(uploads_fig, "%{y:,.0f}")
        uploads_fig.update_layout(hovermode="x unified", bargap=0.5)
        finish(uploads_fig, titles[2], yfmt=",d")

        # length: shorts (~30s) next to streams (~4h) need a log axis, anything else reads better linear
        log_len = needs_log_duration(monthly["content_type"])
        dur = monthly.groupby(group)["duration_minutes"].median().reset_index()
        dur["duration_display"] = dur["duration_minutes"].map(fmt_duration)
        duration_fig = style_lines(px.line(dur, y="duration_minutes", custom_data=["duration_display"], **common), n_months)
        month_hover(duration_fig, "%{customdata[0]}")
        ticks = duration_axis_ticks(dur["duration_minutes"], log_len)
        duration_fig.update_yaxes(type="log" if log_len else "linear",
                                  tickvals=[v for v, _ in ticks], ticktext=[t for _, t in ticks])
        if not log_len:
            duration_fig.update_yaxes(rangemode="tozero")
        finish(duration_fig, titles[3] + (" (median, log scale)" if log_len else " (median)"))

        like = monthly.dropna(subset=["like_rate"]).groupby(group)["like_rate"].median().reset_index()
        rate_fig = month_hover(style_lines(px.line(like, y="like_rate", **common), n_months), "%{y:.2f}%")
        rate_fig.update_yaxes(ticksuffix="%", tickformat=".1f", rangemode="tozero")
        finish(rate_fig, titles[4])

    # ---------- breakouts: how far above "normal" was each upload? ----------
    # baseline = median of the previous 20 uploads of the same type, computed on the FULL history
    bk = filter_period(add_multiples(full, metric), time_period, latest)
    if bk.empty:
        breakout_fig = empty_fig(titles[5], "Not enough upload history to set a baseline")
    else:
        bk = bk.assign(when=bk["upload_time"].dt.tz_localize(None))
        hover = ("<b>%{customdata[0]}</b><br>%{customdata[1]:,.0f} " + low
                 + "<br>%{y:.1f}× usual<br>%{x|%d %b %Y}<extra>%{fullData.name}</extra>")
        breakout_fig = go.Figure()
        # everything that is within 3x of usual is background; only real breakouts get a colour
        normal = bk[bk["multiple"] < BREAKOUT_AT]
        breakout_fig.add_trace(go.Scatter(
            x=normal["when"], y=normal["multiple"], mode="markers", name=f"Within {BREAKOUT_AT}× usual",
            customdata=np.stack([normal["title"], normal[metric]], axis=-1),
            marker=dict(size=6, color="#4b5262", opacity=0.55, line=dict(width=1, color=SURFACE)),
            hovertemplate=hover,
        ))
        for ctype in TYPE_ORDER:
            hit = bk[(bk["content_type"] == ctype) & (bk["multiple"] >= BREAKOUT_AT)]
            if hit.empty:
                continue
            breakout_fig.add_trace(go.Scatter(
                x=hit["when"], y=hit["multiple"], mode="markers", name=ctype,
                customdata=np.stack([hit["title"], hit[metric]], axis=-1),
                marker=dict(size=9, color=TYPE_COLORS[ctype], opacity=0.9, line=dict(width=2, color=SURFACE)),
                hovertemplate=hover,
            ))
        vals, text = log_ticks(bk["multiple"].min(), bk["multiple"].max())
        breakout_fig.update_yaxes(type="log", tickvals=vals, ticktext=text)
        breakout_fig.add_hline(y=1, line=dict(color=MUTED, width=1))
        breakout_fig.add_hline(y=BREAKOUT_AT, line=dict(color=MUTED, width=1, dash="dot"))
        # annotations on a log axis take log10 values (add_hline's own label would be placed at 10^3)
        breakout_fig.add_annotation(
            xref="paper", x=1, xanchor="right", y=np.log10(BREAKOUT_AT), yanchor="bottom", text=f"{BREAKOUT_AT}× usual",
            showarrow=False, font=dict(size=11, color=MUTED),
        )
        # label only the single biggest outlier, the tooltip carries the rest
        top = bk.loc[bk["multiple"].idxmax()]
        span = (bk["when"].max() - bk["when"].min()).total_seconds() or 1
        late = (top["when"] - bk["when"].min()).total_seconds() / span > 0.5
        short = top["title"] if len(top["title"]) <= 34 else top["title"][:33] + "…"
        breakout_fig.add_annotation(
            x=top["when"], y=np.log10(top["multiple"]), text=f"{short} · {top['multiple']:.0f}×",
            showarrow=True, arrowcolor=MUTED, arrowwidth=1, arrowhead=0,
            ax=-14 if late else 14, ay=-22, xanchor="right" if late else "left",
            font=dict(size=11, color=SECONDARY),
        )
        finish(breakout_fig, titles[5])

    return kpis, total_fig, median_fig, uploads_fig, duration_fig, rate_fig, breakout_fig, [
        html.H4("Quick read"),
        html.Ul([html.Li(line) for line in _insights(df, prev, metric)]),
        html.P("Recent uploads are still collecting views, and the current partial month is left out "
               "of the monthly charts.", className="footnote"),
    ]
