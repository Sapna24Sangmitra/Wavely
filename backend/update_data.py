# STEP 1: Install dependencies
#pip install pymongo requests python-dotenv
# STEP 2: Connect to MongoDB Atlas
from pymongo import MongoClient
from datetime import datetime
import requests

# MongoDB Atlas connection
mongo_uri = "mongodb+srv://wavelyuser:Sjsu2025@cluster0.wootyit.mongodb.net/wavelly?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_uri)
db = client["wavelly"]

# STEP 2: Fetch Last 10 Years of Crime Data from SF OpenData
from datetime import datetime, timedelta

collection = db["crime_reports"]
# Get latest timestamp from DB
latest_record = collection.find_one(sort=[("timestamp", -1)])
last_time = latest_record["timestamp"].strftime("%Y-%m-%dT%H:%M:%S") 


# Socrata API query
url = "https://data.sfgov.org/resource/wg3w-h783.json"
params = {
    "$limit": 1000000,  # you can paginate if needed
    "$where": f"incident_datetime >= '{last_time}' AND latitude IS NOT NULL AND longitude IS NOT NULL"
}

response = requests.get(url, params=params)
data = response.json()
print(f"✅ Fetched {len(data)} records from the last 10 years")

# STEP 3: Format data into MongoDB-ready documents
formatted_docs = []
for item in data:
    try:
        doc = {
            "timestamp": datetime.fromisoformat(item["incident_datetime"]),
            "category": item.get("incident_category"),
            "subcategory": item.get("incident_subcategory"),
            "description": item.get("incident_description"),
            "lat": float(item["latitude"]),
            "lng": float(item["longitude"]),
            "neighborhood": item.get("analysis_neighborhood"),
            "district": item.get("police_district"),
            "resolution": item.get("resolution")
        }
        formatted_docs.append(doc)
    except Exception:
        continue  # Skip bad rows

print(f"🧹 Prepared {len(formatted_docs)} documents for insertion.")

# STEP 4: Insert into MongoDB in chunks
def insert_in_chunks(data, chunk_size=1000):
    inserted = 0
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        try:
            collection.insert_many(chunk, ordered=False)
            inserted += len(chunk)
            print(f"✅ Inserted chunk {i//chunk_size + 1}: {len(chunk)}")
        except Exception as e:
            print(f"⚠️ Error in chunk {i//chunk_size + 1}: {e}")
    print(f"\n🎉 Total inserted: {inserted} records into 'crime_reports'")

# Run the insert
insert_in_chunks(formatted_docs)

