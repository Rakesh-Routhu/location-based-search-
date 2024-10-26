from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from service import maps_service
import server_properties

import logger

log = logger.get_logger()

api_key = server_properties.GOOGLE_API_KEY
maps_controller = APIRouter(prefix="/maps")

# Request body models
class LocationRequest(BaseModel):
    location: str
    radius: int = 5000
    keyword: str = "restaurant"

class CoordinatesRequest(BaseModel):
    latitude: float
    longitude: float

@maps_controller.post("/nearby_restaurants")
async def nearby_restaurants(request: Request, data: LocationRequest):
    log.info(f"Finding restaurants near {data.location}...")
    if not data.location:
        raise HTTPException(status_code=400, detail="Location is required.")
    
    restaurants = maps_service.find_nearby_restaurants(api_key, data.location, data.radius, data.keyword)
    if restaurants:
        return {"restaurants": restaurants}
    else:
        return {"message": "No restaurants found."}

@maps_controller.post("/get_lat_long")
async def get_latitude_longitude(data: LocationRequest):
    log.info("Getting latitude and longitude...")
    if not data.location:
        raise HTTPException(status_code=400, detail="Location is required.")

    latitude, longitude = maps_service.get_lat_long(data.location)
    log.info(f"Got the latitude and longitude for {data.location}: {latitude}, {longitude}")

    if latitude is not None and longitude is not None:
        return {
            'location': data.location,
            'latitude': latitude,
            'longitude': longitude
        }
    else:
        raise HTTPException(status_code=404, detail="Could not find latitude and longitude for the specified location.")

@maps_controller.get("/restaurant_details/{restaurant_id}")
async def restaurant_details(restaurant_id: str):
    log.info(f"Fetching details for restaurant ID: {restaurant_id}...")
    try:
        details = maps_service.get_restaurant_details(api_key, restaurant_id)
        return {'details': details}
    except Exception as e:
        log.error(f"Error fetching restaurant details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch restaurant details.")

@maps_controller.post("/reverse_geocode")
async def reverse_geocode(data: CoordinatesRequest):
    log.info("Performing reverse geocoding...")
    if not data.latitude or not data.longitude:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required.")

    try:
        location = maps_service.reverse_geocode(data.latitude, data.longitude)
        return {'location': location}
    except Exception as e:
        log.error(f"Error in reverse geocoding: {e}")
        raise HTTPException(status_code=500, detail="Failed to find location for the specified coordinates.")

@maps_controller.get("/restaurant_reviews/{restaurant_id}")
async def restaurant_reviews(restaurant_id: str):
    log.info(f"Fetching reviews for restaurant ID: {restaurant_id}...")
    try:
        reviews = maps_service.get_restaurant_reviews(api_key, restaurant_id)
        return {'reviews': reviews}
    except Exception as e:
        log.error(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch reviews for the restaurant.")
