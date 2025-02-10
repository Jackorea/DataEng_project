import os
import json
from pymongo import MongoClient

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)

db = client["movie_database"]
collection = db["movies"]

script_dir = os.path.dirname(os.path.abspath(__file__)) 
project_dir = os.path.abspath(os.path.join(script_dir, "../../"))  
file_path = os.path.join(project_dir, "data/output.json")  

if not os.path.exists(file_path):
    raise FileNotFoundError(f"File not found: {file_path}")

with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

if isinstance(data, list):
    for movie in data:
        collection.update_one(
            {"title": movie["title"]},
            {"$set": movie},
            upsert=True
        )

print("✅ Exportation vers MongoDB terminée !")
