import requests
import server_properties
from helper import utility

import logger

log = logger.get_logger()

api_key = server_properties.GOOGLE_API_KEY

def find_nearby_restaurants(api_key, location, radius=5000, keyword='restaurant'):
    log.info("Inside find_nearby_restaurants")
    latitude, longitude = get_lat_long(location)
    if latitude is None or longitude is None:
        log.error("Failed to get latitude and longitude.")
        return []
    location = f"{latitude},{longitude}"
    log.info(f"Finding restaurants near {location}...")
    url = utility.build_places_url(location, radius, keyword)
    response = requests.get(url,verify=False)

    log.info("Response Status Code: %s", response.status_code) 
    response_data = response.json()
    log.info("Response Data:", response_data)
    if response.status_code == 200 and 'results' in response_data:
        results = response_data['results']
        if results:
            restaurants = []
            for place in results:
                restaurant_info = {
                    'name': place.get('name'),
                    'address': place.get('vicinity'),
                    'rating': place.get('rating'),
                    'id': place.get('place_id')
                }
                restaurants.append(restaurant_info)
            sorted_data = sorted(restaurants, key=lambda x: x['rating'], reverse=True)

            return sorted_data
        else:
            log.info("Found 0 restaurants.")
            return []
    else:
        log.error(f"Error: {response_data.get('error_message', 'Unknown error')}")
        return []

def get_lat_long(location):
    url = server_properties.GOOGLE_GEOCODE_API_BASE_URL
    params = {
        'address': location,
        'key': api_key
    }
    response = requests.get(url, params=params,verify=False)
    log.info("Response Status Code: %s", response.status_code)
    data = response.json()
    log.info("Response Data:", data)

    if response.status_code == 200 and 'results' in data and data['results']:
        latitude = data['results'][0]['geometry']['location']['lat']
        longitude = data['results'][0]['geometry']['location']['lng']
        return latitude, longitude
    else:
        return None, None
    
def get_restaurant_details(api_key, restaurant_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={restaurant_id}&key={api_key}"
    response = requests.get(url,verify=False)
    if response.status_code == 200:
        return response.json().get('result', {})
    else:
        raise Exception(f"Error fetching restaurant details: {response.content}")


def reverse_geocode(latitude, longitude):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={api_key}"
    response = requests.get(url,verify=False)
    if response.status_code == 200:
        result = response.json().get('results', [])
        if result:
            return result[0].get('formatted_address')
        else:
            raise Exception("Coordinates not found.")
    else:
        raise Exception(f"Error in reverse geocoding: {response.content}")


def get_restaurant_reviews(api_key, restaurant_id):
    details = get_restaurant_details(api_key, restaurant_id)
    if 'reviews' in details:
        return details['reviews']
    else:
        return []