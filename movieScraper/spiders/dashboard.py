import dash
from dash import dcc, html

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Dashboard des Films"),
    dcc.Graph(
        id='example-graph',
        figure={
            'data': [{'x': ['Action', 'Drame', 'Comédie'], 'y': [25, 15, 10], 'type': 'bar'}],
            'layout': {'title': 'Nombre de films par genre'}
        }
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)
