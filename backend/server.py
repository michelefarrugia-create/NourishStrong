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
import re
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
weight_logs_collection = db['weight_logs']
password_reset_tokens_collection = db['password_reset_tokens']

# JWT settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-2F8757d69949133Ef3')

# SendGrid settings
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')

# Badge definitions
BADGES = {
    "first_meal": {"name": "First Meal", "description": "Logged your first meal", "icon": "🎯", "points": 50},
    "5_meals": {"name": "Getting Started", "description": "Logged 5 meals", "icon": "🌟", "points": 25},
    "10_meals": {"name": "Building Momentum", "description": "Logged 10 meals", "icon": "🚀", "points": 50},
    "25_meals": {"name": "Consistency", "description": "Logged 25 meals", "icon": "💪", "points": 100},
    "50_meals": {"name": "Halfway Hero", "description": "Logged 50 meals", "icon": "🎖️", "points": 200},
    "100_meals": {"name": "Century Club", "description": "Logged 100 meals", "icon": "🏆", "points": 500},
    "250_meals": {"name": "Elite Tracker", "description": "Logged 250 meals", "icon": "💎", "points": 1000},
    "streak_7": {"name": "Week Warrior", "description": "7-day streak", "icon": "🔥", "points": 100},
    "streak_14": {"name": "Fortnight Champion", "description": "14-day streak", "icon": "🔥🔥", "points": 250},
    "streak_30": {"name": "Month Master", "description": "30-day streak", "icon": "⭐", "points": 500},
    "streak_60": {"name": "Unstoppable", "description": "60-day streak", "icon": "⚡", "points": 1000},
    "streak_100": {"name": "Legendary", "description": "100-day streak", "icon": "👑", "points": 2000},
    "early_bird": {"name": "Early Bird", "description": "Logged breakfast before 9am", "icon": "🌅", "points": 20},
    "consistent": {"name": "Consistency King", "description": "Logged 3 meals in one day", "icon": "👑", "points": 30},
    "mood_master": {"name": "Mood Master", "description": "Tracked mood for 10 meals", "icon": "😊", "points": 50},
    "challenge_10": {"name": "Challenge Seeker", "description": "Completed 10 challenges", "icon": "🎯", "points": 100},
}

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
    # Mood journal fields
    before_mood: Optional[str] = None  # "happy", "neutral", "low"
    before_energy: Optional[str] = None  # "energized", "moderate", "tired"
    hunger_level: Optional[int] = None  # 1-10: 1=starving, 10=not hungry
    after_mood: Optional[str] = None  # "happy", "neutral", "low"
    after_energy: Optional[str] = None  # "energized", "moderate", "tired"
    satisfaction_level: Optional[int] = None  # 1-10: 1=very full, 10=still hungry

class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    activity_level: Optional[str] = None
    goal_weight: Optional[float] = None
    profile_picture: Optional[str] = None  # base64 image

class WeightLog(BaseModel):
    weight: float
    notes: Optional[str] = ""

class CoachAssignment(BaseModel):
    coach_email: str

class ProgressPhoto(BaseModel):
    image_base64: str
    weight: Optional[float] = None
    notes: Optional[str] = ""

class DailyChallengeComplete(BaseModel):
    challenge_id: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

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
    except Exception:
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

def validate_password_strength(password: str) -> dict:
    """
    Validate password strength
    Returns: {"valid": bool, "message": str, "strength": str}
    """
    if len(password) < 8:
        return {"valid": False, "message": "Password must be at least 8 characters long", "strength": "weak"}
    
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    strength_count = sum([has_upper, has_lower, has_digit, has_special])
    
    if strength_count < 3:
        missing = []
        if not has_upper:
            missing.append("uppercase letter")
        if not has_lower:
            missing.append("lowercase letter")
        if not has_digit:
            missing.append("number")
        if not has_special:
            missing.append("special character")
        
        return {
            "valid": False, 
            "message": f"Password must contain at least 3 of: uppercase, lowercase, number, special character. Missing: {', '.join(missing[:2])}",
            "strength": "weak"
        }
    
    if strength_count == 3:
        return {"valid": True, "message": "Password strength: Good", "strength": "good"}
    else:
        return {"valid": True, "message": "Password strength: Strong", "strength": "strong"}

def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send email using SendGrid"""
    try:
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code in [200, 201, 202]
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_welcome_email(user_email: str, user_name: str) -> bool:
    """Send welcome email to new users"""
    subject = "Welcome to NourishStrong! 🎉"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2D5F3F; text-align: center;">Welcome to NourishStrong! 🌱</h1>
                <p>Hi {user_name},</p>
                <p>We're thrilled to have you join our community! Your journey to a healthier, stronger you starts today.</p>
                
                <div style="background-color: #f4f4f4; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h2 style="color: #2D5F3F; margin-top: 0;">Getting Started:</h2>
                    <ul style="padding-left: 20px;">
                        <li>📸 Log your first meal by taking a photo</li>
                        <li>💪 Track your daily activities</li>
                        <li>🎯 Complete daily challenges</li>
                        <li>🏆 Earn badges for your achievements</li>
                    </ul>
                </div>
                
                <p>Remember: Progress, not perfection. Every small step counts!</p>
                
                <p style="margin-top: 30px;">Stay strong,<br>
                <strong>The NourishStrong Team</strong></p>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #888; font-size: 12px;">
                    <p>You're receiving this email because you signed up for NourishStrong.</p>
                </div>
            </div>
        </body>
    </html>
    """
    return send_email(user_email, subject, html_content)

def send_password_reset_email(user_email: str, user_name: str, reset_token: str) -> bool:
    """Send password reset email"""
    # In production, this should be the actual frontend URL
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    
    subject = "Reset Your NourishStrong Password"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2D5F3F; text-align: center;">Password Reset Request</h1>
                <p>Hi {user_name},</p>
                <p>We received a request to reset your password for your NourishStrong account.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #2D5F3F; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="background-color: #f4f4f4; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px;">
                    {reset_link}
                </p>
                
                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #856404;">
                        <strong>⚠️ Security Note:</strong> This link will expire in 1 hour. 
                        If you didn't request this reset, please ignore this email.
                    </p>
                </div>
                
                <p style="margin-top: 30px;">Stay strong,<br>
                <strong>The NourishStrong Team</strong></p>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #888; font-size: 12px;">
                    <p>You're receiving this email because a password reset was requested for your account.</p>
                </div>
            </div>
        </body>
    </html>
    """
    return send_email(user_email, subject, html_content)

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
    
    # Check badge conditions
    if meal_count >= 1 and "first_meal" not in current_badges:
        new_badges.append("first_meal")
    
    if meal_count >= 5 and "5_meals" not in current_badges:
        new_badges.append("5_meals")
    
    if meal_count >= 10 and "10_meals" not in current_badges:
        new_badges.append("10_meals")
    
    if meal_count >= 25 and "25_meals" not in current_badges:
        new_badges.append("25_meals")
    
    if meal_count >= 50 and "50_meals" not in current_badges:
        new_badges.append("50_meals")
    
    if meal_count >= 100 and "100_meals" not in current_badges:
        new_badges.append("100_meals")
    
    if meal_count >= 250 and "250_meals" not in current_badges:
        new_badges.append("250_meals")
    
    if streak >= 7 and "streak_7" not in current_badges:
        new_badges.append("streak_7")
    
    if streak >= 14 and "streak_14" not in current_badges:
        new_badges.append("streak_14")
    
    if streak >= 30 and "streak_30" not in current_badges:
        new_badges.append("streak_30")
    
    if streak >= 60 and "streak_60" not in current_badges:
        new_badges.append("streak_60")
    
    if streak >= 100 and "streak_100" not in current_badges:
        new_badges.append("streak_100")
    
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
    
    # Check for mood master (10 meals with mood tracking)
    meals_with_mood = sum(1 for meal in meals if meal.get("before_mood") or meal.get("after_mood"))
    if meals_with_mood >= 10 and "mood_master" not in current_badges:
        new_badges.append("mood_master")
    
    # Check for challenge seeker (10 completed challenges)
    completed_challenges = challenges_collection.count_documents({"user_id": user_id, "completed": True})
    if completed_challenges >= 10 and "challenge_10" not in current_badges:
        new_badges.append("challenge_10")
    
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
    """Analyze food image using GPT-4o with enhanced accuracy for nutrition estimation"""
    try:
        # Create chat instance with enhanced system message
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"food-analysis-{uuid.uuid4()}",
            system_message="""You are an expert nutritionist and dietitian with advanced training in visual portion estimation and nutritional analysis. 

Your task is to provide highly accurate nutrition estimates (within 2% margin of error) by:
1. Carefully identifying all visible food items
2. Estimating portion sizes using visual reference points (plate size, utensil comparison, food density)
3. Considering cooking methods that affect caloric content (fried vs grilled, oil usage, etc.)
4. Accounting for hidden ingredients (sauces, dressings, oils, butter)
5. Using standardized nutritional databases (USDA) for calculations

Be extremely precise and detailed in your analysis."""
        ).with_model("openai", "gpt-4o")
        
        # Create image content
        image_content = ImageContent(image_base64=image_base64)
        
        # Enhanced prompt for better accuracy
        user_message = UserMessage(
            text="""Analyze this food image with EXTREME PRECISION and provide nutritional information.

CRITICAL INSTRUCTIONS:
1. IDENTIFY all food items visible in the image
2. ESTIMATE portion sizes by:
   - Comparing to standard plate size (usually 10-11 inches)
   - Using visible utensils as reference (fork/spoon typically 6-7 inches)
   - Considering food density and volume
   - Identifying serving containers (cup, bowl, plate dimensions)

3. CALCULATE calories and macros by:
   - Using USDA nutritional database standards
   - Accounting for cooking methods (fried adds 50-100 cal, oil/butter adds ~120 cal per tbsp)
   - Including hidden ingredients (sauces, dressings, cooking fats)
   - Considering preparation style (restaurant portions are typically 1.5-2x home portions)

4. PROVIDE confidence level based on:
   - "high" = All items clearly visible, standard preparations
   - "medium" = Some items partially obscured or mixed dishes
   - "low" = Complex dishes with many hidden ingredients

Respond with ONLY this JSON format (no markdown, no explanations):
{
  "food_name": "specific dish name",
  "items_identified": ["item 1", "item 2"],
  "calories": exact_number,
  "protein": exact_grams,
  "carbs": exact_grams,
  "fats": exact_grams,
  "fiber": exact_grams,
  "portion_size": "detailed portion description with measurements",
  "portion_weight": estimated_grams,
  "confidence": "high/medium/low",
  "analysis_notes": "brief explanation of estimation method"
}

Be as accurate as possible. This is for health tracking.""",
            file_contents=[image_content]
        )
        
        # Get response
        response = await chat.send_message(user_message)
        print(f"Enhanced AI nutrition analysis: {response}")
        
        import json
        import re
        
        # Clean and parse response
        response_text = response.strip()
        
        # Extract JSON using regex
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        if json_matches:
            # Take the largest JSON match (most complete)
            response_text = max(json_matches, key=len)
        else:
            # Fallback: remove markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
        
        nutrition_data = json.loads(response_text)
        
        # Validate and ensure required fields
        required_fields = ["food_name", "calories", "protein", "carbs", "fats"]
        for field in required_fields:
            if field not in nutrition_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Add default values for optional fields
        nutrition_data.setdefault("fiber", 0)
        nutrition_data.setdefault("portion_weight", 0)
        nutrition_data.setdefault("confidence", "medium")
        nutrition_data.setdefault("portion_size", "1 serving")
        nutrition_data.setdefault("items_identified", [nutrition_data["food_name"]])
        nutrition_data.setdefault("analysis_notes", "Standard nutritional analysis")
        
        print(f"Successfully parsed enhanced nutrition data: {nutrition_data}")
        return nutrition_data
        
    except Exception as e:
        print(f"Error analyzing food image: {str(e)}")
        print(f"Raw response was: {response if 'response' in locals() else 'No response received'}")
        
        # Return realistic default values if analysis fails
        return {
            "food_name": "Mixed meal",
            "items_identified": ["Unknown items"],
            "calories": 350,
            "protein": 25,
            "carbs": 40,
            "fats": 12,
            "fiber": 5,
            "portion_size": "1 serving",
            "portion_weight": 250,
            "confidence": "low",
            "analysis_notes": "Analysis failed - using estimated values",
            "error": str(e)
        }

# Routes
@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/auth/register")
def register(user_data: UserRegister):
    # Validate password strength
    password_validation = validate_password_strength(user_data.password)
    if not password_validation["valid"]:
        raise HTTPException(status_code=400, detail=password_validation["message"])
    
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
        "streak_record": 0,
        "points": 0,
        "total_points_earned": 0
    }
    users_collection.insert_one(user)
    
    token = create_token(user_id, user_data.email, user_data.role)
    
    # Send welcome email (don't block registration if email fails)
    try:
        send_welcome_email(user_data.email, user_data.name)
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")
    
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

@app.post("/api/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest):
    """Send password reset email"""
    user = users_collection.find_one({"email": request.email})
    
    # Don't reveal if email exists or not for security
    if not user:
        return {"message": "If an account with that email exists, a password reset link has been sent."}
    
    # Generate reset token
    reset_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    # Store reset token
    password_reset_tokens_collection.insert_one({
        "token": reset_token,
        "user_id": user["user_id"],
        "email": request.email,
        "expires_at": expires_at.isoformat(),
        "used": False,
        "created_at": datetime.utcnow().isoformat()
    })
    
    # Send reset email
    try:
        send_password_reset_email(request.email, user["name"], reset_token)
    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")
    
    return {"message": "If an account with that email exists, a password reset link has been sent."}

@app.post("/api/auth/reset-password")
def reset_password(request: ResetPasswordRequest):
    """Reset password using token"""
    # Validate password strength
    password_validation = validate_password_strength(request.new_password)
    if not password_validation["valid"]:
        raise HTTPException(status_code=400, detail=password_validation["message"])
    
    # Find and validate token
    token_doc = password_reset_tokens_collection.find_one({"token": request.token})
    
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    if token_doc["used"]:
        raise HTTPException(status_code=400, detail="This reset link has already been used")
    
    # Check if token is expired
    expires_at = datetime.fromisoformat(token_doc["expires_at"])
    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Update user password
    users_collection.update_one(
        {"user_id": token_doc["user_id"]},
        {"$set": {"password": hash_password(request.new_password)}}
    )
    
    # Mark token as used
    password_reset_tokens_collection.update_one(
        {"token": request.token},
        {"$set": {"used": True, "used_at": datetime.utcnow().isoformat()}}
    )
    
    return {"message": "Password has been reset successfully"}

@app.get("/api/auth/validate-password")
def validate_password(password: str):
    """Validate password strength - for frontend real-time feedback"""
    return validate_password_strength(password)

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
    # Don't allow weight in user profile
    update_data = profile_data.dict(exclude_none=True)
    update_data.pop('weight', None)  # Remove weight if somehow included
    
    users_collection.update_one(
        {" user_id": user["user_id"]},
        {"$set": {"profile": update_data}}
    )
    return {"message": "Profile updated successfully"}

@app.post("/api/coach/users/{user_id}/weight")
def log_client_weight(user_id: str, weight_data: WeightLog, coach = Depends(require_coach)):
    """Coach logs weight for a client"""
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    weight_log_id = str(uuid.uuid4())
    weight_log = {
        "log_id": weight_log_id,
        "user_id": user_id,
        "coach_id": coach["user_id"],
        "weight": weight_data.weight,
        "notes": weight_data.notes,
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    weight_logs_collection.insert_one(weight_log)
    
    return {
        "log_id": weight_log_id,
        "message": "Weight logged successfully",
        "weight": weight_data.weight
    }

@app.get("/api/coach/users/{user_id}/weight-history")
def get_client_weight_history(user_id: str, coach = Depends(require_coach)):
    """Get weight history for a client"""
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    weight_logs = list(weight_logs_collection.find({"user_id": user_id}).sort("timestamp", -1))
    
    for log in weight_logs:
        log.pop('_id', None)
    
    return {"weight_logs": weight_logs}

@app.delete("/api/coach/users/{user_id}/weight/{log_id}")
def delete_weight_log(user_id: str, log_id: str, coach = Depends(require_coach)):
    """Delete a weight log"""
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    weight_logs_collection.delete_one({"log_id": log_id, "user_id": user_id})
    return {"message": "Weight log deleted successfully"}

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
        "created_at": datetime.utcnow().isoformat(),
        # Mood journal fields
        "before_mood": meal_data.before_mood,
        "before_energy": meal_data.before_energy,
        "hunger_level": meal_data.hunger_level,
        "after_mood": meal_data.after_mood,
        "after_energy": meal_data.after_energy,
        "satisfaction_level": meal_data.satisfaction_level
    }
    meals_collection.insert_one(meal)
    
    # Award points for logging meal
    points_earned = 10
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {
            "$inc": {
                "points": points_earned,
                "total_points_earned": points_earned
            }
        }
    )
    
    # Check for new badges
    new_badges = check_and_award_badges(user["user_id"])
    
    # Award points for new badges
    if new_badges:
        badge_points = sum(BADGES[b].get("points", 0) for b in new_badges if b in BADGES)
        if badge_points > 0:
            users_collection.update_one(
                {"user_id": user["user_id"]},
                {
                    "$inc": {
                        "points": badge_points,
                        "total_points_earned": badge_points
                    }
                }
            )
            points_earned += badge_points
    
    if user["role"] == "user":
        response = {
            "meal_id": meal_id,
            "message": f"Great job logging your meal! 🎉 {nutrition_data.get('food_name', 'Your food')} looks delicious. Keep up the amazing work on your journey!",
            "food_name": nutrition_data.get('food_name', 'Unknown'),
            "timestamp": meal["timestamp"],
            "points_earned": points_earned
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

# Activity endpoints removed - missing required collections and constants

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
