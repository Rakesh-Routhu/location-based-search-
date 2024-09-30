from flask import Blueprint, request, jsonify
import server_properties
from service import maps_service

import logger

log = logger.get_logger()

api_key = server_properties.GOOGLE_API_KEY
maps_controller = Blueprint('maps_controller', __name__,url_prefix='/maps')


@maps_controller.route('/nearby_restaurants', methods=['POST'])
def nearby_restaurants():
    data = request.get_json()
    location = data.get('location')
    radius = int(data.get('radius', 5000))
    keyword = data.get('keyword', 'restaurant')
    log.info(f"Finding restaurants near {location}...")

    if not location:
        return jsonify({'error': 'Location is required.'}), 400
    restaurants = maps_service.find_nearby_restaurants(api_key, location, radius, keyword)
    if restaurants:
        return jsonify({'restaurants': restaurants}), 200
    else:
        return jsonify({'message': 'No restaurants found.'}), 200
    

@maps_controller.route('/get_lat_long', methods=['POST'])
def get_latitude_longitude():
    log.info("Getting latitude and longitude...")
    data = request.get_json()
    location = data.get('location')

    if not location:
        return jsonify({'error': 'Location is required.'}), 400

    latitude, longitude = maps_service.get_lat_long(location)
    log.info(f"Got the latitude and longitude for {location}: {latitude}, {longitude}")

    if latitude is not None and longitude is not None:
        return jsonify({
            'location': location,
            'latitude': latitude,
            'longitude': longitude
        }), 200
    else:
        return jsonify({'error': 'Could not find latitude and longitude for the specified location.'}), 404


@maps_controller.route('/restaurant_details/<string:restaurant_id>', methods=['GET'])
def restaurant_details(restaurant_id):
    log.info(f"Fetching details for restaurant ID: {restaurant_id}...")
    try:
        details = maps_service.get_restaurant_details(api_key, restaurant_id)
        return jsonify({'details': details}), 200
    except Exception as e:
        log.error(f"Error fetching restaurant details: {e}")
        return jsonify({'error': 'Failed to fetch restaurant details.'}), 500


@maps_controller.route('/reverse_geocode', methods=['POST'])
def reverse_geocode():
    log.info("Performing reverse geocoding...")
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not latitude or not longitude:
        return jsonify({'error': 'Latitude and longitude are required.'}), 400

    try:
        location = maps_service.reverse_geocode(latitude, longitude)
        return jsonify({'location': location}), 200
    except Exception as e:
        log.error(f"Error in reverse geocoding: {e}")
        return jsonify({'error': 'Failed to find location for the specified coordinates.'}), 500


@maps_controller.route('/restaurant_reviews/<string:restaurant_id>', methods=['GET'])
def restaurant_reviews(restaurant_id):
    log.info(f"Fetching reviews for restaurant ID: {restaurant_id}...")
    try:
        reviews = maps_service.get_restaurant_reviews(api_key, restaurant_id)
        return jsonify({'reviews': reviews}), 200
    except Exception as e:
        log.error(f"Error fetching reviews: {e}")
        return jsonify({'error': 'Failed to fetch reviews for the restaurant.'}), 500