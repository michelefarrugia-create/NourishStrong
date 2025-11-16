from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, List
from collections import Counter
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
progress_photos_collection = db['progress_photos']
challenges_collection = db['challenges']
activities_collection = db['activities']

# JWT settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-2F8757d69949133Ef3')

# Badge definitions
BADGES = {
    "first_meal": {"name": "First Steps", "description": "Logged your first meal", "icon": "🎯"},
    "week_streak": {"name": "Week Warrior", "description": "7-day logging streak", "icon": "🔥"},
    "month_streak": {"name": "Month Master", "description": "30-day logging streak", "icon": "⭐"},
    "meals_10": {"name": "Getting Started", "description": "Logged 10 meals", "icon": "🌱"},
    "meals_50": {"name": "Committed", "description": "Logged 50 meals", "icon": "💪"},
    "meals_100": {"name": "Century Club", "description": "Logged 100 meals", "icon": "🏆"},
    "early_bird": {"name": "Early Bird", "description": "Logged breakfast before 9am", "icon": "🌅"},
    "consistent": {"name": "Consistency King", "description": "Logged 3 meals in one day", "icon": "👑"},
    "first_activity": {"name": "Active Start", "description": "Logged your first activity", "icon": "🏃"},
    "activity_10": {"name": "Moving Forward", "description": "Logged 10 activities", "icon": "🚴"},
    "activity_50": {"name": "Fitness Enthusiast", "description": "Logged 50 activities", "icon": "🏋️"},
    "marathon": {"name": "Marathon Master", "description": "Logged 5+ hours of activity in a week", "icon": "🎖️"},
}

# Activity types with calorie burn rates (calories per minute based on moderate intensity)
ACTIVITY_TYPES = {
    "walking": {"name": "Walking", "icon": "🚶", "cal_per_min": {"low": 3, "moderate": 5, "high": 7}},
    "running": {"name": "Running", "icon": "🏃", "cal_per_min": {"low": 7, "moderate": 10, "high": 15}},
    "cycling": {"name": "Cycling", "icon": "🚴", "cal_per_min": {"low": 5, "moderate": 8, "high": 12}},
    "swimming": {"name": "Swimming", "icon": "🏊", "cal_per_min": {"low": 6, "moderate": 9, "high": 13}},
    "gym": {"name": "Gym Workout", "icon": "🏋️", "cal_per_min": {"low": 4, "moderate": 6, "high": 9}},
    "yoga": {"name": "Yoga", "icon": "🧘", "cal_per_min": {"low": 2, "moderate": 3, "high": 5}},
    "dancing": {"name": "Dancing", "icon": "💃", "cal_per_min": {"low": 4, "moderate": 6, "high": 9}},
    "sports": {"name": "Sports", "icon": "⚽", "cal_per_min": {"low": 5, "moderate": 8, "high": 12}},
    "hiking": {"name": "Hiking", "icon": "🥾", "cal_per_min": {"low": 4, "moderate": 6, "high": 9}},
    "other": {"name": "Other", "icon": "🎯", "cal_per_min": {"low": 3, "moderate": 5, "high": 7}},
}

def calculate_calories_burned(activity_type: str, duration_minutes: int, intensity: str) -> int:
    """Calculate estimated calories burned based on activity type, duration, and intensity"""
    if activity_type not in ACTIVITY_TYPES:
        activity_type = "other"
    
    cal_rates = ACTIVITY_TYPES[activity_type]["cal_per_min"]
    cal_per_min = cal_rates.get(intensity, cal_rates["moderate"])
    
    return int(cal_per_min * duration_minutes)

def parse_apple_health_xml(xml_content: str) -> List[dict]:
    """Parse Apple Health XML export and extract workout data"""
    import xml.etree.ElementTree as ET
    from datetime import datetime
    
    activities = []
    
    try:
        root = ET.fromstring(xml_content)
        
        # Map Apple workout types to our activity types
        workout_type_map = {
            "HKWorkoutActivityTypeWalking": "walking",
            "HKWorkoutActivityTypeRunning": "running",
            "HKWorkoutActivityTypeCycling": "cycling",
            "HKWorkoutActivityTypeSwimming": "swimming",
            "HKWorkoutActivityTypeFunctionalStrengthTraining": "gym",
            "HKWorkoutActivityTypeTraditionalStrengthTraining": "gym",
            "HKWorkoutActivityTypeYoga": "yoga",
            "HKWorkoutActivityTypeDance": "dancing",
            "HKWorkoutActivityTypeSoccer": "sports",
            "HKWorkoutActivityTypeBasketball": "sports",
            "HKWorkoutActivityTypeHiking": "hiking",
        }
        
        for workout in root.findall(".//Workout"):
            workout_type = workout.get("workoutActivityType", "")
            duration = float(workout.get("duration", 0))
            start_date = workout.get("startDate", "")
            
            # Map to our activity type
            activity_type = workout_type_map.get(workout_type, "other")
            duration_minutes = int(duration / 60) if duration > 0 else 0
            
            if duration_minutes > 0:
                activities.append({
                    "activity_type": activity_type,
                    "duration_minutes": duration_minutes,
                    "intensity": "moderate",
                    "timestamp": start_date,
                    "source": "Apple Health"
                })
        
    except Exception as e:
        print(f"Error parsing Apple Health XML: {str(e)}")
    
    return activities

def parse_google_fit_csv(csv_content: str) -> List[dict]:
    """Parse Google Fit CSV export and extract activity data"""
    import csv
    from io import StringIO
    
    activities = []
    
    try:
        csv_reader = csv.DictReader(StringIO(csv_content))
        
        # Map Google Fit activity names to our types
        activity_map = {
            "walking": "walking",
            "running": "running",
            "biking": "cycling",
            "swimming": "swimming",
            "strength training": "gym",
            "yoga": "yoga",
            "dancing": "dancing",
            "football": "sports",
            "basketball": "sports",
            "hiking": "hiking",
        }
        
        for row in csv_reader:
            # Google Fit CSV typically has: Activity, Date, Duration, etc.
            activity_name = row.get("Activity", "").lower()
            duration_str = row.get("Duration (min)", "") or row.get("Duration", "")
            date_str = row.get("Date", "")
            
            # Match activity type
            activity_type = "other"
            for key, value in activity_map.items():
                if key in activity_name:
                    activity_type = value
                    break
            
            try:
                duration_minutes = int(float(duration_str))
            except:
                duration_minutes = 0
            
            if duration_minutes > 0:
                activities.append({
                    "activity_type": activity_type,
                    "duration_minutes": duration_minutes,
                    "intensity": "moderate",
                    "timestamp": date_str,
                    "source": "Google Fit"
                })
        
    except Exception as e:
        print(f"Error parsing Google Fit CSV: {str(e)}")
    
    return activities

# Motivational quotes
MOTIVATIONAL_QUOTES = [
    {"quote": "Every meal logged is a step closer to your goal.", "category": "motivation"},
    {"quote": "Progress, not perfection. You're doing great!", "category": "encouragement"},
    {"quote": "Small changes lead to remarkable transformations.", "category": "motivation"},
    {"quote": "Your journey is unique and beautiful.", "category": "encouragement"},
    {"quote": "Consistency is the key to lasting change.", "category": "motivation"},
    {"quote": "Celebrate every small victory along the way.", "category": "encouragement"},
    {"quote": "You're stronger than you think.", "category": "motivation"},
    {"quote": "Focus on how you feel, not just the numbers.", "category": "wellness"},
    {"quote": "Nourish your body with love and intention.", "category": "wellness"},
    {"quote": "Every day is a fresh start.", "category": "motivation"},
    {"quote": "Your health journey is a marathon, not a sprint.", "category": "wellness"},
    {"quote": "Believe in yourself and all that you are.", "category": "encouragement"},
    {"quote": "You're making positive choices for your future self.", "category": "motivation"},
    {"quote": "Progress is progress, no matter how small.", "category": "encouragement"},
    {"quote": "Stay committed to your goals, even on tough days.", "category": "motivation"},
    {"quote": "Your body is your home. Treat it with respect.", "category": "wellness"},
    {"quote": "Healthy eating is an act of self-love.", "category": "wellness"},
    {"quote": "You have the power to change your story.", "category": "motivation"},
    {"quote": "Trust the process and enjoy the journey.", "category": "encouragement"},
    {"quote": "Your dedication is inspiring. Keep going!", "category": "encouragement"},
]

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "user"

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

class ProgressPhoto(BaseModel):
    image_base64: str
    weight: Optional[float] = None
    notes: Optional[str] = ""

class DailyChallengeComplete(BaseModel):
    challenge_id: str

class ActivityLog(BaseModel):
    activity_type: str
    duration_minutes: int
    intensity: str  # low, moderate, high
    notes: Optional[str] = ""

class HealthDataImport(BaseModel):
    file_type: str  # "apple_health" or "google_fit"
    file_content: str  # base64 encoded file content

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

def calculate_streak(user_id: str) -> int:
    """Calculate current consecutive days streak"""
    meals = list(meals_collection.find({"user_id": user_id}).sort("timestamp", -1))
    
    if not meals:
        return 0
    
    # Get unique days with meals
    days_with_meals = set()
    for meal in meals:
        meal_date = datetime.fromisoformat(meal["timestamp"]).date()
        days_with_meals.add(meal_date)
    
    # Sort days in descending order
    sorted_days = sorted(days_with_meals, reverse=True)
    
    if not sorted_days:
        return 0
    
    # Check if today or yesterday has a meal (streak is still active)
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    if sorted_days[0] not in [today, yesterday]:
        return 0  # Streak is broken
    
    # Count consecutive days
    streak = 1
    current_date = sorted_days[0]
    
    for i in range(1, len(sorted_days)):
        expected_date = current_date - timedelta(days=1)
        if sorted_days[i] == expected_date:
            streak += 1
            current_date = sorted_days[i]
        else:
            break
    
    return streak

def check_and_award_badges(user_id: str) -> List[str]:
    """Check and award new badges to user"""
    user = users_collection.find_one({"user_id": user_id})
    current_badges = set(user.get("badges", []))
    new_badges = []
    
    # Get user stats
    meals = list(meals_collection.find({"user_id": user_id}))
    meal_count = len(meals)
    streak = calculate_streak(user_id)
    
    # Get activity stats
    activities = list(activities_collection.find({"user_id": user_id}))
    activity_count = len(activities)
    
    # Check badge conditions
    if meal_count >= 1 and "first_meal" not in current_badges:
        new_badges.append("first_meal")
    
    if meal_count >= 10 and "meals_10" not in current_badges:
        new_badges.append("meals_10")
    
    if meal_count >= 50 and "meals_50" not in current_badges:
        new_badges.append("meals_50")
    
    if meal_count >= 100 and "meals_100" not in current_badges:
        new_badges.append("meals_100")
    
    if streak >= 7 and "week_streak" not in current_badges:
        new_badges.append("week_streak")
    
    if streak >= 30 and "month_streak" not in current_badges:
        new_badges.append("month_streak")
    
    # Check for early bird (meal before 9am)
    for meal in meals:
        meal_time = datetime.fromisoformat(meal["timestamp"])
        if meal_time.hour < 9 and "early_bird" not in current_badges:
            new_badges.append("early_bird")
            break
    
    # Check for consistent (3 meals in one day)
    meals_by_day = {}
    for meal in meals:
        meal_date = datetime.fromisoformat(meal["timestamp"]).date()
        meals_by_day[meal_date] = meals_by_day.get(meal_date, 0) + 1
    
    if any(count >= 3 for count in meals_by_day.values()) and "consistent" not in current_badges:
        new_badges.append("consistent")
    
    # Activity badges
    if activity_count >= 1 and "first_activity" not in current_badges:
        new_badges.append("first_activity")
    
    if activity_count >= 10 and "activity_10" not in current_badges:
        new_badges.append("activity_10")
    
    if activity_count >= 50 and "activity_50" not in current_badges:
        new_badges.append("activity_50")
    
    # Marathon badge - 5+ hours of activity in past week
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_activities = [a for a in activities if datetime.fromisoformat(a["timestamp"]) >= week_ago]
    total_minutes = sum(a["duration_minutes"] for a in recent_activities)
    if total_minutes >= 300 and "marathon" not in current_badges:  # 5 hours = 300 minutes
        new_badges.append("marathon")
    
    # Update user badges
    if new_badges:
        users_collection.update_one(
            {"user_id": user_id},
            {"$addToSet": {"badges": {"$each": new_badges}}}
        )
    
    return new_badges

def generate_daily_challenge(user_id: str) -> dict:
    """Generate daily challenge for user"""
    today = datetime.utcnow().date().isoformat()
    
    # Check if challenge already exists for today
    existing = challenges_collection.find_one({
        "user_id": user_id,
        "date": today
    })
    
    if existing:
        existing.pop('_id', None)
        return existing
    
    # Create new challenge
    challenges = [
        {"id": "log_breakfast", "title": "Log Your Breakfast", "description": "Start your day right by logging breakfast", "icon": "🌅"},
        {"id": "log_3_meals", "title": "Log 3 Meals Today", "description": "Track all your main meals", "icon": "🍽️"},
        {"id": "early_meal", "title": "Early Bird Special", "description": "Log a meal before 9am", "icon": "⏰"},
        {"id": "add_notes", "title": "Mindful Eating", "description": "Add notes to your meal today", "icon": "📝"},
        {"id": "log_any_meal", "title": "Stay Consistent", "description": "Log at least one meal today", "icon": "✨"},
    ]
    
    import random
    challenge = random.choice(challenges)
    
    challenge_doc = {
        "challenge_id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": today,
        "challenge": challenge,
        "completed": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    challenges_collection.insert_one(challenge_doc)
    challenge_doc.pop('_id', None)
    
    return challenge_doc

async def analyze_food_image(image_base64: str) -> dict:
    """Analyze food image using GPT-4o with Emergent LLM key"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"food-analysis-{uuid.uuid4()}",
            system_message="You are a nutritionist expert. You MUST respond with ONLY valid JSON, no additional text or explanations."
        ).with_model("openai", "gpt-4o")
        
        image_content = ImageContent(image_base64=image_base64)
        
        user_message = UserMessage(
            text="""Analyze this food image and respond with ONLY this exact JSON format (no markdown, no explanations, no additional text):
{"food_name": "name of the dish", "calories": 250, "protein": 20, "carbs": 30, "fats": 10, "portion_size": "1 serving", "confidence": "medium"}

Replace the example values with your analysis. Respond with ONLY the JSON object.""",
            file_contents=[image_content]
        )
        
        response = await chat.send_message(user_message)
        print(f"Raw AI response: {response}")
        
        import json
        import re
        
        response_text = response.strip()
        
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, response_text)
        
        if json_matches:
            response_text = json_matches[0]
        else:
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
        
        nutrition_data = json.loads(response_text)
        
        required_fields = ["food_name", "calories", "protein", "carbs", "fats", "portion_size", "confidence"]
        for field in required_fields:
            if field not in nutrition_data:
                raise ValueError(f"Missing required field: {field}")
        
        print(f"Successfully parsed nutrition data: {nutrition_data}")
        return nutrition_data
        
    except Exception as e:
        print(f"Error analyzing food image: {str(e)}")
        print(f"Raw response was: {response if 'response' in locals() else 'No response received'}")
        
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
    if users_collection.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "created_at": datetime.utcnow().isoformat(),
        "profile": {},
        "coach_id": None,
        "clients": [],
        "badges": [],
        "streak_record": 0
    }
    users_collection.insert_one(user)
    
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
        "coach": coach_info,
        "badges": user.get("badges", []),
        "streak_record": user.get("streak_record", 0)
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
    if user["role"] != "user":
        raise HTTPException(status_code=400, detail="Only users can assign coaches")
    
    coach = users_collection.find_one({"email": assignment.coach_email, "role": "coach"})
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found with this email")
    
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"coach_id": coach["user_id"]}}
    )
    
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
    if user["role"] != "user":
        raise HTTPException(status_code=400, detail="Only users can remove coaches")
    
    if not user.get("coach_id"):
        raise HTTPException(status_code=400, detail="No coach assigned")
    
    users_collection.update_one(
        {"user_id": user["coach_id"]},
        {"$pull": {"clients": user["user_id"]}}
    )
    
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"coach_id": None}}
    )
    
    return {"message": "Coach removed successfully"}

@app.get("/api/gamification/streak")
def get_streak(user = Depends(get_current_user)):
    current_streak = calculate_streak(user["user_id"])
    streak_record = user.get("streak_record", 0)
    
    # Update record if current streak is higher
    if current_streak > streak_record:
        users_collection.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"streak_record": current_streak}}
        )
        streak_record = current_streak
    
    return {
        "current_streak": current_streak,
        "streak_record": streak_record
    }

@app.get("/api/gamification/badges")
def get_badges(user = Depends(get_current_user)):
    user_badges = user.get("badges", [])
    
    badges_info = []
    for badge_id in user_badges:
        if badge_id in BADGES:
            badge_data = BADGES[badge_id].copy()
            badge_data["id"] = badge_id
            badges_info.append(badge_data)
    
    # Get all available badges
    all_badges = []
    for badge_id, badge_data in BADGES.items():
        badge_info = badge_data.copy()
        badge_info["id"] = badge_id
        badge_info["earned"] = badge_id in user_badges
        all_badges.append(badge_info)
    
    return {
        "earned_badges": badges_info,
        "all_badges": all_badges,
        "total_earned": len(badges_info),
        "total_available": len(BADGES)
    }

@app.get("/api/gamification/challenge")
def get_daily_challenge(user = Depends(get_current_user)):
    challenge = generate_daily_challenge(user["user_id"])
    return challenge

@app.post("/api/gamification/challenge/complete")
def complete_challenge(challenge_data: DailyChallengeComplete, user = Depends(get_current_user)):
    result = challenges_collection.update_one(
        {"challenge_id": challenge_data.challenge_id, "user_id": user["user_id"]},
        {"$set": {"completed": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    return {"message": "Challenge completed!", "celebration": True}

@app.get("/api/gamification/quote")
def get_daily_quote(user = Depends(get_current_user)):
    """Get a random motivational quote"""
    import random
    quote = random.choice(MOTIVATIONAL_QUOTES)
    return {
        "quote": quote["quote"],
        "category": quote["category"],
        "icon": "💫"
    }

@app.post("/api/barcode-scan")
async def scan_barcode(barcode_data: dict, user = Depends(get_current_user)):
    """Scan barcode and get nutrition info using AI"""
    barcode = barcode_data.get("barcode")
    
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode required")
    
    try:
        # Use AI to generate realistic nutrition data based on barcode
        # In production, you'd use a real API like Open Food Facts or USDA
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"barcode-scan-{uuid.uuid4()}",
            system_message="You are a nutrition database expert. Provide realistic nutrition information for common food products."
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(
            text=f"""Given this barcode number: {barcode}
            
Provide realistic nutrition information in this exact JSON format (no markdown, no explanations):
{{"food_name": "product name", "brand": "brand name", "calories": 250, "protein": 10, "carbs": 30, "fats": 8, "serving_size": "1 serving", "confidence": "medium"}}

Make educated guesses for common products. If it seems like a snack barcode, suggest snack nutrition. If it seems like a beverage, suggest beverage nutrition."""
        )
        
        response = await chat.send_message(user_message)
        
        import json
        import re
        
        response_text = response.strip()
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, response_text)
        
        if json_matches:
            response_text = json_matches[0]
        
        nutrition_data = json.loads(response_text)
        
        return {
            "success": True,
            "barcode": barcode,
            "product": nutrition_data
        }
        
    except Exception as e:
        print(f"Error scanning barcode: {str(e)}")
        return {
            "success": False,
            "message": "Could not identify product. Please try manual entry or take a photo.",
            "barcode": barcode
        }

@app.get("/api/activities/types")
def get_activity_types():
    """Get list of available activity types"""
    activity_list = []
    for key, value in ACTIVITY_TYPES.items():
        activity_list.append({
            "id": key,
            "name": value["name"],
            "icon": value["icon"]
        })
    return {"activities": activity_list}

@app.post("/api/activities")
def log_activity(activity_data: ActivityLog, user = Depends(get_current_user)):
    """Log a new activity"""
    # Calculate calories burned
    calories_burned = calculate_calories_burned(
        activity_data.activity_type,
        activity_data.duration_minutes,
        activity_data.intensity
    )
    
    activity_id = str(uuid.uuid4())
    activity = {
        "activity_id": activity_id,
        "user_id": user["user_id"],
        "activity_type": activity_data.activity_type,
        "duration_minutes": activity_data.duration_minutes,
        "intensity": activity_data.intensity,
        "calories_burned": calories_burned,
        "notes": activity_data.notes,
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    activities_collection.insert_one(activity)
    
    # Check for new badges
    new_badges = check_and_award_badges(user["user_id"])
    
    activity_info = ACTIVITY_TYPES.get(activity_data.activity_type, ACTIVITY_TYPES["other"])
    
    response = {
        "activity_id": activity_id,
        "message": f"Great workout! {activity_info['icon']} You burned approximately {calories_burned} calories!",
        "calories_burned": calories_burned,
        "duration_minutes": activity_data.duration_minutes,
        "timestamp": activity["timestamp"]
    }
    
    if new_badges:
        response["new_badges"] = [BADGES[b] for b in new_badges if b in BADGES]
        response["celebration"] = True
    
    return response

@app.get("/api/activities")
def get_activities(user = Depends(get_current_user)):
    """Get user's activity history - hide details from regular users"""
    activities = list(activities_collection.find({"user_id": user["user_id"]}).sort("timestamp", -1))
    
    for activity in activities:
        activity.pop('_id', None)
        # Add activity type info
        if activity["activity_type"] in ACTIVITY_TYPES:
            activity["activity_info"] = ACTIVITY_TYPES[activity["activity_type"]]
        
        # Hide calories and detailed stats from regular users
        if user["role"] != "coach":
            activity.pop('calories_burned', None)
            activity.pop('duration_minutes', None)
            activity.pop('intensity', None)
    
    return {"activities": activities}

@app.get("/api/activities/stats")
def get_activity_stats(user = Depends(get_current_user)):
    """Get activity statistics - only for coaches"""
    # Regular users should not see their stats
    if user["role"] != "coach":
        return {
            "message": "Activity stats are private and only visible to your coach"
        }
    
    activities = list(activities_collection.find({"user_id": user["user_id"]}))
    
    if not activities:
        return {
            "total_activities": 0,
            "total_calories_burned": 0,
            "total_minutes": 0,
            "this_week_activities": 0,
            "this_week_calories": 0,
            "this_week_minutes": 0,
            "favorite_activity": None
        }
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    total_calories = sum(a["calories_burned"] for a in activities)
    total_minutes = sum(a["duration_minutes"] for a in activities)
    
    this_week = [a for a in activities if datetime.fromisoformat(a["timestamp"]) >= week_ago]
    this_week_calories = sum(a["calories_burned"] for a in this_week)
    this_week_minutes = sum(a["duration_minutes"] for a in this_week)
    
    # Find favorite activity
    activity_counts = Counter(a["activity_type"] for a in activities)
    favorite = activity_counts.most_common(1)[0] if activity_counts else None
    favorite_activity = None
    if favorite:
        favorite_activity = {
            "type": favorite[0],
            "count": favorite[1],
            "name": ACTIVITY_TYPES.get(favorite[0], ACTIVITY_TYPES["other"])["name"],
            "icon": ACTIVITY_TYPES.get(favorite[0], ACTIVITY_TYPES["other"])["icon"]
        }
    
    return {
        "total_activities": len(activities),
        "total_calories_burned": total_calories,
        "total_minutes": total_minutes,
        "this_week_activities": len(this_week),
        "this_week_calories": this_week_calories,
        "this_week_minutes": this_week_minutes,
        "favorite_activity": favorite_activity
    }

@app.delete("/api/activities/{activity_id}")
def delete_activity(activity_id: str, user = Depends(get_current_user)):
    """Delete an activity"""
    activity = activities_collection.find_one({"activity_id": activity_id})
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if activity["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    activities_collection.delete_one({"activity_id": activity_id})
    return {"message": "Activity deleted successfully"}

@app.post("/api/activities/import")
def import_health_data(import_data: HealthDataImport, user = Depends(get_current_user)):
    """Import activities from Apple Health XML or Google Fit CSV"""
    import base64
    
    try:
        # Decode file content
        file_content = base64.b64decode(import_data.file_content).decode('utf-8')
        
        # Parse based on file type
        if import_data.file_type == "apple_health":
            activities_data = parse_apple_health_xml(file_content)
        elif import_data.file_type == "google_fit":
            activities_data = parse_google_fit_csv(file_content)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        if not activities_data:
            return {
                "success": False,
                "message": "No activities found in the file. Make sure it's a valid export.",
                "imported_count": 0
            }
        
        # Import activities
        imported_count = 0
        new_badges = []
        
        for activity_data in activities_data:
            # Calculate calories
            calories = calculate_calories_burned(
                activity_data["activity_type"],
                activity_data["duration_minutes"],
                activity_data["intensity"]
            )
            
            activity_id = str(uuid.uuid4())
            activity = {
                "activity_id": activity_id,
                "user_id": user["user_id"],
                "activity_type": activity_data["activity_type"],
                "duration_minutes": activity_data["duration_minutes"],
                "intensity": activity_data["intensity"],
                "calories_burned": calories,
                "notes": f"Imported from {activity_data['source']}",
                "timestamp": activity_data.get("timestamp", datetime.utcnow().isoformat()),
                "created_at": datetime.utcnow().isoformat(),
                "imported": True
            }
            activities_collection.insert_one(activity)
            imported_count += 1
        
        # Check for new badges after import
        new_badges = check_and_award_badges(user["user_id"])
        
        response = {
            "success": True,
            "message": f"Successfully imported {imported_count} activities! 🎉",
            "imported_count": imported_count
        }
        
        if new_badges:
            response["new_badges"] = [BADGES[b] for b in new_badges if b in BADGES]
            response["celebration"] = True
        
        return response
        
    except Exception as e:
        print(f"Error importing health data: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to import: {str(e)}",
            "imported_count": 0
        }

@app.get("/api/analytics/overview")
def get_analytics_overview(user = Depends(get_current_user)):
    meals = list(meals_collection.find({"user_id": user["user_id"]}))
    
    if not meals:
        return {
            "total_meals": 0,
            "meals_this_week": 0,
            "meals_this_month": 0,
            "current_streak": 0,
            "meal_times": [],
            "weekly_trend": []
        }
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    meals_this_week = sum(1 for m in meals if datetime.fromisoformat(m["timestamp"]) >= week_ago)
    meals_this_month = sum(1 for m in meals if datetime.fromisoformat(m["timestamp"]) >= month_ago)
    
    # Analyze meal times
    meal_hours = [datetime.fromisoformat(m["timestamp"]).hour for m in meals]
    hour_counts = Counter(meal_hours)
    most_common_hours = hour_counts.most_common(3)
    
    # Weekly trend (last 7 days)
    weekly_data = []
    for i in range(7):
        day = now - timedelta(days=6-i)
        day_date = day.date()
        day_meals = sum(1 for m in meals if datetime.fromisoformat(m["timestamp"]).date() == day_date)
        weekly_data.append({
            "date": day_date.isoformat(),
            "day_name": day.strftime("%a"),
            "meals": day_meals
        })
    
    return {
        "total_meals": len(meals),
        "meals_this_week": meals_this_week,
        "meals_this_month": meals_this_month,
        "current_streak": calculate_streak(user["user_id"]),
        "meal_times": [{"hour": h, "count": c} for h, c in most_common_hours],
        "weekly_trend": weekly_data
    }

@app.post("/api/progress-photos")
def upload_progress_photo(photo_data: ProgressPhoto, user = Depends(get_current_user)):
    photo_id = str(uuid.uuid4())
    photo = {
        "photo_id": photo_id,
        "user_id": user["user_id"],
        "image_base64": photo_data.image_base64,
        "weight": photo_data.weight,
        "notes": photo_data.notes,
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    progress_photos_collection.insert_one(photo)
    
    return {
        "photo_id": photo_id,
        "message": "Progress photo uploaded successfully!"
    }

@app.get("/api/progress-photos")
def get_progress_photos(user = Depends(get_current_user)):
    photos = list(progress_photos_collection.find({"user_id": user["user_id"]}).sort("timestamp", 1))
    
    for photo in photos:
        photo.pop('_id', None)
    
    return {"photos": photos}

@app.delete("/api/progress-photos/{photo_id}")
def delete_progress_photo(photo_id: str, user = Depends(get_current_user)):
    photo = progress_photos_collection.find_one({"photo_id": photo_id})
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    if photo["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    progress_photos_collection.delete_one({"photo_id": photo_id})
    return {"message": "Photo deleted successfully"}

@app.post("/api/meals")
async def create_meal(meal_data: MealCreate, user = Depends(get_current_user)):
    nutrition_data = await analyze_food_image(meal_data.image_base64)
    
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
    
    # Check for new badges
    new_badges = check_and_award_badges(user["user_id"])
    
    if user["role"] == "user":
        response = {
            "meal_id": meal_id,
            "message": f"Great job logging your meal! 🎉 {nutrition_data.get('food_name', 'Your food')} looks delicious. Keep up the amazing work on your journey!",
            "food_name": nutrition_data.get('food_name', 'Unknown'),
            "timestamp": meal["timestamp"]
        }
        
        if new_badges:
            response["new_badges"] = [BADGES[b] for b in new_badges if b in BADGES]
            response["celebration"] = True
        
        return response
    else:
        return {
            "meal_id": meal_id,
            "nutrition": nutrition_data,
            "timestamp": meal["timestamp"]
        }

@app.get("/api/meals")
def get_meals(user = Depends(get_current_user)):
    meals = list(meals_collection.find({"user_id": user["user_id"]}).sort("timestamp", -1))
    
    for meal in meals:
        meal.pop('_id', None)
        
        if user["role"] == "user":
            meal.pop('nutrition', None)
    
    return {"meals": meals}

@app.get("/api/meals/{meal_id}")
def get_meal(meal_id: str, user = Depends(get_current_user)):
    meal = meals_collection.find_one({"meal_id": meal_id})
    
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    if meal["user_id"] != user["user_id"] and user["role"] != "coach":
        raise HTTPException(status_code=403, detail="Access denied")
    
    meal.pop('_id', None)
    
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
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
        "avg_calories_per_meal": total_calories / len(meals) if meals else 0,
        "current_streak": calculate_streak(user_id)
    }

@app.get("/api/coach/users/{user_id}/analytics")
def get_user_analytics(user_id: str, coach = Depends(require_coach)):
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    meals = list(meals_collection.find({"user_id": user_id}))
    
    if not meals:
        return {
            "total_meals": 0,
            "meals_this_week": 0,
            "current_streak": 0,
            "weekly_trend": []
        }
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    meals_this_week = sum(1 for m in meals if datetime.fromisoformat(m["timestamp"]) >= week_ago)
    
    # Weekly trend
    weekly_data = []
    for i in range(7):
        day = now - timedelta(days=6-i)
        day_date = day.date()
        day_meals = sum(1 for m in meals if datetime.fromisoformat(m["timestamp"]).date() == day_date)
        weekly_data.append({
            "date": day_date.isoformat(),
            "day_name": day.strftime("%a"),
            "meals": day_meals
        })
    
    return {
        "total_meals": len(meals),
        "meals_this_week": meals_this_week,
        "current_streak": calculate_streak(user_id),
        "weekly_trend": weekly_data
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
