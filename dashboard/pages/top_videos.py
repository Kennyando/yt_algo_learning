import dash
import numpy as np
from dash import html, callback, Input, Output, dcc

from utils.data_loader import load_data
from utils.helpers import (
    TYPE_LABELS, METRIC_LABELS, METRIC_OPTIONS, filter_period, filter_group, period_radio,
)
from theme import compact, fmt_duration

# measure via views and display the videos in a youtube card style

# register page
dash.register_page(__name__, path="/top-videos", name="Top Videos")

all_dfs = load_data()

layout = html.Div([
    html.H3("Top Videos"),

    html.Div([
        filter_group("Content", dcc.RadioItems(
            id="top_content_type_filter",
            options=[{"label": label, "value": key} for key, label in TYPE_LABELS.items()],
            value="videos", inline=True, className="pill_group")),
        filter_group("Rank by", dcc.Dropdown(
            id="top_metric_filter", options=METRIC_OPTIONS, value="views", clearable=False)),
        filter_group("Period", period_radio("top_time_period_filter")),
    ], className="filter_bar"),

    html.Div(id="top_video_cards", className="card_grid"),
])


@callback(
    Output("top_video_cards", "children"),
    Input("top_content_type_filter", "value"),
    Input("top_time_period_filter", "value"),
    Input("top_metric_filter", "value"),
)
def update_top_videos(content_type, time_period, metric):
    # choose the correct df and window (same window logic as the other pages)
    latest = all_dfs["all"]["upload_time"].max()
    df = filter_period(all_dfs[content_type], time_period, latest)
    if df.empty:
        return html.P("No uploads in this window.", className="footnote")

    median = df[metric].median()
    label = METRIC_LABELS[metric].lower()

    # get top 10 videos by metric selected
    top10 = df.sort_values(metric, ascending=False).head(10)

    cards = []  # list of <a> tags, one per video; dash unpacks a list in children like react
    # itertuples lets you iterate row by row, returns a named tuple for each row
    for rank, row in enumerate(top10.itertuples(), start=1):
        value = getattr(row, metric)
        multiple = value / median if median else np.nan
        like_rate = row.likes / row.views * 100 if row.views else 0
        cards.append(html.A([
            html.Div([
                html.Img(src=row.thumbnail_url, className="thumbnail"),
                html.Span(f"#{rank}", className="rank_badge"),
                html.Span(fmt_duration(row.duration_minutes), className="duration_badge"),
            ], className="thumb_wrap"),
            html.P(row.title, className="video_title"),
            html.Div([
                html.Span(f"{compact(value)} {label}", className="card_main_stat"),
                html.Span(f"{multiple:.1f}× median", className="chip") if multiple >= 1.5 else None,
            ], className="card_row"),
            html.P(f"{compact(row.likes)} likes · {compact(row.comment_count)} comments", className="card_meta"),
            html.P(f"{like_rate:.1f}% like rate · {row.upload_date:%d %b %Y}", className="card_meta"),
        ], href=row.video_url, target="_blank", className="video_card"))  # opens in a new tab

    return cards
