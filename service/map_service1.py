import requests
import server_properties
from elasticsearch import Elasticsearch,NotFoundError
from helper import utility
from datetime import datetime
import logger

log = logger.get_logger()

api_key = server_properties.GOOGLE_API_KEY

es_host = 'https://192.168.1.57:9200'
username = 'elastic'
password = 'cRb3rurpFbWe0DpL2p4g'

es = Elasticsearch(
    es_host,
    basic_auth=(username, password),
    verify_certs=False 
)
def find_nearby_restaurants(api_key, location, radius=5000, keyword='restaurant'):
    log.info("Inside find_nearby_restaurants")
    latitude, longitude = get_lat_long(location)
    if latitude is None or longitude is None:
        log.error("Failed to get latitude and longitude.")
        return []

    location = f"{latitude},{longitude}"
    
    # Search for existing data in Elasticsearch
    es_query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"keyword": keyword}},
                    {
                        "geo_distance": {
                            "distance": f"{radius}m",  # radius in meters
                            "location": {
                                "lat": latitude,
                                "lon": longitude
                            }
                        }
                    }
                ]
            }
        }
    }
    log.info("searching in ES...")
    es_response = es.search(index="restaurants", body=es_query)
    
    if es_response['hits']['total']['value'] > 0:
        log.info("Found results in Elasticsearch.")
        return [hit['_source'] for hit in es_response['hits']['hits']]
    log.info("Data did not found in ES so direct call to place api")
    
    # If no data found, call the Google Places API
    log.info(f"Finding restaurants near {latitude},{longitude}...")
    url = utility.build_places_url(location, radius, keyword)
    log.info(f"url -> {url}")
    
    response = requests.get(url, verify=False)
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
                    'id': place.get('place_id'),
                    'location': {'lat': latitude, 'lon': longitude},
                    'keyword': keyword
                }
                
                # Add the restaurant to the list
                restaurants.append(restaurant_info)
                
                # Store in Elasticsearch
                es.index(index="restaurants", body=restaurant_info)

            for place in results:
                interaction_data = {
                        'restaurant_id': place.get('place_id'),
                        'name': place.get('name'),
                        'searched_location': {'lat': latitude, 'lon': longitude},
                        'keyword': keyword,
                        'timestamp': datetime.now().isoformat()  # Add the current timestamp in ISO format
                    }

                # Store the interaction data in Elasticsearch in the `interaction_history` index
                es.index(index="interaction_history", body=interaction_data)
            
            # Sort results by rating
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


def store_reviews_in_elasticsearch(restaurant_id, reviews):
    """
    Stores the reviews in Elasticsearch for the given restaurant.
    """
    doc = {
        "reviews": reviews
    }

    # Check if the restaurant already exists in Elasticsearch
    try:
        # Try to fetch the restaurant document by its ID
        existing_doc = es.get(index="restaurants", id=restaurant_id)
        # If the document exists, update it with the new reviews
        es.update(index="restaurants", id=restaurant_id, body={
            "doc": doc
        })
        log.info(f"Updated reviews for restaurant {restaurant_id}")
    except NotFoundError:
        # If the restaurant does not exist, create a new document
        doc.update({
            "id": restaurant_id,
            "reviews": reviews  # Include reviews in the document
        })
        es.index(index="restaurants", id=restaurant_id, body=doc)
        log.info(f"Added reviews for restaurant {restaurant_id}")

def get_restaurant_reviews(api_key, restaurant_id):
    """
    Get restaurant reviews. First search for reviews in Elasticsearch.
    If not found, fetch them from Google Places API and store in Elasticsearch.
    """
    # First, try to get reviews from Elasticsearch
    try:
        res = es.get(index="restaurants", id=restaurant_id)
        reviews = res['_source']['reviews']  # Retrieve cached reviews from Elasticsearch
        log.info(f"Found reviews in Elasticsearch for restaurant {restaurant_id}")
        return reviews
    except NotFoundError:
        # If reviews are not found in Elasticsearch, fetch from Google API
        log.info(f"Reviews not found in Elasticsearch for restaurant {restaurant_id}. Fetching from Google Places API.")
        details = get_restaurant_details(api_key, restaurant_id)
        
        # If reviews are found in the Google Places API response, store them in Elasticsearch
        if 'reviews' in details:
            reviews = details['reviews']
            store_reviews_in_elasticsearch(restaurant_id, reviews)
            return reviews
        else:
            return []