class UserService:
    def __init__(self):
        # Replace Elasticsearch with a simple dictionary as in-memory storage
        self.users = {}  # In-memory storage for user data (keyed by email)
        
    def signup(self, username, password, email, phone=None, address=None):
        # Check if a user with the same email already exists
        if email in self.users:
            return {"success": False, "error": "User already exists"}
        
        # Prepare the user data
        user_data = {
            "username": username,
            "password": password,  # Ensure password is hashed in a real application
            "email": email,
            "phone": phone,
            "address": address
        }
        
        # Remove None values to keep the data clean
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        # Save the user data in the in-memory cache
        self.users[email] = user_data
        return {"success": True}

    def login(self, email, password):
        # Check if the user exists in the cache
        user_data = self.users.get(email)
        if not user_data:
            return {"success": False}
        
        # Verify the password (hashed passwords should be used in real applications)
        if user_data['password'] == password:
            return {"success": True, "token": "fake-jwt-token"}  # Replace with actual JWT logic
        
        return {"success": False}

    def update_user(self, username, email, password):
        # Check if the user exists in the cache
        user_data = self.users.get(email)
        if not user_data:
            return {"success": False, "error": "User not found"}
        
        # Prepare the update data
        update_data = {}
        if username:
            update_data["username"] = username
        if password:
            update_data["password"] = password  # Hash password in a real implementation
        
        # Update the user data in memory
        self.users[email].update(update_data)
        return {"success": True}

    def delete_user(self, email):
        # Check if the user exists in the cache
        if email in self.users:
            del self.users[email]
            return {"success": True}
        else:
            return {"success": False, "error": "User not found"}
