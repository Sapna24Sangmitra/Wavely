from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import motor.motor_asyncio
import copy
import json
import asyncio
from datetime import datetime

# MongoDB setup with motor (async driver)
uri = "mongodb+srv://wavelyuser:Sjsu2025@cluster0.wootyit.mongodb.net/"
client = motor.motor_asyncio.AsyncIOMotorClient(uri)
db = client["wavelly"]
crime_collection = db["crime_reports"]
light_collection = db["street_lighting"]
institution_collection = db["institutions"]
foot_traffic_collection = db["foot_traffic"]
user_incident_collection = db["user_incident_report"]

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://wavelly.tech", "https://wavelly.tech", "http://www.wavelly.tech", "https://www.wavelly.tech"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class Location(BaseModel):
    lat: float
    lng: float

class Step(BaseModel):
    start_location: Location
    end_location: Location
    html_instructions: Optional[str] = None
    travel_mode: str
    maneuver: Optional[str] = None

class Leg(BaseModel):
    steps: List[Step]
    duration: Optional[Dict[str, Any]] = None
    distance: Optional[Dict[str, Any]] = None
    start_location: Optional[Location] = None
    end_location: Optional[Location] = None
    start_address: Optional[str] = None
    end_address: Optional[str] = None

class Route(BaseModel):
    legs: List[Leg]
    summary: Optional[str] = None
    overview_polyline: Optional[Union[str, Dict[str, Any]]] = None
    safety_score: Optional[float] = None

class GoogleMapsResponse(BaseModel):
    routes: List[Route]
    
    class Config:
        extra = "allow"  # Allow extra fields in the model

class Coordinates(BaseModel):
    latitude: float
    longitude: float

class LocationInfo(BaseModel):
    name: str
    coordinates: Coordinates

class IncidentReport(BaseModel):
    description: str
    location: LocationInfo
    timestamp: str

@app.post("/calculate_route_scores")
async def calculate_route_scores(google_maps_response: GoogleMapsResponse):
    try:
        print("Received request to calculate route scores.")
        print(f"Number of routes: {len(google_maps_response.routes)}")
        
        # Create tasks for each route to process them concurrently
        tasks = []
        for idx, route in enumerate(google_maps_response.routes):
            tasks.append(process_route(idx, route))
        
        # Wait for all routes to be processed
        enriched_routes = await asyncio.gather(*tasks)
        
        return {
            "routes": enriched_routes
        }
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

async def process_route(idx, route):
    """Process a single route asynchronously"""
    print(f"Calculating safety score for route {idx+1}...")
    print(f"Route has {len(route.legs)} legs")
    
    total_score = 0
    total_steps = 0
    
    # Create tasks for each leg to process them concurrently
    leg_tasks = []
    for leg_idx, leg in enumerate(route.legs):
        leg_tasks.append(process_leg(idx, leg_idx, leg))
    
    # Wait for all legs to be processed
    leg_results = await asyncio.gather(*leg_tasks)
    
    # Sum up the results
    for score, steps in leg_results:
        total_score += score
        total_steps += steps
    
    avg_score = total_score / total_steps if total_steps else 0
    route_score = round(avg_score, 2)
    
    # Create a deep copy of the original route to preserve all parameters
    enriched_route = copy.deepcopy(route.dict())
    
    # Add the safety score to the route
    enriched_route["safety_score"] = route_score
    
    # Log the original route keys for debugging
    print(f"Original route {idx+1} keys: {list(route.dict().keys())}")
    print(f"Enriched route {idx+1} keys: {list(enriched_route.keys())}")
    
    # Ensure all original fields are preserved
    if "overview_polyline" not in enriched_route:
        enriched_route["overview_polyline"] = None
        
    if "legs" not in enriched_route:
        enriched_route["legs"] = []
    
    # Ensure duration information is preserved for each leg
    if route.legs:
        for leg_idx, leg in enumerate(route.legs):
            # Check if the leg has a duration attribute
            if hasattr(leg, 'duration'):
                # Access the text key from the duration dictionary
                duration_text = leg.duration.get('text', 'Duration unknown')
                print(f"Route {idx+1}, Leg {leg_idx+1} duration: {duration_text}")
                
                # Make sure the duration is properly copied to the enriched route
                if "legs" in enriched_route and len(enriched_route["legs"]) > leg_idx:
                    if "duration" not in enriched_route["legs"][leg_idx]:
                        enriched_route["legs"][leg_idx]["duration"] = leg.duration
                    else:
                        # Ensure the duration has the text property
                        if "text" not in enriched_route["legs"][leg_idx]["duration"]:
                            enriched_route["legs"][leg_idx]["duration"]["text"] = duration_text
    
    return enriched_route

async def process_leg(route_idx, leg_idx, leg):
    """Process a single leg asynchronously"""
    print(f"  Processing leg {leg_idx+1} with {len(leg.steps)} steps")
    
    total_score = 0
    total_steps = 0
    
    # Create tasks for each step to process them concurrently
    step_tasks = []
    for step_idx, step in enumerate(leg.steps):
        step_tasks.append(process_step(route_idx, leg_idx, step_idx, step))
    
    # Wait for all steps to be processed
    step_results = await asyncio.gather(*step_tasks)
    
    # Sum up the results
    for score in step_results:
        total_score += score
        total_steps += 1
    
    return total_score, total_steps

async def process_step(route_idx, leg_idx, step_idx, step):
    """Process a single step asynchronously"""
    print(f"    Processing step {step_idx+1}")
    print(f"    Start location: {step.start_location.lat}, {step.start_location.lng}")
    print(f"    End location: {step.end_location.lat}, {step.end_location.lng}")
    
    start_lat, start_lng = step.start_location.lat, step.start_location.lng
    end_lat, end_lng = step.end_location.lat, step.end_location.lng
    
    # Create tasks for each component score to calculate them concurrently
    score_tasks = [
        get_crime_score((start_lat, start_lng), (end_lat, end_lng)),
        get_lighting_score((start_lat, start_lng), (end_lat, end_lng)),
        get_institution_score((start_lat, start_lng), (end_lat, end_lng)),
        get_foot_traffic_score((start_lat, start_lng), (end_lat, end_lng))
    ]
    
    # Wait for all scores to be calculated
    crime_score, lighting_score, institution_score, foot_traffic_score = await asyncio.gather(*score_tasks)
    
    # Combine with weighted score
    combined_score = (
        (0.45 * crime_score) +
        (0.3 * foot_traffic_score) +
        (0.15 * lighting_score) +
        (0.1 * institution_score)
    )
    
    return combined_score

async def get_crime_score(start, end, radius_miles=0.5):
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

    result = await crime_collection.aggregate(pipeline).to_list(length=1)
    count = result[0]['crime_count'] if result else 0
    score = min(count * 0.1, 100)
    print(f"Crime score for ({lat}, {lng}): {score} from {count} crimes")
    return score

async def get_lighting_score(start, end, radius_miles=0.05):
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

    results = await light_collection.aggregate(pipeline).to_list(length=None)

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

async def get_institution_score(start, end, radius_miles=0.25):
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

    result = await institution_collection.aggregate(pipeline).to_list(length=1)

    if result:
        print(f"Institution found near ({lat}, {lng}). Score: 100")
        return 100
    else:
        print(f"No institution near ({lat}, {lng}). Score: 0")
        return 0

async def get_foot_traffic_score(start, end, radius_miles=0.1):
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
        {"$group": {
            "_id": None,
            "total_foot_traffic": {"$sum": "$count"}
        }}
    ]

    result = await foot_traffic_collection.aggregate(pipeline).to_list(length=1)

    if result:
        score = min(result[0]['total_foot_traffic'], 100)
        print(f"Foot traffic score for ({lat}, {lng}): {score}")
        return score
    else:
        print(f"No foot traffic data for ({lat}, {lng}). Score: 50")
        return 50

@app.post("/debug_request")
async def debug_request(request: Request):
    """Debug endpoint to inspect the raw request data"""
    try:
        body = await request.json()
        return {
            "received_data": body,
            "data_type": str(type(body)),
            "routes_count": len(body.get("routes", [])),
            "sample_route": body.get("routes", [{}])[0] if body.get("routes") else None
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/submit_incident_report")
async def submit_incident_report(report: IncidentReport):
    try:
        print(f"Received incident report: {report.description}")
        
        # Convert the report to a dictionary
        report_dict = report.dict()
        
        # Add a created_at timestamp
        report_dict["created_at"] = datetime.now()
        
        # Add a GeoJSON point for the location with lat and long keys
        report_dict["location"]["coordinates"] = {
            "type": "Point",
            "coordinates": {
                "lat": report_dict["location"]["coordinates"]["latitude"],
                "long": report_dict["location"]["coordinates"]["longitude"]
            }
        }
        
        # Insert the report into the database
        result = await user_incident_collection.insert_one(report_dict)
        
        print(f"Incident report saved with ID: {result.inserted_id}")
        
        return {"status": "success", "message": "Incident report submitted successfully"}
    except Exception as e:
        print(f"Error submitting incident report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting incident report: {str(e)}")
