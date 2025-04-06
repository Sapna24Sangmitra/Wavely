from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pymongo import MongoClient

# MongoDB setup
uri = "mongodb+srv://wavelyuser:Sjsu2025@cluster0.wootyit.mongodb.net/"
client = MongoClient(uri)
db = client["wavelly"]
crime_collection = db["crime_reports"]
light_collection = db["street_lighting"]
institution_collection = db["institutions"]

app = FastAPI()

class Location(BaseModel):
    lat: float
    lng: float

class Step(BaseModel):
    start_location: Location
    end_location: Location
    html_instructions: str
    travel_mode: str
    maneuver: Optional[str] = None

class Leg(BaseModel):
    steps: List[Step]

class Route(BaseModel):
    legs: List[Leg]

class GoogleMapsResponse(BaseModel):
    routes: List[Route]

@app.post("/calculate_route_scores")
async def calculate_route_scores(google_maps_response: GoogleMapsResponse):
    print("Received request to calculate route scores.")
    route_scores = []

    for idx, route in enumerate(google_maps_response.routes):
        print(f"Calculating safety score for route {idx+1}...")
        total_score = 0
        total_steps = 0

        for leg in route.legs:
            for step in leg.steps:
                start_lat, start_lng = step.start_location.lat, step.start_location.lng
                end_lat, end_lng = step.end_location.lat, step.end_location.lng

                # Get crime-based safety score (higher crimes => higher score => less safe)
                crime_score = get_crime_score((start_lat, start_lng), (end_lat, end_lng))

                # Get lighting-based safety score (more light => higher score => safer)
                lighting_score = get_lighting_score((start_lat, start_lng), (end_lat, end_lng))

                # Get institution-based safety score (presence of institutions => safer)
                institution_score = get_institution_score((start_lat, start_lng), (end_lat, end_lng))

                # Combine with weighted score
                combined_score = (0.6 * crime_score) + (0.2 * lighting_score) + (0.2 * institution_score)
                total_score += combined_score
                total_steps += 1

        avg_score = total_score / total_steps if total_steps else 0
        route_scores.append({"route_id": f"route{idx+1}", "safety_score": round(avg_score, 2)})

    return {"route_scores": route_scores}

def get_crime_score(start, end, radius_miles=0.5):
    lat = (start[0] + end[0]) / 2
    lng = (start[1] + end[1]) / 2
    radius_meters = radius_miles * 1609.34

    pipeline = [
        {"$geoNear": {
            "near": {"type": "Point", "coordinates": [lng, lat]},
            "distanceField": "dist.calculated",
            "maxDistance": radius_meters,
            "spherical": True
        }},
        {"$count": "crime_count"}
    ]

    result = list(crime_collection.aggregate(pipeline))
    count = result[0]['crime_count'] if result else 0
    score = min(count * 0.1, 100)
    print(f"Crime score for ({lat}, {lng}): {score} from {count} crimes")
    return score

def get_lighting_score(start, end, radius_miles=0.05):
    lat = (start[0] + end[0]) / 2
    lng = (start[1] + end[1]) / 2
    radius_meters = radius_miles * 1609.34

    pipeline = [
        {"$geoNear": {
            "near": {"type": "Point", "coordinates": [lng, lat]},
            "distanceField": "dist.calculated",
            "maxDistance": radius_meters,
            "spherical": True
        }}
    ]

    results = list(light_collection.aggregate(pipeline))

    if not results:
        print(f"No lighting found for ({lat}, {lng}). Score: 0")
        return 0

    total_brightness = 0
    count = 0
    for light in results:
        if light.get("status") == "working":
            total_brightness += light.get("brightness", 0)
            count += 1

    if count == 0:
        print(f"All lights broken at ({lat}, {lng}). Score: 0")
        return 0

    avg_brightness = total_brightness / count
    print(f"Lighting score for ({lat}, {lng}): {avg_brightness}")
    return min(avg_brightness, 100)

def get_institution_score(start, end, radius_miles=0.25):
    lat = (start[0] + end[0]) / 2
    lng = (start[1] + end[1]) / 2
    radius_meters = radius_miles * 1609.34

    pipeline = [
        {"$geoNear": {
            "near": {"type": "Point", "coordinates": [lng, lat]},
            "distanceField": "dist.calculated",
            "maxDistance": radius_meters,
            "spherical": True
        }},
        {"$limit": 1}
    ]

    result = list(institution_collection.aggregate(pipeline))

    if result:
        print(f"Institution found near ({lat}, {lng}). Score: 100")
        return 100
    else:
        print(f"No institution near ({lat}, {lng}). Score: 0")
        return 0
