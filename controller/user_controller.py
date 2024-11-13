from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional
from service.user_service import UserService

# Create router
user_controller = APIRouter()

# Pydantic models for input validation
class SignupModel(BaseModel):
    username: str
    password: str
    email: str
    address: str
    phone: str

class LoginModel(BaseModel):
    email: str
    password: str

class UpdateModel(BaseModel):
    username: str
    email: Optional[str] = None
    password: Optional[str] = None

# Dependency to use the service
user_service = UserService()

@user_controller.post("/signup")
async def signup(user: SignupModel):
    result = user_service.signup(user.username, user.password, user.email)
    if result.get("success"):
        return {"message": "User signed up successfully"}
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))

@user_controller.post("/login")
async def login(user: LoginModel):
    result = user_service.login(user.email, user.password)
    if result.get("success"):
        return {"message": "Login successful", "token": result.get("token")}
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")

@user_controller.put("/update")
async def update(user: UpdateModel):
    result = user_service.update_user(user.username, user.email, user.password)
    if result.get("success"):
        return {"message": "User updated successfully"}
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))
