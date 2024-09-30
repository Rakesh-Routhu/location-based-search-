import requests

def find_nearby_restaurants(api_key, location, radius=5000, keyword='restaurant'):
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&keyword={keyword}&key={api_key}"
    response = requests.get(url,verify=False)

    print("Response Status Code:", response.status_code)  # Print the status code
    response_data = response.json()
    print("Response Data:", response_data)  # Print the full response data
    
    if response.status_code == 200 and 'results' in response_data:
        results = response_data['results']
        if results:
            restaurants = []
            for place in results:
                restaurant_info = {
                    'name': place.get('name'),
                    'address': place.get('vicinity'),
                    'rating': place.get('rating'),
                    'place_id': place.get('place_id')
                }
                restaurants.append(restaurant_info)
            return restaurants
        else:
            print("Found 0 restaurants.")
            return []
    else:
        print(f"Error: {response_data.get('error_message', 'Unknown error')}")
        return []

# Example usage
api_key = 'AIzaSyAwLW9piy3F_VDT674GrolzKCBtlAo6_Xg'
location = '37.7749,-122.4194'  # Latitude,Longitude for San Francisco
print(f"Finding restaurants near {location}...")
restaurants = find_nearby_restaurants(api_key, location)
print(f"Found {len(restaurants)} restaurants:")
for restaurant in restaurants:
    print(restaurant)
