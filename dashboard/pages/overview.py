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
    #grid layout for graphs
    html.Div([
        dcc.Graph(id = "monthly_total"),
        dcc.Graph(id= "monthly_avg"),
        dcc.Graph(id="monthly_uploads"),
        dcc.Graph(id="placeholder")
    ], style = {
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr",
        "gridTemplateRows": "1fr 1fr",
        "gap": "10px"
    })
])

@callback(
    Output("monthly_total", "figure"),
    Output("monthly_avg", "figure"),
    Output("monthly_uploads", "figure"),
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
    combined_df = pd.concat(dfs_to_plot)

    #monthly total at 0,0 position
    monthly_total = combined_df.groupby(['upload_month','content_type'])[metric].sum().reset_index()
    monthly_total_fig = px.line(
        monthly_total, x = "upload_month", y = metric, color = "content_type",
        title = f"Total {metric.replace("_", " ").title()} per Month"
    )
    monthly_total_fig.update_xaxes(tickformat = "%b %Y") #format date to show yyyy-m

    #monthly avg
    monthly_avg = combined_df.groupby(['upload_month','content_type'])[metric].mean().reset_index()
    monthly_avg_fig = px.line(
        monthly_avg, x = "upload_month", y = metric, color = "content_type", 
        title = f"Average {metric.replace("_", " ").title()} per Video"
    )
    monthly_avg_fig.update_xaxes(tickformat = "%b %Y")
    #monthly uploads
    monthly_uploads = combined_df.groupby(['upload_month','content_type'])['video_id'].count().reset_index()
    monthly_uploads = monthly_uploads.rename(columns = {"video_id": "uploads"})
    monthly_uploads_fig = px.bar(
        monthly_uploads, x = 'upload_month', y = "uploads", color = "content_type",
        title = "Uploads per Month", barmode = "stack", opacity = 0.6
    )
    monthly_uploads_fig.update_xaxes(tickformat = "%b %Y")

    #will not be using for now
    scatter = px.scatter(
        combined_df,
        x = "upload_date",
        y = metric,
        color = "content_type",
        hover_data = ['title'],
        title = f"{metric.replace("_"," ").title()} over time"
    )


    return monthly_total_fig, monthly_avg_fig, monthly_uploads_fig