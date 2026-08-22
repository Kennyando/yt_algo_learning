import dash
import pandas as pd
from dash import html, dcc, callback, Input, Output
import plotly.express as px
from utils.data_loader import load_data #function from data loader python file

#register python file as a page and make it available at the path "/" which is the root of the website, as overview
dash.register_page(__name__, path = "/", name = "Overview") 

all_dfs = load_data()

layout = html.Div([
    html.H3("Channel Overview"),

    dcc.Checklist(
        id = "content_type_filter",
        options = [
            {"label": "Videos", "value" : "videos"}, #videos corresponds to the videos df loaded, same for others
            {"label": "Shorts", "value" : "shorts"},
            {"label": "VODs", "value" : "vods"},
        ],
        value = ['videos', 'shorts', 'vods'],
        inline = True
    ),

    #to toggle between what metrics you want to view
    dcc.Dropdown(
        id = "metrics_dropdown",
        options = [
            {"label": "Views", "value": "views"},
            {"label": "Likes", "value": "likes"},
            {"label": "Comments", "value": "comment_count"},
        ],
        value = "views"
    ),

    dcc.Graph(id = "overview_graph")
])

@callback(
    Output("overview_graph", "figure"),
    Input("content_type_filter", "value"),
    Input("metrics_dropdown", "value")
)

#make year to date and 1y 2y recent, follows order of the callback, first input in callback = first input in function that its decorating
#its a bit too noisy rn, cant tell, could do something to toggle total views per month, need to distinguish the dots between shorts, vods, videos
def update_graph(selected_types, metric):
    dfs_to_plot = []
    for t in selected_types:
        temp = all_dfs[t].copy()
        temp['content_type'] = t
        dfs_to_plot.append(temp)
    combined = pd.concat(dfs_to_plot)

    fig = px.scatter(
        combined,
        x = "upload_date",
        y = metric,
        color = "content_type",
        hover_data = ['title'],
        title = f"{metric.replace("_"," ").title()} over time"
    )
    return fig