#frame and router, layout and putting together all the pages

import dash
from dash import dcc, Dash, html

#need suppress_callback_exceptions for dynamic and multipage because dash tries to check if all the elements are there at the start
app = Dash(__name__, use_pages = True, suppress_callback_exceptions = True)
server = app.server #standard if ever want to deploy

app.layout = html.Div([
    html.Div([
        html.H2('Lugwig Channel Dashboard'),
        html.Div([ #wrapper into python list
            dcc.Link(page['name'], href = page['path'], className = "nav-link") #will show a link which you can click on to change page, list comprehension 
            for page in dash.page_registry.values() #get page for every page registered so no need to hard the names like best page, best thumbnails etc
        ], className = "nav-links")
    ], className = "navbar"),

    dash.page_container
])

if __name__ == "__main__":
    app.run(debug=True)