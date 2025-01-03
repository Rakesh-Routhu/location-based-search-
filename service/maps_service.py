from fastapi import HTTPException
import requests
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import server_properties
import logger
from helper import utility

log = logger.get_logger()

api_key = server_properties.GOOGLE_API_KEY
# Elasticsearch connection configuration
es = Elasticsearch(
    hosts=[server_properties.ES_HOST],
    http_auth=(server_properties.ES_USER, server_properties.ES_PASSWORD)
)

def get_lat_long(location):
    url = server_properties.GOOGLE_GEOCODE_API_BASE_URL
    params = {'address': location, 'key': api_key}
    response = requests.get(url, params=params, verify=False)
    log.info("Response Status Code: %s", response.status_code)
    data = response.json()

    if response.status_code == 200 and 'results' in data and data['results']:
        latitude = data['results'][0]['geometry']['location']['lat']
        longitude = data['results'][0]['geometry']['location']['lng']
        return latitude, longitude
    else:
        return None, None

def find_nearby_restaurants(api_key, location, radius=5000, keyword='restaurant'):
    log.info("Inside find_nearby_restaurants")

    # First, try to get latitude and longitude for the given location
    latitude, longitude = get_lat_long(location)
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Error while fetching latitude or longitude")

    # Check if nearby restaurants are cached in Elasticsearch
    cached_restaurants = get_cached_nearby_restaurants(latitude, longitude, radius)
    if cached_restaurants:
        log.info("Found cached restaurants.")
        return cached_restaurants

    # If no cached restaurants, fetch from Google API
    location_str = f"{latitude},{longitude}"
    log.info(f"Fetching nearby restaurants from Google API near {location_str}...")
    url = utility.build_places_url(location_str, radius, keyword)
    response = requests.get(url, verify=False)

    log.info("Response Status Code: %s", response.status_code)
    response_data = response.json()

    if response.status_code == 200 and 'results' in response_data:
        results = response_data['results']
        if results:
            restaurants = []
            for place in results:
                restaurant_info = {
                    'name': place.get('name'),
                    'address': place.get('vicinity'),
                    'rating': place.get('rating'),
                    'id': place.get('place_id'),
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius': radius
                }
                restaurants.append(restaurant_info)

            # Store the fetched restaurants in Elasticsearch for future use
            store_nearby_restaurants(restaurants, latitude, longitude, radius)

            # Return sorted restaurants by rating (high to low)
            sorted_data = sorted(restaurants, key=lambda x: x['rating'], reverse=True)
            return sorted_data
        else:
            log.info("Found 0 restaurants.")
            return []
    else:
        log.error(f"Error fetching restaurants: {response_data.get('error_message', 'Unknown error')}")
        return []

# Helper method to fetch cached restaurants from Elasticsearch
def get_cached_nearby_restaurants(latitude, longitude, radius):
    index_name = "restaurants"
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"latitude": latitude}},
                    {"match": {"longitude": longitude}},
                    {"match": {"radius": radius}}
                ]
            }
        }
    }
    response = es.search(index=index_name, body=query)
    if response['hits']['total']['value'] > 0:
        restaurants = [hit['_source'] for hit in response['hits']['hits']]
        log.info("Returning cached restaurants.")
        return restaurants
    else:
        return []
def store_nearby_restaurants(restaurant_data, latitude, longitude, radius):
    index_name = "restaurants"
    actions = []
    
    # Prepare actions for the bulk API
    for restaurant in restaurant_data:
        # Add the additional fields for latitude, longitude, and radius
        restaurant['latitude'] = latitude
        restaurant['longitude'] = longitude
        restaurant['radius'] = radius

        # Prepare the document action for the bulk API
        action = {
            "_op_type": "index",  # Operation type: "index" means create or replace
            "_index": index_name,
            "_source": restaurant
        }
        actions.append(action)
    
    # Perform the bulk insert into Elasticsearch
    if actions:
        success, failed = bulk(es, actions)
        log.info(f"Bulk insert completed. {success} documents indexed, {failed} failed.")
    else:
        log.info("No restaurants to index.")

def get_restaurant_details(api_key, restaurant_id):
    # First, check if restaurant details are already cached in Elasticsearch
    cached_details = get_cached_restaurant_details(restaurant_id)
    if cached_details:
        log.info(f"Found cached details for restaurant ID: {restaurant_id}")
        return cached_details
    
    # If not cached, fetch the details from Google Places API
    log.info(f"Fetching details for restaurant ID: {restaurant_id} from Google API...")
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={restaurant_id}&key={api_key}"
    response = requests.get(url, verify=False)

    if response.status_code == 200:
        details = response.json().get('result', {})
        
        # Store the fetched details in Elasticsearch for future use
        store_restaurant_details(details)
        
        return details
    else:
        log.error(f"Error fetching details for restaurant ID {restaurant_id}: {response.content}")
        return {}
    

def store_restaurant_details(restaurant_details):
    # Index the restaurant details in Elasticsearch
    index_name = "restaurants_details"
    restaurant_id = restaurant_details.get('place_id')
    if restaurant_id:
        es.index(index=index_name, id=restaurant_id, document=restaurant_details)
        log.info(f"Stored restaurant details for {restaurant_id} in Elasticsearch.")

# Get restaurant details from Elasticsearch (cached)
def get_cached_restaurant_details(restaurant_id):
    index_name = "restaurants_details"
    query = {
        "query": {
            "match": {
                "restaurant_id": restaurant_id
            }
        }
    }
    response = es.search(index=index_name, body=query)
    if response['hits']['total']['value'] > 0:
        return response['hits']['hits'][0]['_source']
    else:
        return None

# Store reviews in Elasticsearch
def store_user_review(review_data):
    index_name = "user_reviews"
    response = es.index(index=index_name, document=review_data)
    log.info(f"Stored review for user {review_data['user_id']} at restaurant {review_data['restaurant_id']}.")
    return response

def fetch_restaurant_reviews(api_key, restaurant_id):
    # Fetch restaurant details using the existing method
    result = get_restaurant_details(api_key, restaurant_id)
    log.info("Response received from get_restaurant_details method", result)

    # Extract the relevant data
    if 'reviews' in result and result['reviews']:
        reviews_data = []
        
        # Collect reviews
        for review in result['reviews']:
            review_info = {
                'user_name': review.get('author_name'),
                'rating': review.get('rating'),
                'text': review.get('text')
            }
            reviews_data.append(review_info)
        
        # Return the data: total ratings count and the reviews list
        return {
            'total_ratings_count': result.get('user_ratings_total', 0),
            'reviews': reviews_data
        }
    else:
        return {
            'total_ratings_count': 0,
            'reviews': []
        }


# Store restaurant reviews in Elasticsearch
def store_restaurant_review(review_data):
    index_name = "restaurant_reviews"
    response = es.index(index=index_name, document=review_data)
    return response

# Store user favorites in Elasticsearch
def store_user_favorite(favorite_data):
    index_name = "user_favorites"
    response = es.index(index=index_name, document=favorite_data)
    return response

# Fetch user favorites from Elasticsearch
def fetch_user_favorites(user_id):
    index_name = "user_favorites"
    query = {
        "query": {
            "match": {
                "user_id": user_id
            }
        }
    }
    response = es.search(index=index_name, body=query)
    return response['hits']['hits']

def fetch_reviews_by_restaurant(restaurant_id):
    index_name = "user_reviews"
    query = {
        "query": {
            "match": {
                "restaurant_id": restaurant_id
            }
        }
    }
    response = es.search(index=index_name, body=query)
    if response['hits']['total']['value'] > 0:
        reviews = [hit['_source'] for hit in response['hits']['hits']]
        log.info(f"Found {len(reviews)} reviews for restaurant {restaurant_id}.")
        return reviews
    else:
        log.info(f"No reviews found for restaurant {restaurant_id}.")
        return []