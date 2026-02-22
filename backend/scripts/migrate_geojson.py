from pymongo import MongoClient

# MongoDB connection string (replace with your connection details)
uri = "mongodb+srv://wavelyuser:Sjsu2025@cluster0.wootyit.mongodb.net/"
client = MongoClient(uri)

# Access the database and collection
db = client["wavelly"]
collection = db["crime_reports"]

# Update the documents to include the 'location' field in GeoJSON format
update_result = collection.update_many(
    {},
    [
        {
            "$set": {
                "location": {
                    "type": "Point",
                    "coordinates": ["$lng", "$lat"]  # Reference the 'lng' and 'lat' fields
                }
            }
        }
    ]
)

# Print the result
print(f"Matched {update_result.matched_count} documents.")
print(f"Modified {update_result.modified_count} documents.")
