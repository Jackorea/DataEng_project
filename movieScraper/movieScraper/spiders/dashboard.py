import dash
from dash import dcc, html
from pymongo import MongoClient
import pandas as pd

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["movie_database"]  # Replace with your database name
collection = db["movies"]      # Replace with your collection name

# Fetch and process data
def process_movie_data():
    movies = list(collection.find({}, {"genres": 1, "rating": 1, "budget_usd": 1, "recette_usd": 1, "release_date": 1, "_id": 0}))
    
    # Prepare genres data
    genre_counts = {}
    for movie in movies:
        for genre in movie.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    # Prepare budget vs revenue data
    budget_vs_revenue = pd.DataFrame(
        [
            {
                "title": movie.get("title", "Unknown"),
                "budget": movie.get("budget_usd", 0),
                "revenue": movie.get("recette_usd", 0)
            }
            for movie in movies
        ]
    )

    # Prepare release year data
    release_years = pd.DataFrame(
        [
            {"year": movie.get("release_date", "Unknown")[-4:], "count": 1}
            for movie in movies
            if movie.get("release_date")
        ]
    ).groupby("year").count().reset_index()

    return genre_counts, budget_vs_revenue, release_years

# Process data
genres_data, budget_vs_revenue_data, release_years_data = process_movie_data()

# Create Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Dashboard des Films"),

    # Bar chart: Movies by Genre
    dcc.Graph(
        id="movies-by-genre",
        figure={
            "data": [
                {
                    "x": list(genres_data.keys()),  # Genres
                    "y": list(genres_data.values()),  # Counts
                    "type": "bar",
                    "name": "Genres"
                }
            ],
            "layout": {
                "title": "Nombre de films par genre",
                "xaxis": {"title": "Genre"},
                "yaxis": {"title": "Nombre de films"}
            }
        }
    ),

    # Bar chart: Budget vs Revenue
    dcc.Graph(
        id="budget-vs-revenue",
        figure={
            "data": [
                {
                    "x": budget_vs_revenue_data["title"],  # Movie titles
                    "y": budget_vs_revenue_data["budget"],  # Budget
                    "type": "bar",
                    "name": "Budget"
                },
                {
                    "x": budget_vs_revenue_data["title"],  # Movie titles
                    "y": budget_vs_revenue_data["revenue"],  # Revenue
                    "type": "bar",
                    "name": "Revenue"
                }
            ],
            "layout": {
                "title": "Budget vs Recette par film",
                "xaxis": {"title": "Film"},
                "yaxis": {"title": "Montant (USD)"}
            }
        }
    ),

    # Line chart: Movies Released Per Year
    dcc.Graph(
        id="movies-by-year",
        figure={
            "data": [
                {
                    "x": release_years_data["year"],  # Years
                    "y": release_years_data["count"],  # Number of movies
                    "type": "line",
                    "name": "Films par année"
                }
            ],
            "layout": {
                "title": "Nombre de films par année de sortie",
                "xaxis": {"title": "Année"},
                "yaxis": {"title": "Nombre de films"}
            }
        }
    )
])

if __name__ == "__main__":
    app.run_server(debug=True)
