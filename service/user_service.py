import bcrypt
import uuid
import datetime
from datetime import timedelta
import jwt
from elasticsearch import Elasticsearch
import server_properties
import logging
from helper import notification

log = logging.getLogger(__name__)

# Elasticsearch connection configuration
es = Elasticsearch(
    hosts=[server_properties.ES_HOST],
    http_auth=(server_properties.ES_USER, server_properties.ES_PASSWORD)
)

log.info("Connected to Elasticsearch")
USER_INDEX = "users"

# JWT Configuration
SECRET_KEY = server_properties.SECRET_KEY  # Use a strong secret key in production
ALGORITHM = server_properties.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing functions
def hash_password(password: str) -> str:
    """
    Hash the password using bcrypt
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(stored_hash: str, password: str) -> bool:
    """
    Verify the password with the stored hashed password
    """
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

def create_access_token(user_id: str):
    """
    Create an access token for the user with user_id in the payload.
    """
    expires = datetime.datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"user_id": user_id, "exp": expires}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class UserService:
    def __init__(self):
        self.es = es
        self.index = USER_INDEX

    def signup(self, username: str, password: str, email: str):
        """
        Handle user signup.
        Checks if the email already exists, hashes the password, and stores the user data in Elasticsearch.
        """
        # Check if the user already exists based on email
        query = {
            "query": {
                "term": {
                    "email": email
                }
            }
        }

        res = self.es.search(index=self.index, body=query)

        if res['hits']['total']['value'] > 0:
            return {"success": False, "error": "User already exists"}

        # Hash the password before storing it
        hashed_password = hash_password(password)

        # Prepare user data for Elasticsearch document
        user_data = {
            "user_id": str(uuid.uuid4()),  # Unique UUID for each user
            "email": email,
            "username": username,
            "password": hashed_password,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }

        # Index the user document in Elasticsearch
        self.es.index(index=self.index, document=user_data)

        # Send welcome notification
        subject = "Welcome! Your Guide to Local Restaurants is Here!"
        body = f"Hello {username},\n\nThank you for signing up! We're excited to have you on board."
        print("subject",subject,"body ",body)
        notification.send_notification(subject,body,email)  # Calling the function from notification.py

        # Return success with user_id and JWT token
        return {"success": True, "user_id": user_data["user_id"], "token": create_access_token(user_data["user_id"])}

    def login(self, email: str, password: str):
        """
        Handle user login.
        Verifies the user's credentials and returns a JWT token on successful login.
        """
        # Check if the user exists based on email
        query = {
            "query": {
                "term": {
                    "email": email
                }
            }
        }

        res = self.es.search(index=self.index, body=query)

        if res['hits']['total']['value'] == 0:
            return {"success": False, "error": "User not found"}

        user_data = res['hits']['hits'][0]['_source']
        result = {
            "user_id":user_data["user_id"],
            "email":user_data["email"],
            "username":user_data["username"]
        }
        log.info(f"result {result}")

        # Verify the password against the stored hash
        if verify_password(user_data['password'], password):
            token = create_access_token(user_data["user_id"])
            return {"success": True, "result": result, "token": token}

        return {"success": False, "error": "Invalid credentials"}

    def update_user(self, user_id: str, username: str = None, password: str = None):
        """
        Update the user's details (username or password).
        """
        # Get user data by user_id
        query = {
            "query": {
                "term": {
                    "user_id": user_id
                }
            }
        }

        res = self.es.search(index=self.index, body=query)

        if res['hits']['total']['value'] == 0:
            return {"success": False, "error": "User not found"}

        user_data = res['hits']['hits'][0]['_source']

        # Prepare the update data
        update_data = {}

        if username:
            update_data["username"] = username
        if password:
            update_data["password"] = hash_password(password)  # Hash the new password

        # Update the document in Elasticsearch
        update_query = {
            "doc": update_data
        }

        update_res = self.es.update(index=self.index, id=res['hits']['hits'][0]['_id'], body=update_query)

        return {"success": True}