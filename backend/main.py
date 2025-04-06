from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from geopy.distance import geodesic
from pymongo import MongoClient

# MongoDB setup (replace this with your connection details)
uri = "mongodb+srv://wavelyuser:Sjsu2025@cluster0.wootyit.mongodb.net/"
client = MongoClient(uri)

# Access the database and collection
db = client["wavelly"]
collection = db["crime_reports"]

# FastAPI app definition
app = FastAPI()

# Pydantic models for input validation
class GeocodedWaypoint(BaseModel):
    geocoder_status: str
    place_id: str
    types: List[str]

class Distance(BaseModel):
    text: str
    value: int

class Duration(BaseModel):
    text: str
    value: int

class Location(BaseModel):
    lat: float
    lng: float

class Step(BaseModel):
    distance: Distance
    duration: Duration
    end_location: Location
    html_instructions: str
    polyline: Optional[dict]
    start_location: Location
    travel_mode: str
    maneuver: Optional[str] = None  # Explicitly set it as Optional and default to None

class Leg(BaseModel):
    distance: Distance
    duration: Duration
    end_address: str
    end_location: Location
    start_address: str
    start_location: Location
    steps: List[Step]

class Route(BaseModel):
    bounds: dict
    copyrights: str
    legs: List[Leg]
    overview_polyline: dict
    summary: str
    warnings: List[str]
    waypoint_order: List[int]

class GoogleMapsResponse(BaseModel):
    geocoded_waypoints: List[GeocodedWaypoint]
    routes: List[Route]
    status: str

# Helper function to calculate safety score for a leg (street)
def calculate_leg_safety_score(lat, lng):
    print(f"Checking safety for coordinates: Latitude: {lat}, Longitude: {lng}")

    # Query MongoDB for crimes near the given latitude and longitude
    crimes_found = get_nearby_crime_count(lat, lng)
    
    if crimes_found == 0:
        # No crimes found, considered a safe leg
        print("No crimes found, this is a safe leg.")
        return 100  # Safe leg gets a high score (100)
    else:
        # Crimes found, calculate a safety score
        safety_score = min(crimes_found * 0.1, 100)  # Adjust the multiplier as needed
        print(f"Found {crimes_found} crimes, calculated safety score: {safety_score}")
        return safety_score

# Function to query MongoDB for nearby crimes efficiently using aggregation
def get_nearby_crime_count(lat, lng, radius=0.5):
    print(f"Querying MongoDB for crimes near latitude: {lat}, longitude: {lng} with radius: {radius} miles")
    
    # Convert radius from miles to meters (MongoDB uses meters for geo queries)
    radius_meters = radius * 1609.34  # 1 mile = 1609.34 meters

    # Use MongoDB aggregation to efficiently count crimes within the radius using $geoNear
    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [lng, lat]  # longitude, latitude
                },
                "distanceField": "distance",
                "maxDistance": radius_meters,
                "spherical": True
            }
        },
        {
            "$count": "total_crimes"  # Count the number of matching crimes
        }
    ]
    
    result = list(collection.aggregate(pipeline))
    
    if result:
        crime_count = result[0].get("total_crimes", 0)
        return crime_count
    else:
        return 0

# Helper function to calculate overall route safety score
def calculate_route_safety_score(route_steps: List[dict]):
    total_score = 0
    num_legs = len(route_steps)

    # Calculate the safety score for each leg (street)
    for step in route_steps:
        start_lat, start_lng = step["start_lat"], step["start_lng"]
        end_lat, end_lng = step["end_lat"], step["end_lng"]

        # Calculate score for start and end locations of the step
        start_score = calculate_leg_safety_score(start_lat, start_lng)
        end_score = calculate_leg_safety_score(end_lat, end_lng)

        # Average the scores for the leg
        leg_score = (start_score + end_score) / 2
        total_score += leg_score

    # Average the total score across all legs
    route_safety_score = total_score / num_legs
    print(f"Total route safety score: {route_safety_score}")
    return route_safety_score

# API endpoint to calculate route scores
@app.post("/calculate_route_scores")
async def calculate_route_scores(google_maps_response: GoogleMapsResponse):
    print("Received request to calculate route scores.")
    try:
        routes = google_maps_response.routes
        if not routes:
            raise HTTPException(status_code=400, detail="No routes found in the Google Maps response")

        route_scores = []

        print(f"Processing {len(routes)} routes...")
        for route_index, route in enumerate(routes):
            route_id = f"route{route_index + 1}"
            route_steps = []

            for leg in route.legs:
                for step in leg.steps:
                    start_location = step.start_location
                    end_location = step.end_location
                    route_steps.append({
                        "start_lat": start_location.lat,
                        "start_lng": start_location.lng,
                        "end_lat": end_location.lat,
                        "end_lng": end_location.lng,
                        "instructions": step.html_instructions
                    })

            print(f"Calculating safety score for route {route_id}...")
            safety_score = calculate_route_safety_score(route_steps)
            route_scores.append({"route_id": route_id, "safety_score": safety_score})

        print("Finished processing all routes.")
        return {"route_scores": route_scores}

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
