# src/data_processing/features.py
import pandas as pd
from collections import Counter
from database.mongodb_connector import collection 

def get_top_actors():
    """ Retrieve the top 10 actors with the most film appearances """
    movies = list(collection.find({}, {"actors": 1, "_id": 0}))
    actor_count = Counter(actor for movie in movies for actor in movie.get("actors", []))
    
    return pd.DataFrame(actor_count.most_common(10), columns=["Actor", "Appearances"])

def get_top_directors():
    """Retrieve the top 10 directors who directed the most films."""
    movies = list(collection.find({}, {"director": 1, "_id": 0}))

    # Count occurrences of each director
    director_count = Counter(
        director.strip()  
        for movie in movies
        for director in (
            movie.get("director") if isinstance(movie.get("director"), list) 
            else [movie.get("director")] if isinstance(movie.get("director"), str) 
            else []  
        )
        if director and director.strip() 
    )

    return pd.DataFrame(director_count.most_common(10), columns=["Director", "Number of Films"])

def get_top_actors_avg_profitability():
    """ Compute the top 10 most profitable actors based on average ROI """
    movies = list(collection.find({}, {"actors": 1, "budget_usd": 1, "recette_usd": 1, "_id": 0}))

    actor_profitability = {}
    actor_counts = {}

    for movie in movies:
        budget = movie.get("budget_usd", 0) or 0  
        revenue = movie.get("recette_usd", 0) or 0  

        if budget > 0:  
            profitability = (revenue - budget) / budget 
            
            for actor in movie.get("actors", []):
                actor_profitability[actor] = actor_profitability.get(actor, 0) + profitability
                actor_counts[actor] = actor_counts.get(actor, 0) + 1

    # Filter actors with at least 8 films
    filtered_actors = {
        actor: actor_profitability[actor] / actor_counts[actor]
        for actor in actor_profitability if actor_counts[actor] >= 8
    }

    # Get top 10 most profitable actors (sorted by highest profitability)
    top_profitable_actors = sorted(filtered_actors.items(), key=lambda x: x[1], reverse=True)[:10]

    return pd.DataFrame(top_profitable_actors, columns=["Actor", "Avg Profitability"])

def get_top_directors_avg_profitability():
    """ Compute the top 10 most profitable directors based on average ROI """
    movies = list(collection.find({}, {"director": 1, "budget_usd": 1, "recette_usd": 1, "_id": 0}))

    director_profitability = {}
    director_counts = {}

    for movie in movies:
        director = movie.get("director", "Unknown")
        budget = movie.get("budget_usd", 0) or 0
        revenue = movie.get("recette_usd", 0) or 0

        if budget > 0:
            profitability = (revenue - budget) / budget

            if director in director_profitability:
                director_profitability[director] += profitability
                director_counts[director] += 1
            else:
                director_profitability[director] = profitability
                director_counts[director] = 1

    # Filter directors who have directed at least 4 films
    filtered_directors = {
        director: director_profitability[director] / director_counts[director]
        for director in director_profitability if director_counts[director] >= 4
    }

    # Get top 10 most profitable directors (sorted by highest profitability)
    top_profitable_directors = sorted(filtered_directors.items(), key=lambda x: x[1], reverse=True)[:10]

    return pd.DataFrame(top_profitable_directors, columns=["Director", "Avg Profitability"])
