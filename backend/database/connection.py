from pymongo import MongoClient

# MongoDB Atlas connection string
uri = "mongodb+srv://wavelyuser:Sjsu2025@cluster0.wootyit.mongodb.net/"

# Connect to the MongoDB cluster
client = MongoClient(uri)

# Check if the connection was successful by listing databases
print(client.list_database_names())