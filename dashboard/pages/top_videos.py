import pandas as pd
import dash
from dash import html, dcc, callback, Input, Output
from utils.data_loader import load_data


#measure via views and display the videos in a youtube card style

#register page
dash.register_page(__name__, path = "/top-videos", name = "Top Videos")

all_dfs = load_data()

layout = html.Div([
    html.H3("Top Videos"),

    dcc.RadioItems(
        id = "top_content_type_filter",
        options = [
            {"label": "Videos", "value": "videos"},
            {"label": "Shorts", "value": "shorts"},
            {"label": "VODs", "value": "vods"},
        ],
        value = "videos",
        inline = True
    ),

    dcc.RadioItems(
        id = "top_time_period_filter",
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

    dcc.Dropdown(
        id = "top_metric_filter",
        options = [
            {"label": "Views", "value" : "views"},
            {"label": "Likes", "value" : "likes"},
            {"label": "Comments", "value" : "comment_count"},
        ],
        value = "views"
    ),

    html.Div(id = "top_video_cards", className = "card_grid")
])

@callback(
    Output("top_video_cards", "children"),
    Input("top_content_type_filter", "value"),
    Input("top_time_period_filter", "value"),
    Input("top_metric_filter", "value")
)

def update_top_videos(content_type, time_period, metric):
    #choose the correct df
    df = all_dfs[content_type].copy()

    if time_period != "all":
        latest_date = df["upload_time"].max()
        if time_period == "3m":
            start_date = latest_date - pd.DateOffset(months = 3)
        elif time_period == "6m": 
            start_date = latest_date - pd.DateOffset(months = 6)
        elif time_period == "ytd":
            start_date = pd.Timestamp(year = latest_date.year, month = 1 , day = 1, tz = latest_date.tz)
        elif time_period == "1y":
            start_date = latest_date - pd.DateOffset(years = 1)
        elif time_period == "2y":
            start_date = latest_date - pd.DateOffset(years = 2)

        df = df[df["upload_time"] >= start_date]

    #get top 10 videos by metric selected
    top10 = df.sort_values(metric, ascending = False).head(10)

    cards = [] #make a list of A tags which is individual video tags, and children in the output will unpack each iterable when it sees a list, same as react
    #itertuples lets you iterate row by row, without it it will iterate over the column names, returns a named tuple for each row
    for row in top10.itertuples():
        #create a card for each video, <a> tag for links,
        card = html.A([
            html.Img(src = row.thumbnail_url, className = "thumbnail"), #since we used itertuples can just do row.xxx instead of row['xx']
            html.P(row.title, className = "video_title"),
            html.P(f"{row.views:,} views"), #:, formats and inserts , every 3 digits 1000 : 1,000
            html.P(f"{row.likes:,} likes"),
            html.P(f"{row.comment_count:,} comments"),
            html.P(f"{row.upload_date}")
        ], href = row.video_url, target = "_blank", className= "video_card" #open in a new tab, ="_blank"
        )
        cards.append(card)

    return cards
    
            
