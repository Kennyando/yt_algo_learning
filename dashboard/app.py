#frame and router, layout and putting together all the pages

import dash
from dash import dcc, Dash, html
from utils.data_loader import load_channel_stats

#need suppress_callback_exceptions for dynamic and multipage because dash tries to check if all the elements are there at the start
app = Dash(__name__, use_pages = True, suppress_callback_exceptions = True)
server = app.server #standard if ever want to deploy

#load channel stats from the loader
channel_stats = load_channel_stats()

# to prepare for channel count, format number since people have billions of views, subs etc
def format_count(n):
    if n is None:
        return "Hidden"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}BIL"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    return f"{n:,}"

app.layout = html.Div([
    html.Div([
        html.H2('Channel Dashboard for Ludwig'),
        html.Div([ #wrapper into python list
            dcc.Link(page['name'], href = page['path'], className = "nav-link") #will show a link which you can click on to change page, list comprehension 
            for page in dash.page_registry.values() #get page for every page registered so no need to hard the names like best page, best thumbnails etc
        ], className = "nav-links")
    ], className = "navbar"),

    #div for the channel stats
    html.Div([
        #div for each stat, subscriber, views, uploads
        html.Div([
           html.P(format_count(channel_stats['subscriber_count']), className = "stat_value") ,
           html.P("Subscribers", className = "stat_label")
        ], className = "stat_card"),
        html.Div([
            html.P(format_count(channel_stats['total_view_count']), className = "stat_value"),
            html.P("Total Views", className= "stat_label")
        ], className = "stat_card"),
        html.Div([
            html.P(format_count(channel_stats['video_count']), className = "stat_value"),
            html.P("Videos Uploaded", className = "stat_label")
        ], className = "stat_card")

    ], className= "stat_bar"),
    dash.page_container
])

if __name__ == "__main__":
    app.run(debug=True)