#!/usr/bin/env p
import json
from pymongo import MongoClient

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27018/")
db = client["movie_database"]  # Nom de la base
collection = db["movies"]      # Nom de la collection

# Charger les données JSON
with open("output.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Insérer les données dans MongoDB
collection.insert_many(data)

print("Exportation vers MongoDB terminée !")

