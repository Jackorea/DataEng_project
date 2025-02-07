import dash
import re
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output
from pymongo import MongoClient
from collections import Counter
import pandas as pd
import numpy as np
import plotly.express as px
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings

warnings.filterwarnings("ignore")

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["movie_database"]
collection = db["movies"]

# Chargement et traitement des données depuis MongoDB
def process_movie_data():
    movies = list(collection.find({}, {"title": 1, "genres": 1, "rating": 1, "budget_usd": 1, "recette_usd": 1, "release_date": 1, "runtime": 1, "_id": 0}))
    
    # Comptage des genres
    genre_counts = {}
    for movie in movies:
        for genre in movie.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    # Données Budget vs Recette
    budget_vs_revenue = pd.DataFrame([
        {
            "title": movie.get("title", "Unknown"),
            "budget": movie.get("budget_usd", 0),
            "revenue": movie.get("recette_usd", 0),
            "rating": movie.get("rating", None),
            "director": movie.get("director", "Unknown"),
            "actors": movie.get("actors", [])
        }
        for movie in movies if movie.get("budget_usd") and movie.get("recette_usd")
    ])
    
    # Extraction des années de sortie des films
    release_years = []
    for movie in movies:
        release_date = movie.get("release_date", "")
        match = re.search(r"\b(19\d{2}|20\d{2})\b", release_date)  # Cherche une année valide (1900-2099)
        if match:
            year = int(match.group(0))  # Convertit en entier
            release_years.append({"year": year, "count": 1})
    
    # Création du DataFrame pour les années de sortie
    if release_years:
        release_years_data = pd.DataFrame(release_years).groupby("year").count().reset_index()
    else:
        release_years_data = pd.DataFrame(columns=["year", "count"])  # DataFrame vide avec colonnes correctes
    
    # Calcul du ROI
    if not budget_vs_revenue.empty:
        # Remplace les valeurs manquantes par 0
        budget_vs_revenue["budget"] = budget_vs_revenue["budget"].fillna(0)
        budget_vs_revenue["revenue"] = budget_vs_revenue["revenue"].fillna(0)

        # Calcul du ROI en évitant la division par zéro
        budget_vs_revenue["ROI"] = budget_vs_revenue.apply(
            lambda x: (x["revenue"] - x["budget"]) / x["budget"] if x["budget"] > 0 else np.nan, axis=1
        )

        # Calculate the profitability percentage (not ROI)
        budget_vs_revenue["Profitability (%)"] = ((budget_vs_revenue["revenue"] - budget_vs_revenue["budget"]) / budget_vs_revenue["budget"]) * 100

        # Compute the average profitability per rating (excluding min & max values)
        def calculate_average_profitability(df):
            avg_profitability = {}

            for rating in df["rating"].unique():
                subset = df[df["rating"] == rating]["Profitability (%)"]
                
                if len(subset) >= 10:  # Only calculate if at least 10 values exist
                    subset = subset[(subset != subset.max()) & (subset != subset.min())]  # Remove min & max
                    avg_profitability[rating] = subset.mean() if not subset.empty else None
                else:
                    avg_profitability[rating] = None  # If less than 10 films, do not calculate

            return pd.DataFrame({"rating": list(avg_profitability.keys()), "Moyenne Profitability (%)": list(avg_profitability.values())})

        # Generate the "moyenne" profitability dataset
        moyenne_profitability_df = calculate_average_profitability(budget_vs_revenue)

        # Détermination des films rentables
        budget_vs_revenue["Success"] = budget_vs_revenue.apply(
            lambda x: "Rentable" if x["ROI"] >= 1 else "Non Rentable", axis=1  # ROI >= 1 équivaut à 2× budget
        )

        # ROI categorization function
        def categorize_roi(roi):
            if pd.isna(roi):
                return "Unknown"
            elif roi < -0.5:
                return "Severe Loss (< -50%)"
            elif -0.5 <= roi < 0:
                return "Loss (0% to -50%)"
            elif 0 <= roi < 0.5:
                return "Low Profit (0% to 50%)"
            elif 0.5 <= roi < 1:
                return "Good Profit (50% to 100%)"
            else:
                return "High Profit (> 100%)"

        # Apply categorization to dataset
        budget_vs_revenue["ROI Category"] = budget_vs_revenue["ROI"].apply(categorize_roi)

        # Count occurrences of each ROI category and rename columns properly
        roi_category_counts = budget_vs_revenue["ROI Category"].value_counts().reset_index()
        roi_category_counts.columns = ["ROI Category", "Count"]  # Rename columns

        # Define the correct order for ROI categories
        roi_order = [
            "Severe Loss (< -50%)",
            "Loss (0% to -50%)",
            "Low Profit (0% to 50%)",
            "Good Profit (50% to 100%)",
            "High Profit (> 100%)",
            "Unknown"
        ]

        # Ensure correct ordering of ROI categories
        roi_category_counts["ROI Category"] = pd.Categorical(
            roi_category_counts["ROI Category"],
            categories=roi_order,  # Enforce the correct order
            ordered=True
        )
        roi_category_counts = roi_category_counts.sort_values("ROI Category")
        
    else:
        budget_vs_revenue["ROI"] = []
        budget_vs_revenue["Success"] = []

    # Calcul de la moyenne des ratings par genre
    genre_ratings = {}
    genre_counts = {}

    for movie in movies:
        rating = movie.get("rating", None)
        if rating is not None:
            for genre in movie.get("genres", []):
                if genre in genre_ratings:
                    genre_ratings[genre] += rating
                    genre_counts[genre] += 1
                else:
                    genre_ratings[genre] = rating
                    genre_counts[genre] = 1

    # Calculer la moyenne des ratings
    average_genre_ratings = {genre: genre_ratings[genre] / genre_counts[genre] for genre in genre_ratings}

    # Trier les genres par ordre croissant de moyenne des ratings
    sorted_average_genre_ratings = dict(sorted(average_genre_ratings.items(), key=lambda item: item[1]))

    def parse_runtime(runtime_str):
        """
        Convertit une chaîne de runtime (ex: "2h 41m") en minutes entières.
        Gère les cas où runtime est None ou vide.
        """
        if not isinstance(runtime_str, str) or not runtime_str.strip():
            return np.nan  # Retourne NaN si runtime est None ou vide

        hours_match = re.search(r"(\d+)h", runtime_str)
        minutes_match = re.search(r"(\d+)m", runtime_str)

        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0

        return hours * 60 + minutes

    # 🔹 Extraction des durées des films et regroupement par tranches de 10 minutes
    runtimes = [parse_runtime(movie.get("runtime", "")) for movie in movies if movie.get("runtime")]

    if runtimes:  # Vérifie s'il y a au moins une valeur valide
        runtimes_rounded = [round(rt, -1) for rt in runtimes]
        runtime_counts = pd.Series(runtimes_rounded).value_counts().reset_index()
        runtime_counts.columns = ["Runtime (min)", "Number of Films"]
        runtime_counts = runtime_counts.sort_values("Runtime (min)")
    else:
        runtime_counts = pd.DataFrame(columns=["Runtime (min)", "Number of Films"])


    # Compute profitability vs runtime
    runtime_profitability_data = []
    for movie in movies:
        runtime = parse_runtime(movie.get("runtime", ""))
        budget = movie.get("budget_usd", 0) or 0  # Ensure budget is a number
        revenue = movie.get("recette_usd", 0) or 0  # Ensure revenue is a number

        if pd.notna(runtime) and isinstance(budget, (int, float)) and budget > 0:

            profitability = ((revenue - budget) / budget) * 100  # Profitability in %
            runtime_rounded = round(runtime, -1)  # Round to nearest 10 minutes
            runtime_profitability_data.append({"Runtime (min)": runtime_rounded, "Profitability (%)": profitability})

    # Convert to DataFrame
    if runtime_profitability_data:
        avg_runtime_profitability = pd.DataFrame(runtime_profitability_data)
        avg_runtime_profitability = avg_runtime_profitability.groupby("Runtime (min)")["Profitability (%)"].mean().reset_index()
    else:
        avg_runtime_profitability = pd.DataFrame(columns=["Runtime (min)", "Profitability (%)"])

    return genre_counts, budget_vs_revenue, release_years_data, sorted_average_genre_ratings, roi_category_counts, moyenne_profitability_df, runtime_counts, avg_runtime_profitability

# Traitement des données
genres_data, budget_vs_revenue_data, release_years_data, sorted_average_genre_ratings, roi_category_counts, moyenne_profitability_df, runtime_counts, avg_runtime_profitability = process_movie_data()

def get_top_actors():
    movies = list(collection.find({}, {"actors": 1, "_id": 0}))  # Fetch actors from MongoDB
    actor_count = Counter(actor for movie in movies for actor in movie.get("actors", []))
    top_actors = actor_count.most_common(10)  # Get top 10 actors
    return pd.DataFrame(top_actors, columns=["Actor", "Appearances"])

def get_top_actors_avg_profitability():
    movies = list(collection.find({}, {"actors": 1, "budget_usd": 1, "recette_usd": 1, "_id": 0}))

    actor_profitability = {}
    actor_counts = {}

    for movie in movies:
        budget = movie.get("budget_usd", 0) or 0  # Ensure it's never None
        revenue = movie.get("recette_usd", 0) or 0  # Ensure it's never None

        if budget > 0:  # Prevent division by zero
            profitability = (revenue - budget) / budget  # ROI formula
            
            for actor in movie.get("actors", []):
                actor_profitability[actor] = actor_profitability.get(actor, 0) + profitability
                actor_counts[actor] = actor_counts.get(actor, 0) + 1

    # Filter actors who have appeared in 3 or more films
    filtered_actors = {actor: actor_profitability[actor] / actor_counts[actor] 
                       for actor in actor_profitability if actor_counts[actor] >= 8}

    # Get top 10 most profitable actors (sorted by highest average profitability)
    top_profitable_actors = sorted(filtered_actors.items(), key=lambda x: x[1], reverse=True)[:10]

    return pd.DataFrame(top_profitable_actors, columns=["Actor", "Avg Profitability"])


def get_top_directors():
    movies = list(collection.find({}, {"director": 1, "_id": 0}))

    director_count = {}
    
    for movie in movies:
        director = movie.get("director", "Unknown")
        if director:
            director_count[director] = director_count.get(director, 0) + 1

    # Get top 10 directors with the most films
    top_directors = sorted(director_count.items(), key=lambda x: x[1], reverse=True)[:10]

    return pd.DataFrame(top_directors, columns=["Director", "Number of Films"])

def get_top_directors_avg_profitability():
    movies = list(collection.find({}, {"director": 1, "budget_usd": 1, "recette_usd": 1, "_id": 0}))

    director_profitability = {}
    director_counts = {}

    for movie in movies:
        director = movie.get("director", "Unknown")
        budget = movie.get("budget_usd", 0) or 0  # Ensure it's never None
        revenue = movie.get("recette_usd", 0) or 0  # Ensure it's never None

        if budget > 0:  # Prevent division by zero
            profitability = (revenue - budget) / budget  # ROI formula

            if director in director_profitability:
                director_profitability[director] += profitability
                director_counts[director] += 1
            else:
                director_profitability[director] = profitability
                director_counts[director] = 1

    # Filter directors who have directed 4 or more films
    filtered_directors = {director: director_profitability[director] / director_counts[director] 
                          for director in director_profitability if director_counts[director] >= 4}

    # Get top 10 most profitable directors (sorted by highest average profitability)
    top_profitable_directors = sorted(filtered_directors.items(), key=lambda x: x[1], reverse=True)[:10]

    return pd.DataFrame(top_profitable_directors, columns=["Director", "Avg Profitability"])


# Fetch the top 10 actors by highest average profitability (among actors with 3+ films)
top_actors_avg_profitability_df = get_top_actors_avg_profitability()

top_actors_df = get_top_actors()  # ✅ Add this line to store actor data
# Fetch the top 10 actors by highest profitability
top_actors_profitability_df = get_top_actors_avg_profitability()  # ✅ Call the function before using it in the layout
# Fetch the top 10 directors with the most films
top_directors_df = get_top_directors()
# Fetch the top 10 directors by highest average profitability (among directors with 4+ films)
top_directors_avg_profitability_df = get_top_directors_avg_profitability()



# Prédiction des tendances de sorties de films
if not release_years_data.empty:  # Vérifie que le DataFrame n'est pas vide
    model = ExponentialSmoothing(release_years_data["count"], trend="add", seasonal=None)
    fit = model.fit()
    future_years = list(range(release_years_data["year"].max() + 1, release_years_data["year"].max() + 6))
    predictions = fit.forecast(len(future_years))
    predicted_data = pd.DataFrame({"year": future_years, "count": predictions})

    # Fusion des données historiques et des prévisions
    full_release_data = pd.concat([release_years_data, predicted_data], ignore_index=True)
else:
    full_release_data = release_years_data  # Évite une erreur si aucune donnée historique

# Création de l'application Dash
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Dashboard des 880 Films les plus populaires - Analyse et Prédiction"),

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

        dcc.Tab(label="Rentabilité", children=[
            dcc.Graph(
                id="roi-categorized-distribution",
                figure=px.bar(
                    roi_category_counts,
                    x="ROI Category",
                    y="Count",
                    labels={"ROI Category": "Profitability Category", "Count": "Number of Movies"},
                    title="Distribution of Movie Profitability (Sorted in Ascending Order)",
                    text_auto=True
                )
            ),
            dcc.Graph(
                id="success-ratio",
                figure=px.pie(
                    names=budget_vs_revenue_data["Success"].value_counts().index,
                    values=budget_vs_revenue_data["Success"].value_counts().values,
                    title="Proportion de films Rentables vs Non Rentables (rentable si profit > 100%)"
                )
            )
        ]),

        dcc.Tab(label="Ratings", children=[
            dcc.Graph(
                id="average-rating-by-genre",
                figure=px.bar(
                    x=list(sorted_average_genre_ratings.keys()),
                    y=list(sorted_average_genre_ratings.values()),
                    labels={"x": "Genre", "y": "Moyenne des Ratings"},
                    title="Moyenne des Ratings par Genre (Trié par ordre croissant)",
                    text_auto=True
                )
            )
        ]),

        dcc.Tab(label="Analyse Dynamique", children=[
            html.Div([
                html.Label("Number of Divisions of the Interval:"),
                dcc.Slider(
                    id="bins-slider",
                    min=5, max=25, step=1, value=20,
                    marks={i: str(i) for i in range(5, 55, 5)}
                ),
                dcc.Graph(id="dynamic-roi-histogram")
            ]),

            html.Div([
                html.Label("Filter by Success:"),
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

        dcc.Tab(label="Profitability vs Ratings", children=[
            html.Div([
                html.H3("Profitability vs Ratings"),
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
                    title="Top 10 Actors with Most Film Appearances",
                    labels={"Appearances": "Number of Films", "Actor": "Actor"},
                ).update_layout(yaxis={"categoryorder": "total ascending"})
            ),
            dcc.Graph(
                id="top-actors-profitability",
                figure=px.bar(
                    top_actors_avg_profitability_df,
                    x="Avg Profitability",
                    y="Actor",
                    orientation="h",
                    title="Top 10 Actors with Highest Profitability (+8 films)",
                    labels={"Avg Profitability": "Average ROI", "Actor": "Actor"},
                ).update_layout(yaxis={"categoryorder": "total ascending"})
            ),
            dcc.Graph(
                id="top-directors",
                figure=px.bar(
                    top_directors_df,
                    x="Number of Films",
                    y="Director",
                    orientation="h",
                    title="Top 10 Directors Who Directed the Most Films",
                    labels={"Number of Films": "Number of Films Directed", "Director": "Director"},
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
                    title="Top 10 Directors with Highest Average Profitability (4+ Films)",
                    labels={"Avg Profitability": "Average ROI", "Director": "Director"},
                    color_discrete_sequence=["#FF0000"]
                ).update_layout(yaxis={"categoryorder": "total ascending"})
            )
        ]),

        dcc.Tab(label="Distribution des Durées de Films", children=[
            dcc.Graph(
                id="runtime-distribution",
                figure=px.bar(
                    runtime_counts,
                    x="Runtime (min)",
                    y="Number of Films",
                    labels={"Runtime (min)": "Durée (minutes)", "Number of Films": "Nombre de Films"},
                    title="Nombre de Films en fonction de la Durée",
                    text_auto=True
                )
            )
        ]),

        dcc.Tab(label="Profitability vs Runtime", children=[
            dcc.Graph(
                id="runtime-profitability",
                figure=px.line(
                    avg_runtime_profitability,
                    x="Runtime (min)",
                    y="Profitability (%)",
                    labels={"Runtime (min)": "Runtime Group (minutes)", "Profitability (%)": "Average Profitability (%)"},
                    title="Average Profitability vs Runtime Group",
                    markers=True
                )
            )
        ])

    ])
])

@app.callback(
    Output("dynamic-roi-histogram", "figure"),
    Input("bins-slider", "value")
)
def update_histogram(bins):
    fig = px.histogram(
        budget_vs_revenue_data, x="ROI", nbins=bins,
        labels={"ROI": "Return on Investment (ROI)"},
        title=f"Distribution of ROI (Intervals: {bins})"
    )
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
        labels={"rating": "Note", "Profitability (%)": "Rentabilité (%)"},
        title="Rentabilité vs Notes des Films",
        hover_data=["title"],
        trendline="ols"  
    )

    # Add "Moyenne" (Average Profitability) as red diamond markers
    # Round the "Moyenne Profitability (%)" values to the nearest integer
    moyenne_profitability_df["Moyenne Profitability (%)"] = moyenne_profitability_df["Moyenne Profitability (%)"].apply(
    lambda x: np.round(x) if not pd.isna(x) else x
    )
    moyenne_trace = go.Scatter(
        x=moyenne_profitability_df["rating"],
        y=moyenne_profitability_df["Moyenne Profitability (%)"],
        mode="markers",
        marker=dict(size=10, color="red", symbol="diamond"),
        name="Moyenne Profitability +10 films(appuyer pour activer/désactiver)"
    )

    fig.add_trace(moyenne_trace)

    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
