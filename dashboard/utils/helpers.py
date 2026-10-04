"""Data helpers shared by every page: content-type merging, time windows, filter widgets."""
import numpy as np
import pandas as pd
from dash import dcc, html

from utils.data_loader import data_as_of

TYPE_LABELS = {"videos": "Videos", "shorts": "Shorts", "vods": "Streams"}
METRIC_LABELS = {"views": "Views", "likes": "Likes", "comment_count": "Comments"}

TYPE_OPTIONS = [{"label": label, "value": key} for key, label in TYPE_LABELS.items()]
METRIC_OPTIONS = [{"label": label, "value": key} for key, label in METRIC_LABELS.items()]
PERIOD_OPTIONS = [
    {"label": "3M", "value": "3m"},
    {"label": "6M", "value": "6m"},
    {"label": "YTD", "value": "ytd"},
    {"label": "1Y", "value": "1y"},
    {"label": "2Y", "value": "2y"},
    {"label": "Max", "value": "max"},
]


# ---------- data ----------
def combine_types(all_dfs, selected_types):
    """Stack the chosen content-type dfs and add a readable `content_type` column."""
    frames = []
    for t in selected_types or []:
        temp = all_dfs[t].copy()
        temp["content_type"] = TYPE_LABELS[t]
        frames.append(temp)
    if not frames:
        return all_dfs["all"].iloc[0:0].assign(content_type=pd.Series(dtype="object"))
    return pd.concat(frames, ignore_index=True)


def _start_of_period(latest, period):
    if period in (None, "max", "all"):
        return None
    if period == "ytd":
        return pd.Timestamp(year=latest.year, month=1, day=1, tz=latest.tz)
    months = {"3m": 3, "6m": 6, "1y": 12, "2y": 24}[period]
    return latest - pd.DateOffset(months=months)


def filter_period(df, period, latest):
    """Rows uploaded inside the selected window (window ends at the newest upload overall)."""
    start = _start_of_period(latest, period)
    return df if start is None else df[df["upload_time"] >= start]


def previous_window(df, period, latest):
    """Rows from the equally long window right before the selected one (None for Max)."""
    start = _start_of_period(latest, period)
    if start is None:
        return None
    length = latest - start
    return df[(df["upload_time"] >= start - length) & (df["upload_time"] < start)]


def comparison_label(period, latest):
    """
    Words for the window a KPI is compared against, e.g. ("6 months", "1 Mar 2025 – 31 Aug 2025").
    Returns (None, None) for Max, which has nothing earlier to compare with.
    """
    start = _start_of_period(latest, period)
    if start is None:
        return None, None
    length = latest - start
    fixed = {"3m": "3 months", "6m": "6 months", "1y": "year", "2y": "2 years"}
    if period in fixed:
        text = fixed[period]
    elif length.days < 60:  # ytd early in the year
        text = f"{length.days} days"
    else:  # ytd: as many months as the year has run so far
        months = round(length.days / 30.44)
        text = f"{months} months"
    prev_start = start - length
    prev_end = start - pd.Timedelta(days=1)
    date_range = f"{prev_start:%d %b %Y} – {prev_end:%d %b %Y}"
    return text, date_range


def drop_partial_month(df):
    """
    The month the data was pulled in is incomplete, which makes every monthly
    line/bar plunge on the right edge. Hide it unless the pull happened on the last day.
    """
    asof = data_as_of()
    if asof.day >= asof.days_in_month:
        return df
    cutoff = pd.Timestamp(year=asof.year, month=asof.month, day=1)
    return df[df["upload_month"] < cutoff]


def add_multiples(df, metric, window=20, min_periods=5):
    """
    How many times bigger than "normal" each upload was: the metric divided by
    the median of that content type's previous `window` uploads. Needs the FULL history
    (call before filtering by period) so early rows in a window still have a baseline.
    """
    out = []
    for _, g in df.sort_values("upload_time").groupby("content_type"):
        baseline = g[metric].shift(1).rolling(window, min_periods=min_periods).median()
        out.append(g.assign(multiple=g[metric] / baseline))
    if not out:
        return df.assign(multiple=np.nan)
    res = pd.concat(out)
    res = res.replace([np.inf, -np.inf], np.nan)
    return res[res["multiple"] > 0]


def pct_change(current, previous):
    if previous is None or previous == 0 or pd.isna(previous) or pd.isna(current):
        return None
    return (current - previous) / previous * 100


# ---------- UI pieces ----------
def filter_group(label, component):
    return html.Div([html.Span(label, className="filter_label"), component], className="filter_group")


def type_checklist(component_id, default=("videos",)):
    return dcc.Checklist(id=component_id, options=TYPE_OPTIONS, value=list(default),
                         inline=True, className="pill_group")


def period_radio(component_id, default="ytd"):
    return dcc.RadioItems(id=component_id, options=PERIOD_OPTIONS, value=default,
                          inline=True, className="pill_group")


def metric_dropdown(component_id, default="views"):
    return dcc.Dropdown(id=component_id, options=METRIC_OPTIONS, value=default, clearable=False)


def kpi_card(label, value, delta=None, delta_kind="pct", up_is_good=True, compare_to=None, compare_range=None,
             compare_phrase=None):
    """
    Stat tile: big number + change vs the previous window.
    The arrow and sign carry the direction (colour is a bonus, never the only cue).
    """
    if delta is None:
        delta_el = html.Div("no earlier period to compare", className="kpi_delta flat")
    else:
        direction = "up" if delta > 0.05 else "down" if delta < -0.05 else "flat"
        arrow = {"up": "▲", "down": "▼", "flat": "▬"}[direction]
        amount = f"{abs(delta):.0f}%" if delta_kind == "pct" else f"{abs(delta):.1f} pts"
        tone = "flat" if direction == "flat" or up_is_good is None else (
            "good" if (direction == "up") == up_is_good else "bad")
        # compare_to is e.g. "6 months"; hovering the line shows the exact dates being compared against
        what = compare_phrase or (f"previous {compare_to}" if compare_to else "previous period")
        delta_el = html.Div(f"{arrow} {amount} vs {what}", className=f"kpi_delta {tone}",
                            title=f"Compared with {compare_range}" if compare_range else None)
    return html.Div([
        html.P(label, className="kpi_label"),
        html.P(value, className="kpi_value"),
        delta_el,
    ], className="kpi_card")
