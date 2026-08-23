import dash
import pandas as pd
from dash import html, dcc, callback, Input, Output
import plotly.express as px
from utils.data_loader import load_data #function from data loader python file

#todo when polishing
#add checks for empty results, ie if no vods, no shorts or timeperiod not long enough

#register python file as a page and make it available at the path "/" which is the root of the website, as overview
dash.register_page(__name__, path = "/", name = "Overview")  #/ is also reserved for what you want to load by default

all_dfs = load_data()

layout = html.Div([
    html.H3("Channel Overview"),

    dcc.Checklist(
        id = "overview_content_type_filter",
        options = [
            {"label": "Videos", "value" : "videos"}, #videos corresponds to the videos df loaded, same for others
            {"label": "Shorts", "value" : "shorts"},
            {"label": "VODs", "value" : "vods"},
        ],
        value = ['videos'],
        inline = True
    ),

    #to toggle between what metrics you want to view
    dcc.Dropdown(
        id = "overview_metrics_dropdown",
        options = [
            {"label": "Views", "value": "views"},
            {"label": "Likes", "value": "likes"},
            {"label": "Comments", "value": "comment_count"},
        ],
        value = "views"
    ),
    #time period filter
    dcc.RadioItems(
        id = "overview_time_period_filter",
        options = [
            {"label": "6M", "value": "6m"},
            {"label": "YTD", "value": "ytd"},
            {"label": "1Y", "value": "1y"},
            {"label": "2Y", "value": "2y"},
            {"label": "Max", "value" : "max"},
        ],
        value = "ytd",
        inline = True
    ),
    #grid layout for graphs
    html.Div([
        dcc.Graph(id = "overview_monthly_total"),
        dcc.Graph(id= "overview_monthly_avg"),
        dcc.Graph(id="overview_monthly_uploads"),
        dcc.Graph(id="overview_avg_duration")
    ], style = {
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr",
        "gridTemplateRows": "1fr 1fr",
        "gap": "10px"
    })
])

@callback(
    Output("overview_monthly_total", "figure"),
    Output("overview_monthly_avg", "figure"),
    Output("overview_monthly_uploads", "figure"),
    Output("overview_avg_duration", "figure"),
    Input("overview_content_type_filter", "value"),
    Input("overview_metrics_dropdown", "value"),
    Input("overview_time_period_filter", "value")
)

#make year to date and 1y 2y recent, follows order of the callback, first input in callback = first input in function that its decorating
#its a bit too noisy rn, cant tell, could do something to toggle total views per month, need to distinguish the dots between shorts, vods, videos
def update_graph(selected_types, metric, time_period):
    dfs_to_plot = []
    for t in selected_types:
        temp = all_dfs[t].copy()
        temp['content_type'] = t
        dfs_to_plot.append(temp)
    combined_df = pd.concat(dfs_to_plot)

    #do pandas filter for time period
    if time_period != 'max':
        #find latest upload and work backwards
        latest_upload_date = combined_df["upload_time"].max()
        if time_period == "6m":
            start_date = latest_upload_date - pd.DateOffset(months= 6)
        elif time_period == "ytd": #first day of current year to current date
            start_date = pd.Timestamp(year = latest_upload_date.year, month = 1, day = 1, tz = latest_upload_date.tz)
        elif time_period == "1y":
            start_date = latest_upload_date - pd.DateOffset(years = 1)
        elif time_period == "2y":
            start_date = latest_upload_date - pd.DateOffset(years = 2)
        #use start date to filter now
        combined_df = combined_df[combined_df["upload_time"] >= start_date]
        
    #monthly gained views is probably more impactful rather than the total from that month
    #monthly total at 0,0 position
    monthly_total = combined_df.groupby(['upload_month','content_type'])[metric].sum().reset_index()
    monthly_total_fig = px.line(
        monthly_total, x = "upload_month", y = metric, color = "content_type",
        title = f"Total {metric.replace("_", " ").title()} grouped by Upload Month"
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

    #avg duration of videos, need to format the duration col because its in iso format, format into a numeric
    #need the whole row, because 2 inputs, duration and isshort
    def format_duration(row):
        minutes = row['duration_minutes']
        if row['content_type'] == 'shorts':
            seconds = minutes * 60
            return f"{seconds:.0f}s"
        hrs = int(minutes // 60)
        mins = int(minutes % 60)
        if hrs > 0:
            return f"{hrs}h {mins}m"
        return f"{mins}m"
    
    monthly_avg_duration = combined_df.groupby(['upload_month', 'content_type'])['duration_minutes'].mean().reset_index()
    #set axis = 1 to tell pandas to call the function per row
    monthly_avg_duration['duration_display'] = monthly_avg_duration.apply(format_duration, axis = 1)
    avg_duration_fig = px.line(
        monthly_avg_duration, x = "upload_month", y = "duration_minutes", color = "content_type",
        hover_data = {"duration_display": True, "duration_minutes": False},
        title = "Average Duration of Uploads per Month"
    )
    avg_duration_fig.update_xaxes(tickformat = "%b %Y")

    #will not be using for now
    scatter = px.scatter(
        combined_df,
        x = "upload_date",
        y = metric,
        color = "content_type",
        hover_data = ['title'],
        title = f"{metric.replace("_"," ").title()} over time"
    )


    return monthly_total_fig, monthly_avg_fig, monthly_uploads_fig, avg_duration_fig