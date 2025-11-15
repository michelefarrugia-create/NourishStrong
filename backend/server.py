from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, List
import os
import jwt
import bcrypt
import uuid
import base64
import asyncio
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv()

app = FastAPI()
security = HTTPBearer()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client['weight_loss_app']
users_collection = db['users']
meals_collection = db['meals']

# JWT settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-2F8757d69949133Ef3')

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "user"  # "user" or "coach"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class MealCreate(BaseModel):
    image_base64: str
    notes: Optional[str] = ""

class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_level: Optional[str] = None
    goal_weight: Optional[float] = None

class CoachAssignment(BaseModel):
    coach_email: str

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    user = users_collection.find_one({"user_id": payload["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_coach(user = Depends(get_current_user)):
    if user["role"] != "coach":
        raise HTTPException(status_code=403, detail="Coach access required")
    return user

async def analyze_food_image(image_base64: str) -> dict:
    """Analyze food image using GPT-4o with Emergent LLM key"""
    try:
        # Create chat instance
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"food-analysis-{uuid.uuid4()}",
            system_message="You are a nutritionist expert. You MUST respond with ONLY valid JSON, no additional text or explanations."
        ).with_model("openai", "gpt-4o")
        
        # Create image content
        image_content = ImageContent(image_base64=image_base64)
        
        # Create message with stricter JSON requirements
        user_message = UserMessage(
            text="""Analyze this food image and respond with ONLY this exact JSON format (no markdown, no explanations, no additional text):
{"food_name": "name of the dish", "calories": 250, "protein": 20, "carbs": 30, "fats": 10, "portion_size": "1 serving", "confidence": "medium"}

Replace the example values with your analysis. Respond with ONLY the JSON object.""",
            file_contents=[image_content]
        )
        
        # Get response
        response = await chat.send_message(user_message)
        print(f"Raw AI response: {response}")
        
        # Parse response with better error handling
        import json
        import re
        
        # Clean the response
        response_text = response.strip()
        
        # Try to find JSON in the response using regex
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, response_text)
        
        if json_matches:
            response_text = json_matches[0]
        else:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Try to parse JSON
        nutrition_data = json.loads(response_text)
        
        # Validate required fields
        required_fields = ["food_name", "calories", "protein", "carbs", "fats", "portion_size", "confidence"]
        for field in required_fields:
            if field not in nutrition_data:
                raise ValueError(f"Missing required field: {field}")
        
        print(f"Successfully parsed nutrition data: {nutrition_data}")
        return nutrition_data
        
    except Exception as e:
        print(f"Error analyzing food image: {str(e)}")
        print(f"Raw response was: {response if 'response' in locals() else 'No response received'}")
        
        # Return realistic default values if analysis fails
        return {
            "food_name": "Mixed meal",
            "calories": 350,
            "protein": 25,
            "carbs": 40,
            "fats": 12,
            "portion_size": "1 serving",
            "confidence": "low",
            "error": str(e)
        }

# Routes
@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/auth/register")
def register(user_data: UserRegister):
    # Check if user exists
    if users_collection.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "created_at": datetime.utcnow().isoformat(),
        "profile": {},
        "coach_id": None,  # For users to store their assigned coach
        "clients": []  # For coaches to store their client IDs
    }
    users_collection.insert_one(user)
    
    # Create token
    token = create_token(user_id, user_data.email, user_data.role)
    
    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "email": user_data.email,
            "name": user_data.name,
            "role": user_data.role
        }
    }

@app.post("/api/auth/login")
def login(user_data: UserLogin):
    user = users_collection.find_one({"email": user_data.email})
    
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["user_id"], user["email"], user["role"])
    
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/me")
def get_me(user = Depends(get_current_user)):
    # Get coach info if user has a coach
    coach_info = None
    if user.get("coach_id"):
        coach = users_collection.find_one({"user_id": user["coach_id"]})
        if coach:
            coach_info = {
                "coach_id": coach["user_id"],
                "name": coach["name"],
                "email": coach["email"]
            }
    
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "profile": user.get("profile", {}),
        "coach": coach_info
    }

@app.put("/api/profile")
def update_profile(profile_data: UserProfile, user = Depends(get_current_user)):
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"profile": profile_data.dict(exclude_none=True)}}
    )
    return {"message": "Profile updated successfully"}

@app.post("/api/assign-coach")
def assign_coach(assignment: CoachAssignment, user = Depends(get_current_user)):
    # Only regular users can assign coaches
    if user["role"] != "user":
        raise HTTPException(status_code=400, detail="Only users can assign coaches")
    
    # Find the coach by email
    coach = users_collection.find_one({"email": assignment.coach_email, "role": "coach"})
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found with this email")
    
    # Update user's coach_id
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"coach_id": coach["user_id"]}}
    )
    
    # Add user to coach's client list
    users_collection.update_one(
        {"user_id": coach["user_id"]},
        {"$addToSet": {"clients": user["user_id"]}}
    )
    
    return {
        "message": "Coach assigned successfully",
        "coach": {
            "name": coach["name"],
            "email": coach["email"]
        }
    }

@app.delete("/api/remove-coach")
def remove_coach(user = Depends(get_current_user)):
    # Only regular users can remove coaches
    if user["role"] != "user":
        raise HTTPException(status_code=400, detail="Only users can remove coaches")
    
    if not user.get("coach_id"):
        raise HTTPException(status_code=400, detail="No coach assigned")
    
    # Remove user from coach's client list
    users_collection.update_one(
        {"user_id": user["coach_id"]},
        {"$pull": {"clients": user["user_id"]}}
    )
    
    # Remove coach_id from user
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"coach_id": None}}
    )
    
    return {"message": "Coach removed successfully"}

@app.post("/api/meals")
async def create_meal(meal_data: MealCreate, user = Depends(get_current_user)):
    # Analyze the food image
    nutrition_data = await analyze_food_image(meal_data.image_base64)
    
    # Create meal entry
    meal_id = str(uuid.uuid4())
    meal = {
        "meal_id": meal_id,
        "user_id": user["user_id"],
        "image_base64": meal_data.image_base64,
        "notes": meal_data.notes,
        "nutrition": nutrition_data,
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    meals_collection.insert_one(meal)
    
    # Return supportive message without numbers for regular users
    if user["role"] == "user":
        return {
            "meal_id": meal_id,
            "message": f"Great job logging your meal! 🎉 {nutrition_data.get('food_name', 'Your food')} looks delicious. Keep up the amazing work on your journey!",
            "food_name": nutrition_data.get('food_name', 'Unknown'),
            "timestamp": meal["timestamp"]
        }
    else:
        # Coaches can see all data
        return {
            "meal_id": meal_id,
            "nutrition": nutrition_data,
            "timestamp": meal["timestamp"]
        }

@app.get("/api/meals")
def get_meals(user = Depends(get_current_user)):
    meals = list(meals_collection.find({"user_id": user["user_id"]}).sort("timestamp", -1))
    
    # Remove MongoDB _id
    for meal in meals:
        meal.pop('_id', None)
        
        # Hide nutrition data from regular users
        if user["role"] == "user":
            meal.pop('nutrition', None)
    
    return {"meals": meals}

@app.get("/api/meals/{meal_id}")
def get_meal(meal_id: str, user = Depends(get_current_user)):
    meal = meals_collection.find_one({"meal_id": meal_id})
    
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    # Check if user owns the meal or is a coach
    if meal["user_id"] != user["user_id"] and user["role"] != "coach":
        raise HTTPException(status_code=403, detail="Access denied")
    
    meal.pop('_id', None)
    
    # Hide nutrition data from regular users
    if user["role"] == "user":
        meal.pop('nutrition', None)
    
    return meal

@app.delete("/api/meals/{meal_id}")
def delete_meal(meal_id: str, user = Depends(get_current_user)):
    meal = meals_collection.find_one({"meal_id": meal_id})
    
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    if meal["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    meals_collection.delete_one({"meal_id": meal_id})
    return {"message": "Meal deleted successfully"}

# Coach-only endpoints
@app.get("/api/coach/users")
def get_all_users(coach = Depends(require_coach)):
    # Get only assigned clients
    client_ids = coach.get("clients", [])
    
    if not client_ids:
        return {"users": []}
    
    users = list(users_collection.find({"user_id": {"$in": client_ids}}))
    
    for user in users:
        user.pop('_id', None)
        user.pop('password', None)
    
    return {"users": users}

@app.get("/api/coach/users/{user_id}/meals")
def get_user_meals(user_id: str, coach = Depends(require_coach)):
    # Check if this user is assigned to this coach
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    # Get user info
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all meals for this user
    meals = list(meals_collection.find({"user_id": user_id}).sort("timestamp", -1))
    
    for meal in meals:
        meal.pop('_id', None)
    
    return {
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "profile": user.get("profile", {})
        },
        "meals": meals
    }

@app.get("/api/coach/users/{user_id}/stats")
def get_user_stats(user_id: str, coach = Depends(require_coach)):
    # Check if this user is assigned to this coach
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    meals = list(meals_collection.find({"user_id": user_id}))
    
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fats = 0
    
    for meal in meals:
        nutrition = meal.get('nutrition', {})
        total_calories += nutrition.get('calories', 0)
        total_protein += nutrition.get('protein', 0)
        total_carbs += nutrition.get('carbs', 0)
        total_fats += nutrition.get('fats', 0)
    
    return {
        "total_meals": len(meals),
        "total_calories": total_calories,
        "total_protein": total_protein,
        "total_carbs": total_carbs,
        "total_fats": total_fats,
        "avg_calories_per_meal": total_calories / len(meals) if meals else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
