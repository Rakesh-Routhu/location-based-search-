import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s environment variable" % var_name
        raise Exception(error_msg)


GOOGLE_API_KEY = get_env_variable('GOOGLE_API_KEY')
GOOGLE_PLACES_API_BASE_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
GOOGLE_GEOCODE_API_BASE_URL = 'https://maps.googleapis.com/maps/api/geocode/json'