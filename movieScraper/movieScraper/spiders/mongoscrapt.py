# how to verify that the data has been successfully inserted:
#mongosh --host localhost --port 27017
#use movie_database
#db.movies.find().pretty()

#!/usr/bin/env python3
import json
from pymongo import MongoClient

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["movie_database"]  # Nom de la base
collection = db["movies"]      # Nom de la collection

# Charger les données JSON
with open("output.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Insérer les données dans MongoDB (éviter les doublons)
if isinstance(data, list):  # Vérifier si le JSON est une liste
    for movie in data:
        # Utiliser un filtre pour éviter les doublons basés sur le titre
        collection.update_one(
            {"title": movie["title"]},  # Critère pour détecter les doublons
            {"$set": movie},            # Met à jour ou insère les données
            upsert=True                 # Insère si le document n'existe pas
        )

print("Exportation vers MongoDB terminée !")
