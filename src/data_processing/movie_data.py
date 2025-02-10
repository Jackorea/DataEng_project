# src/data_processing/movie_data.py
import pandas as pd
import numpy as np
import re
from database.mongodb_connector import collection
from statsmodels.tsa.holtwinters import ExponentialSmoothing

def load_movies():
    """ Load movie data from MongoDB """
    return list(collection.find({}, {
        "title": 1, "genres": 1, "rating": 1,
        "budget_usd": 1, "recette_usd": 1, "release_date": 1, "runtime": 1, "_id": 0
    }))

def count_movie_genres(movies):
    """ Count occurrences of movie genres """
    genre_counts = {}
    for movie in movies:
        for genre in movie.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    return genre_counts

def extract_release_years(movies):
    """ Extract release years from movie data """
    release_years = []
    for movie in movies:
        release_date = movie.get("release_date", "")
        match = re.search(r"\b(19\d{2}|20\d{2})\b", release_date)
        if match:
            release_years.append({"year": int(match.group(0)), "count": 1})
    
    if release_years:
        return pd.DataFrame(release_years).groupby("year").count().reset_index()
    return pd.DataFrame(columns=["year", "count"])

def compute_roi(budget_vs_revenue):
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
        budget_vs_revenue["Success"] = budget_vs_revenue["ROI"].apply(
            lambda roi: "Rentable" if pd.notna(roi) and roi >= 1 else "Non Rentable" if pd.notna(roi) else "Inconnu"
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
        roi_category_counts.columns = ["ROI Category", "Count"]

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

    return budget_vs_revenue, roi_category_counts, moyenne_profitability_df


def compute_runtime_statistics(movies):
    """Process runtime statistics and profitability vs runtime"""

    def parse_runtime(runtime_str):
        """Convert runtime string (e.g., '2h 41m') into minutes"""
        if not isinstance(runtime_str, str) or not runtime_str.strip():
            return np.nan
        hours_match = re.search(r"(\d+)h", runtime_str)
        minutes_match = re.search(r"(\d+)m", runtime_str)
        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0
        return hours * 60 + minutes

    # Extract runtimes
    runtimes = [parse_runtime(movie.get("runtime", "")) for movie in movies if movie.get("runtime")]

    # Compute runtime distribution
    if runtimes:
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
        budget = movie.get("budget_usd", 0) or 0
        revenue = movie.get("recette_usd", 0) or 0

        if pd.notna(runtime) and isinstance(budget, (int, float)) and budget > 0:
            profitability = ((revenue - budget) / budget) * 100  # Profitability in %
            runtime_rounded = round(runtime, -1)  # Round to nearest 10 minutes
            runtime_profitability_data.append({"Runtime (min)": runtime_rounded, "Profitability (%)": profitability})

    # Ensure DataFrame has correct columns
    if runtime_profitability_data:
        avg_runtime_profitability = pd.DataFrame(runtime_profitability_data)
        avg_runtime_profitability = avg_runtime_profitability.groupby("Runtime (min)")["Profitability (%)"].mean().reset_index()
    else:
        avg_runtime_profitability = pd.DataFrame(columns=["Runtime (min)", "Profitability (%)"])

    return runtime_counts, avg_runtime_profitability

def compute_genre_ratings(movies):
    """ Calcule la moyenne des ratings pour chaque genre """
    genre_ratings = {}
    genre_counts = {}

    for movie in movies:
        rating = movie.get("rating", None)
        if rating is not None and isinstance(rating, (int, float)):  # Vérifie que le rating est valide
            for genre in movie.get("genres", []):
                if genre in genre_ratings:
                    genre_ratings[genre] += rating
                    genre_counts[genre] += 1
                else:
                    genre_ratings[genre] = rating
                    genre_counts[genre] = 1

    # Calcul correct de la moyenne
    average_genre_ratings = {genre: genre_ratings[genre] / genre_counts[genre] for genre in genre_ratings if genre_counts[genre] > 0}

    return average_genre_ratings

def process_movie_data():
    movies = load_movies()

    budget_vs_revenue = pd.DataFrame([
        {
            "title": movie.get("title", "Unknown"),
            "budget": movie.get("budget_usd", 0),
            "revenue": movie.get("recette_usd", 0),
            "rating": movie.get("rating", None),
            "director": movie.get("director", "Unknown"),
            "actors": movie.get("actors", [])
        }
        for movie in movies if "budget_usd" in movie and "recette_usd" in movie
    ])

    budget_vs_revenue, roi_category_counts, moyenne_profitability_df = compute_roi(budget_vs_revenue)
    
    genre_counts = count_movie_genres(movies)
    release_years_data = extract_release_years(movies)
    runtime_counts, avg_runtime_profitability = compute_runtime_statistics(movies)
    average_genre_ratings = compute_genre_ratings(movies)
    sorted_average_genre_ratings = dict(sorted(average_genre_ratings.items(), key=lambda item: item[1]))
    
    return (genre_counts, budget_vs_revenue, release_years_data, sorted_average_genre_ratings, 
            roi_category_counts, moyenne_profitability_df, runtime_counts, avg_runtime_profitability)

