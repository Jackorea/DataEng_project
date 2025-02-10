import os
from pymongo import MongoClient

# Connexion à MongoDB
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)

# Sélection de la base de données et collection
db = client["movie_database"]
collection = db["movies"]
