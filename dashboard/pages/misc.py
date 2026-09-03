import dash
import pandas as pd
from dash import Dash, dcc, html, callback, Input, Output
from utils.data_loader import load_data
import plotly.express as px

#register page
dash.register_page(__name__, path= "/misc", name = "Miscellaneous Stats")

all_dfs = load_data()

layout = html.Div([
    html.H3("Miscellaneous statistics"),

    dcc.Checklist(
        id = "misc_content_type_filter",
        options = [
            {"label": "Videos", "value": "videos"},
            {"label": "Shorts", "value": "shorts"},
            {"label": "VODs", "value": "vods"},
        ],
        value = ["videos"],
        inline = True
    ),

    dcc.RadioItems(
        id = "misc_time_period_filter",
        options = [
            {"label": "3M", "value": "3m"},
            {"label": "6M", "value": "6m"},
            {"label": "YTD", "value": "ytd"},
            {"label": "1Y", "value": "1y"},
            {"label": "2Y", "value": "2y"},
            {"label": "Max", "value": "all"},
        ],
        value = "ytd",
        inline = True
    ),

    html.Div([
        dcc.Graph(id = "misc_hour_day_heatmap"),
        dcc.Graph(id = "misc_duration_dist"),
        dcc.Graph(id = "misc_views_dist"),
        dcc.Graph(id = "misc_views_likes_scatter"),
        dcc.Graph(id = "misc_upload_gap_hist", style = {"gridColumn": "1/3"}),
    ], style = {
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr",
        "gridTemplateRows": "1fr 1fr 1fr",
        "gap": "10px"
    })
])


@callback(
    Output("misc_hour_day_heatmap", "figure"),
    Output("misc_duration_dist", "figure"),
    Output("misc_views_dist", "figure"),
    Output("misc_views_likes_scatter", "figure"),
    Output("misc_upload_gap_hist", "figure"),
    Input("misc_content_type_filter", "value"),
    Input("misc_time_period_filter", "value")
)

def update_misc_graphs(selected_types, time_period):
    dfs_to_plot = []
    for type in selected_types:
        temp = all_dfs[type].copy() #copy that content df
        temp['content_type'] = type #make a new col content type to distinguish
        dfs_to_plot.append(temp)
    combined_df = pd.concat(dfs_to_plot)

    if time_period != "all":
        latest_date = combined_df['upload_time'].max()
        if time_period == "3m":
            start_date = latest_date - pd.DateOffset(months = 3)
        elif time_period == "6m":
            start_date = latest_date - pd.DateOffset(months = 6)
        elif time_period == "ytd": 
            start_date = pd.Timestamp(year = latest_date.year, month = 1, day = 1 , tz = latest_date.tz)
        elif time_period == "1y":
            start_date = latest_date - pd.DateOffset(years = 1)
        elif time_period == "2y":
            start_date = latest_date - pd.DateOffset(years = 2)
        combined_df = combined_df[combined_df['upload_time'] >= start_date]

    def get_time_block(hour):
        if hour < 8:
            return "12AM - 8AM"
        elif hour < 16:
            return "8AM - 4PM"
        else:
            return "4PM - 12AM"

    #hour x day_of the week uploaded heatmap
    #map out upload hour
    combined_df['time_block'] = combined_df['upload_hour'].apply(get_time_block)

    combined_df['day_of_week'] = combined_df['upload_time'].dt.day_name()
    heatmap_fig = px.density_heatmap(
        combined_df, x = "time_block", y = "day_of_week",
        category_orders={"time_block": ["12AM - 8AM", "8AM - 4PM", "4PM - 12AM"]},
        title = "Most Common Days and Hours Uploaded"
    )

    #duration distribution
    duration_dist_fig = px.histogram(
        combined_df, x= "duration_minutes", color = "content_type",
        title = "Distribution of Length of Uploads"
    )

    #views distribution
    views_dist_fig = px.histogram(
        combined_df, x = "views", color = "content_type",
        title = "Distribution of Views of an Upload"
        
    )

    #views vs likes scatter
    views_likes_fig = px.scatter(
        combined_df, x = "views", y = "likes", color = "content_type",
        hover_data = ["title"],
        title = "Relationship Between Views and Likes"
    )

    #gap between uploads, in days

    sorted_df = combined_df.sort_values("upload_time")
    sorted_df["days_since_last_upload"] = sorted_df["upload_time"].diff().dt.total_seconds() / 86400
    upload_gap_fig = px.histogram(
        sorted_df, x = "days_since_last_upload",
        title = "Days Between Uploads"
    )

    return heatmap_fig, duration_dist_fig, views_dist_fig, views_likes_fig, upload_gap_fig