# src/components/layout.py
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output
from server import app
from data_processing.movie_data import process_movie_data
from data_processing.features import get_top_actors, get_top_directors, get_top_actors_avg_profitability, get_top_directors_avg_profitability

genres_data, budget_vs_revenue_data, release_years_data, sorted_average_genre_ratings, roi_category_counts, moyenne_profitability_df, runtime_counts, avg_runtime_profitability = process_movie_data()
top_actors_df = get_top_actors()
top_directors_df = get_top_directors()
top_actors_avg_profitability_df = get_top_actors_avg_profitability()
top_directors_avg_profitability_df = get_top_directors_avg_profitability()

app_layout = html.Div([
    html.H1("Les 880 Films les Plus Populaires de TMDB : Analyse et Prédiction"),

    dcc.Tabs([
        dcc.Tab(label="Films par Genre", children=[
            dcc.Graph(
                id="movies-by-genre",
                figure=px.bar(
                    x=list(genres_data.keys()),
                    y=list(genres_data.values()),
                    labels={"x": "Genre", "y": "Nombre de films"},
                    title="Nombre de films par genre"
                )
            )
        ]),

        dcc.Tab(label="Rentabilité des films", children=[
            dcc.Graph(
                id="roi-categorized-distribution",
                figure=px.bar(
                    roi_category_counts,
                    x="ROI Category",
                    y="Count",
                    labels={"ROI Category": "Profitability Category", "Count": "Nombre de films"},
                    title="Répartition de la rentabilité des films",
                    text_auto=True
                )
            ),
            dcc.Graph(
                id="success-ratio",
                figure=px.pie(
                    names=budget_vs_revenue_data[budget_vs_revenue_data["Success"].isin(["Rentable", "Non Rentable"])]["Success"].value_counts().index,
                    values=budget_vs_revenue_data[budget_vs_revenue_data["Success"].isin(["Rentable", "Non Rentable"])]["Success"].value_counts().values,
                    title="Proportion de films Rentables vs Non Rentables (rentable si RSI > 1)"
                )
            )
        ]),

        dcc.Tab(label="Score d'évaluation par genre", children=[
            dcc.Graph(
                id="average-rating-by-genre",
                figure=px.bar(
                    x=list(sorted_average_genre_ratings.keys()),
                    y=list(sorted_average_genre_ratings.values()),
                    labels={"x": "Genre", "y": "Scores d'évaluation"},
                    title="Moyenne des scores d'évaluation par genre",
                    text_auto=True
                )
            )
        ]),

        dcc.Tab(label="Analyse Dynamique", children=[
            html.Div([
                dcc.Graph(id="dynamic-roi-histogram"),
                html.Label(
                    "Nombre de divisions de l'intervalle :",
                    style={
                        "font-size": "20px",
                        "font-weight": "bold", 
                        #"margin-top": "20px",
                        "margin-bottom": "20px",
                        "display": "block" 
                    }
                ),
                dcc.Slider(
                    id="bins-slider",
                    min=5, max=25, step=1, value=20,
                    marks={i: str(i) for i in range(5, 55, 5)}
                )
            ]),

            html.Hr(style={"border": "1px solid black", "margin-top": "20px", "margin-bottom": "20px"}),

            html.Div([
                html.Label(
                    "Filtrer par rentabilité:",
                    style={
                        "font-size": "20px",
                        "font-weight": "bold", 
                        "margin-top": "20px",
                        "margin-bottom": "20px",
                        "display": "block" 
                    }
                ),
                dcc.Dropdown(
                    id="success-filter",
                    options=[
                        {"label": "All", "value": "All"},
                        {"label": "Rentable", "value": "Rentable"},
                        {"label": "Non Rentable", "value": "Non Rentable"}
                    ],
                    value="All",
                    clearable=False
                ),
                dcc.Graph(id="filtered-scatter-plot")
            ])
        ]),

        dcc.Tab(label="Rentabilité & Score d'évaluation", children=[
            html.Div([
                dcc.Graph(id="profitability-by-rating")
            ])
        ]),

        dcc.Tab(label="Acteurs & Réalisateurs", children=[
            dcc.Graph(
                id="top-actors",
                figure=px.bar(
                    get_top_actors(),
                    x="Appearances",
                    y="Actor",
                    orientation="h",
                    title="Top 10 des acteurs ayant le plus d'apparitions dans des films",
                    labels={"Appearances": "Nombre de films", "Actor": "Acteur"},
                ).update_layout(yaxis={"categoryorder": "total ascending"})
            ),
            dcc.Graph(
                id="top-actors-profitability",
                figure=px.bar(
                    top_actors_avg_profitability_df,
                    x="Avg Profitability",
                    y="Actor",
                    orientation="h",
                    title="Top 10 des acteurs ayant la plus grande rentabilité (+8 films)",
                    labels={"Avg Profitability": "RSI moyen", "Actor": "Acteur"},
                ).update_layout(yaxis={"categoryorder": "total ascending"})
            ),
            dcc.Graph(
                id="top-directors",
                figure=px.bar(
                    top_directors_df,
                    x="Number of Films",
                    y="Director",
                    orientation="h",
                    title="Top 10 des réalisateurs ayant réalisé le plus de films",
                    labels={"Number of Films": "Nombre de films réalisés", "Director": "Réalisateur"},
                    color_discrete_sequence=["#FF0000"]
                ).update_layout(yaxis={"categoryorder": "total ascending"})
            ),
            dcc.Graph(
                id="top-directors-avg-profitability",
                figure=px.bar(
                    top_directors_avg_profitability_df,
                    x="Avg Profitability",
                    y="Director",
                    orientation="h",
                    title="Top 10 des réalisateurs avec la plus grande rentabilité moyenne (+4 films)",
                    labels={"Avg Profitability": "RSI moyen", "Director": "Réalisateur"},
                    color_discrete_sequence=["#FF0000"]
                ).update_layout(yaxis={"categoryorder": "total ascending"})
            )
        ]),

        dcc.Tab(label="Distribution des durées de films", children=[
            dcc.Graph(
                id="runtime-distribution",
                figure=px.bar(
                    runtime_counts,
                    x="Runtime (min)",
                    y="Number of Films",
                    labels={"Runtime (min)": "Durée (minutes)", "Number of Films": "Nombre de films"},
                    title="Nombre de films en fonction de la durée",
                    text_auto=True
                )
            )
        ]),

        dcc.Tab(label="Rentabilité & Durée de films", children=[
            dcc.Graph(
                id="runtime-profitability",
                figure=px.line(
                    avg_runtime_profitability,
                    x="Runtime (min)",
                    y="Profitability (%)",
                    labels={"Runtime (min)": "Catégorie de durée de films(minutes)", "Profitability (%)": "Rentabilité moyenne (%)"},
                    title="Rentabilité moyenne en fonction de la durée",
                    markers=True
                )
            )
        ])

    ])
])

app.layout = app_layout

@app.callback(
    Output("dynamic-roi-histogram", "figure"),
    Input("bins-slider", "value")
)
def update_histogram(bins):
    fig = px.histogram(
        budget_vs_revenue_data, x="ROI", nbins=bins,
        labels={"ROI": "Retour sur Investissement (RSI)"},
        title=f"Distribution du RSI (Intervalles : {bins})"
    )
    fig.update_layout(yaxis_title="Nombre de films")
    return fig

@app.callback(
    Output("filtered-scatter-plot", "figure"),
    Input("success-filter", "value")
)
def update_scatter(selected_category):
    filtered_data = budget_vs_revenue_data if selected_category == "All" else budget_vs_revenue_data[budget_vs_revenue_data["Success"] == selected_category]
    
    fig = px.scatter(
        filtered_data, x="budget", y="revenue", trendline="ols",
        labels={"budget": "Budget (USD)", "revenue": "Recette (USD)"},
        title=f"Corrélation entre Budget et Recette (Filtre: {selected_category})",
        hover_data=["title"]
    )
    return fig

@app.callback(
    Output("profitability-by-rating", "figure"),
    Input("profitability-by-rating", "id")
)
def update_profitability_graph(_):
    fig = px.scatter(
        budget_vs_revenue_data, x="rating", y="Profitability (%)",
        labels={"rating": "Score d'évaluation", "Profitability (%)": "Rentabilité (%)"},
        title="Rentabilité en fonction du score d'évaluation",
        hover_data=["title"],
        trendline="ols"  
    )

    moyenne_profitability_df["Moyenne Profitability (%)"] = moyenne_profitability_df["Moyenne Profitability (%)"].apply(
    lambda x: np.round(x) if not pd.isna(x) else x
    )
    moyenne_trace = go.Scatter(
        x=moyenne_profitability_df["rating"],
        y=moyenne_profitability_df["Moyenne Profitability (%)"],
        mode="markers",
        marker=dict(size=10, color="red", symbol="diamond"),
        name="Rentabilité moyenne (+10 films)*appuyer pour activer/désactiver"
    )

    fig.add_trace(moyenne_trace)

    return fig
