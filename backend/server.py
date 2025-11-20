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
db = client['nourishstrong_app']
users_collection = db['users']
meals_collection = db['meals']
challenges_collection = db['challenges']
body_prompts_collection = db['body_prompts']
password_reset_tokens_collection = db['password_reset_tokens']
movement_collection = db['movement']
sensory_logs_collection = db['sensory_logs']
values_goals_collection = db['values_goals']
restaurant_prep_collection = db['restaurant_prep']
body_appreciation_collection = db['body_appreciation']

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
    
    # Movement badges (joy-focused, not performance)
    "first_movement": {"name": "First Move", "description": "Logged your first movement", "icon": "✨", "points": 50},
    "joy_explorer": {"name": "Joy Explorer", "description": "Tried 5 different movement types", "icon": "🌈", "points": 100},
    "rest_advocate": {"name": "Rest Advocate", "description": "Honored rest 5 times", "icon": "🌙", "points": 100},
    "social_mover": {"name": "Social Butterfly", "description": "5 social movement activities", "icon": "🦋", "points": 75},
    "body_listener": {"name": "Body Listener", "description": "Honored what your body craved 10 times", "icon": "💚", "points": 150},
    "mindful_mover": {"name": "Mindful Mover", "description": "10 mindful movement sessions", "icon": "🧘", "points": 100},
    "movement_variety": {"name": "Variety Champion", "description": "Logged 10 different movement types", "icon": "🎨", "points": 200},
    
    # Sensory eating badges
    "sensory_explorer": {"name": "Sensory Explorer", "description": "Tracked sensory experience for 10 meals", "icon": "👅", "points": 75},
    "texture_lover": {"name": "Texture Lover", "description": "Explored 5 different textures", "icon": "🥕", "points": 50},
    
    # Values-based badges
    "values_aligned": {"name": "Values Aligned", "description": "Created your first value-based goal", "icon": "🎯", "points": 100},
    "intention_keeper": {"name": "Intention Keeper", "description": "Logged 10 behavior intentions", "icon": "💫", "points": 150},
    
    # Social eating badges
    "social_navigator": {"name": "Social Navigator", "description": "Prepared for 5 social eating events", "icon": "🍽️", "points": 100},
    "body_listener_social": {"name": "Social Body Listener", "description": "Honored body at 10 social events", "icon": "🎉", "points": 150},
    
    # Body appreciation badges
    "gratitude_keeper": {"name": "Gratitude Keeper", "description": "Logged 10 body appreciation moments", "icon": "🙏", "points": 100},
    "function_focused": {"name": "Function Focused", "description": "20 body function appreciations", "icon": "✨", "points": 200},
}

# Body-positive affirmations and prompts
BODY_HONOR_PROMPTS = [
    {"quote": "What did your body do for you today? 💚", "category": "body-positive"},
    {"quote": "Your body deserves nourishment and rest. Both are equally important. 🌙", "category": "body-positive"},
    {"quote": "Moving or resting - whatever your body needs is perfect. ✨", "category": "body-positive"},
    {"quote": "Every body is a good body, including yours. 🌟", "category": "body-positive"},
    {"quote": "Listen to your body's wisdom today. It knows what it needs. 🧘", "category": "body-positive"},
    {"quote": "Your worth isn't measured by what you eat or how you move. 💫", "category": "body-positive"},
    {"quote": "Honor your hunger. Honor your fullness. Honor yourself. 🌸", "category": "body-positive"},
    {"quote": "Rest is not laziness. Rest is self-care. 😴", "category": "body-positive"},
    {"quote": "Your body is your home. Treat it with kindness. 🏡", "category": "body-positive"},
    {"quote": "Thank your body for all it does, not how it looks. 🙏", "category": "body-positive"},
    {"quote": "Gentle movement can feel as good as rest. Trust what you need. 🌊", "category": "body-positive"},
    {"quote": "You deserve to eat foods that bring you joy and satisfaction. 🍽️", "category": "body-positive"},
    {"quote": "Your body's signals are valid. You are the expert on you. 💭", "category": "body-positive"},
    {"quote": "Healing your relationship with your body is a journey, not a race. 🛤️", "category": "body-positive"},
    {"quote": "What if you treated your body like a friend today? 🤝", "category": "body-positive"}
]

MOTIVATIONAL_QUOTES = BODY_HONOR_PROMPTS  # Keep for backward compatibility

# Sensory eating options
SENSORY_OPTIONS = {
    "textures": [
        {"id": "crunchy", "name": "Crunchy", "icon": "🥕"},
        {"id": "smooth", "name": "Smooth", "icon": "🍦"},
        {"id": "chewy", "name": "Chewy", "icon": "🍪"},
        {"id": "soft", "name": "Soft", "icon": "🍞"},
        {"id": "crispy", "name": "Crispy", "icon": "🥓"},
        {"id": "creamy", "name": "Creamy", "icon": "🧈"},
        {"id": "tender", "name": "Tender", "icon": "🥩"},
        {"id": "firm", "name": "Firm", "icon": "🥒"}
    ],
    "flavors": [
        {"id": "sweet", "name": "Sweet", "icon": "🍯"},
        {"id": "salty", "name": "Salty", "icon": "🧂"},
        {"id": "sour", "name": "Sour", "icon": "🍋"},
        {"id": "bitter", "name": "Bitter", "icon": "☕"},
        {"id": "umami", "name": "Umami/Savory", "icon": "🍄"},
        {"id": "spicy", "name": "Spicy", "icon": "🌶️"}
    ],
    "temperatures": [
        {"id": "hot", "name": "Hot", "icon": "♨️"},
        {"id": "warm", "name": "Warm", "icon": "🌡️"},
        {"id": "room_temp", "name": "Room Temperature", "icon": "🌿"},
        {"id": "cold", "name": "Cold", "icon": "🧊"},
        {"id": "frozen", "name": "Frozen", "icon": "❄️"}
    ]
}

# Values for goal-setting
WELLNESS_VALUES = [
    {"id": "play", "name": "Play & Fun", "description": "Bringing lightness and joy to life", "icon": "🎈"},
    {"id": "rest", "name": "Rest & Recovery", "description": "Honoring body's need for restoration", "icon": "🌙"},
    {"id": "connection", "name": "Connection & Community", "description": "Building meaningful relationships", "icon": "🤝"},
    {"id": "joy", "name": "Joy & Pleasure", "description": "Finding delight in daily experiences", "icon": "😊"},
    {"id": "creativity", "name": "Creativity & Expression", "description": "Expressing yourself authentically", "icon": "🎨"},
    {"id": "peace", "name": "Peace & Calm", "description": "Cultivating inner tranquility", "icon": "☮️"},
    {"id": "strength", "name": "Strength & Capability", "description": "Appreciating what your body can do", "icon": "💪"},
    {"id": "curiosity", "name": "Curiosity & Learning", "description": "Exploring and discovering", "icon": "🔍"},
    {"id": "self_compassion", "name": "Self-Compassion", "description": "Treating yourself with kindness", "icon": "💚"},
    {"id": "freedom", "name": "Freedom & Autonomy", "description": "Making choices aligned with your needs", "icon": "🕊️"}
]

# Body appreciation categories
APPRECIATION_CATEGORIES = [
    {"id": "strength", "name": "Strength & Power", "icon": "💪"},
    {"id": "movement", "name": "Movement & Mobility", "icon": "🚶"},
    {"id": "creation", "name": "Creation & Making", "icon": "✋"},
    {"id": "connection", "name": "Connection & Touch", "icon": "🤗"},
    {"id": "senses", "name": "Senses & Perception", "icon": "👁️"},
    {"id": "healing", "name": "Healing & Recovery", "icon": "🩹"}
]

# Joyful movement types (no performance metrics)
MOVEMENT_TYPES = [
    {"id": "walking", "name": "Walking", "icon": "🚶", "category": "joyful"},
    {"id": "stretching", "name": "Stretching", "icon": "🧘", "category": "gentle"},
    {"id": "dancing", "name": "Dancing", "icon": "💃", "category": "joyful"},
    {"id": "playing", "name": "Playing (kids/pets)", "icon": "🎾", "category": "playful"},
    {"id": "gardening", "name": "Gardening", "icon": "🌱", "category": "joyful"},
    {"id": "cleaning", "name": "Active Cleaning", "icon": "🏠", "category": "joyful"},
    {"id": "swimming", "name": "Swimming", "icon": "🏊", "category": "joyful"},
    {"id": "hiking", "name": "Hiking", "icon": "🥾", "category": "nature"},
    {"id": "biking", "name": "Biking", "icon": "🚴", "category": "joyful"},
    {"id": "yoga", "name": "Yoga", "icon": "🧘‍♀️", "category": "mindful"},
    {"id": "tai_chi", "name": "Tai Chi", "icon": "☯️", "category": "mindful"},
    {"id": "sports", "name": "Sports/Games", "icon": "⚽", "category": "playful"},
    {"id": "social_walk", "name": "Social Walk", "icon": "👫", "category": "social"},
    {"id": "group_class", "name": "Group Class", "icon": "👥", "category": "social"},
    {"id": "rest", "name": "Honoring Rest", "icon": "🌙", "category": "rest"},
    {"id": "other", "name": "Other Movement", "icon": "✨", "category": "joyful"}
]

# Movement intentions (why, not how)
MOVEMENT_INTENTIONS = [
    {"id": "joy", "name": "For Joy", "icon": "😊"},
    {"id": "stress_relief", "name": "Stress Relief", "icon": "🌊"},
    {"id": "connection", "name": "Social Connection", "icon": "🤝"},
    {"id": "felt_good", "name": "It Felt Good", "icon": "✨"},
    {"id": "nature", "name": "To Be in Nature", "icon": "🌳"},
    {"id": "play", "name": "To Play", "icon": "🎈"},
    {"id": "clear_head", "name": "Clear My Head", "icon": "💭"},
    {"id": "body_asked", "name": "My Body Asked For It", "icon": "💚"}
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

class MovementLog(BaseModel):
    # Movement Mood Journal
    before_mood: Optional[str] = None  # "happy", "neutral", "stressed", "tired"
    before_energy: Optional[str] = None  # "energized", "moderate", "drained"
    
    # Movement type and details
    movement_type: str  # from predefined list or custom
    movement_category: Optional[str] = None  # "joyful", "social", "rest", "mindful"
    
    # Body sensations and intentions
    body_craving: Optional[str] = None  # what body wanted
    movement_intention: Optional[str] = None  # "joy", "stress relief", "connection", "felt good"
    
    # After movement
    after_mood: Optional[str] = None
    after_energy: Optional[str] = None  # did it energize or exhaust?
    
    # Mindfulness
    was_present: Optional[bool] = None  # were you mindful during movement?
    
    # Social aspect
    was_social: Optional[bool] = None
    social_with: Optional[str] = None  # "friend", "family", "group", etc.
    
    # Body gratitude
    body_gratitude: Optional[str] = None  # "what did your body do for you?"
    
    # Rest flag
    is_rest_day: bool = False  # celebrating rest
    
    notes: Optional[str] = ""

class SensoryMealLog(BaseModel):
    meal_id: str  # Link to existing meal
    textures: Optional[List[str]] = []  # "crunchy", "smooth", "chewy", "soft", "crispy"
    flavors: Optional[List[str]] = []  # "sweet", "salty", "sour", "bitter", "umami", "spicy"
    temperatures: Optional[List[str]] = []  # "hot", "warm", "room temp", "cold", "frozen"
    satisfaction_rating: Optional[int] = None  # 1-10 (sensory satisfaction, not fullness)
    sensory_variety: Optional[bool] = None  # Did meal have variety?
    most_satisfying_aspect: Optional[str] = None  # What sensory aspect satisfied most?
    notes: Optional[str] = ""

class ValueBasedGoal(BaseModel):
    value_name: str  # "play", "rest", "connection", "joy", "creativity", "peace"
    value_description: str  # Why this value matters to user
    behavior_intentions: List[str]  # Specific behaviors aligned with value
    # NOT outcome-based: no weight, size, shape goals allowed

class RestaurantPrepLog(BaseModel):
    event_type: str  # "restaurant", "family_dinner", "work_event", "date", "party"
    before_intention: Optional[str] = None  # "How do I want to feel?"
    before_concerns: Optional[str] = None  # Anxieties or worries
    during_checkin: Optional[str] = None  # "Am I listening to my body?"
    after_reflection: Optional[str] = None  # "How did it go?"
    learned: Optional[str] = None  # Key learning
    honored_body: Optional[bool] = None  # Did you listen to body cues?
    event_date: Optional[str] = None  # When is/was the event

class BodyAppreciationLog(BaseModel):
    image_base64: Optional[str] = None  # Optional photo
    body_function: str  # "My legs carried me on a walk"
    appreciation_note: str  # What you're grateful for
    category: str  # "strength", "movement", "creation", "connection", "senses", "healing"

class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    wellness_vision: Optional[str] = None  # Replaced goal_weight
    profile_picture: Optional[str] = None  # base64 image

class CoachAssignment(BaseModel):
    coach_email: str

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
    
    # Movement badges
    movements = list(movement_collection.find({"user_id": user_id}))
    movement_count = len(movements)
    
    if movement_count >= 1 and "first_movement" not in current_badges:
        new_badges.append("first_movement")
    
    # Joy explorer - 5 different movement types
    movement_types = set(m.get("movement_type") for m in movements if m.get("movement_type"))
    if len(movement_types) >= 5 and "joy_explorer" not in current_badges:
        new_badges.append("joy_explorer")
    
    if len(movement_types) >= 10 and "movement_variety" not in current_badges:
        new_badges.append("movement_variety")
    
    # Rest advocate - honored rest 5 times
    rest_count = sum(1 for m in movements if m.get("is_rest_day"))
    if rest_count >= 5 and "rest_advocate" not in current_badges:
        new_badges.append("rest_advocate")
    
    # Social mover - 5 social movements
    social_count = sum(1 for m in movements if m.get("was_social"))
    if social_count >= 5 and "social_mover" not in current_badges:
        new_badges.append("social_mover")
    
    # Body listener - honored body cravings 10 times
    body_craving_count = sum(1 for m in movements if m.get("body_craving"))
    if body_craving_count >= 10 and "body_listener" not in current_badges:
        new_badges.append("body_listener")
    
    # Mindful mover - 10 mindful sessions
    mindful_count = sum(1 for m in movements if m.get("was_present"))
    if mindful_count >= 10 and "mindful_mover" not in current_badges:
        new_badges.append("mindful_mover")
    
    # Sensory eating badges
    sensory_logs = list(sensory_logs_collection.find({"user_id": user_id}))
    if len(sensory_logs) >= 10 and "sensory_explorer" not in current_badges:
        new_badges.append("sensory_explorer")
    
    all_textures = set()
    for log in sensory_logs:
        if log.get("textures"):
            all_textures.update(log.get("textures", []))
    if len(all_textures) >= 5 and "texture_lover" not in current_badges:
        new_badges.append("texture_lover")
    
    # Values-based badges
    values_goals = list(values_goals_collection.find({"user_id": user_id}))
    if len(values_goals) >= 1 and "values_aligned" not in current_badges:
        new_badges.append("values_aligned")
    
    total_intentions = sum(len(goal.get("behavior_intentions", [])) for goal in values_goals)
    if total_intentions >= 10 and "intention_keeper" not in current_badges:
        new_badges.append("intention_keeper")
    
    # Social eating badges
    restaurant_preps = list(restaurant_prep_collection.find({"user_id": user_id}))
    if len(restaurant_preps) >= 5 and "social_navigator" not in current_badges:
        new_badges.append("social_navigator")
    
    honored_count = sum(1 for prep in restaurant_preps if prep.get("honored_body"))
    if honored_count >= 10 and "body_listener_social" not in current_badges:
        new_badges.append("body_listener_social")
    
    # Body appreciation badges
    appreciations = list(body_appreciation_collection.find({"user_id": user_id}))
    if len(appreciations) >= 10 and "gratitude_keeper" not in current_badges:
        new_badges.append("gratitude_keeper")
    
    if len(appreciations) >= 20 and "function_focused" not in current_badges:
        new_badges.append("function_focused")
    
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
    
    # Create new invitation (not pressure-based challenge)
    challenges = [
        {"id": "notice_hunger", "title": "Notice Your Hunger", "description": "Check in with your hunger before eating today", "icon": "🧘"},
        {"id": "mindful_bite", "title": "Savor One Bite", "description": "Take one mindful bite today - notice taste, texture, satisfaction", "icon": "🌸"},
        {"id": "body_gratitude", "title": "Thank Your Body", "description": "What did your body do for you today?", "icon": "💚"},
        {"id": "joyful_movement", "title": "Move for Joy", "description": "Try movement that feels good (or rest if that's what you need)", "icon": "✨"},
        {"id": "honor_rest", "title": "Honor Rest", "description": "If you're tired, give yourself permission to rest", "icon": "🌙"},
        {"id": "food_neutrality", "title": "Food is Neutral", "description": "Remind yourself: all foods can fit", "icon": "🍽️"},
        {"id": "satisfaction_check", "title": "Satisfaction Check", "description": "Ask yourself: did this meal satisfy me?", "icon": "😊"},
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

@app.get("/api/meals/timing-insights")
def get_meal_timing_insights(user = Depends(get_current_user)):
    """Get meal timing patterns and insights"""
    meals = list(meals_collection.find({"user_id": user["user_id"]}))
    
    if len(meals) < 3:
        return {
            "insights": [],
            "typical_eating_window": None,
            "meal_frequency": None,
            "recommendations": ["Log more meals to see patterns"]
        }
    
    # Analyze meal times
    meal_times = []
    for meal in meals:
        timestamp = datetime.fromisoformat(meal["timestamp"])
        hour = timestamp.hour
        minute = timestamp.minute
        time_decimal = hour + minute / 60
        meal_times.append(time_decimal)
    
    meal_times.sort()
    
    # Calculate typical eating window
    if meal_times:
        first_meal_avg = sum([t for t in meal_times if t < 12]) / max(len([t for t in meal_times if t < 12]), 1)
        last_meal_avg = sum([t for t in meal_times if t > 12]) / max(len([t for t in meal_times if t > 12]), 1)
        
        first_meal_hour = int(first_meal_avg)
        first_meal_min = int((first_meal_avg - first_meal_hour) * 60)
        last_meal_hour = int(last_meal_avg)
        last_meal_min = int((last_meal_avg - last_meal_hour) * 60)
        
        eating_window = {
            "first_meal": f"{first_meal_hour:02d}:{first_meal_min:02d}",
            "last_meal": f"{last_meal_hour:02d}:{last_meal_min:02d}",
            "window_hours": round(last_meal_avg - first_meal_avg, 1)
        }
    else:
        eating_window = None
    
    # Calculate meal frequency
    total_days = (datetime.utcnow() - datetime.fromisoformat(meals[0]["timestamp"])).days + 1
    meal_frequency = round(len(meals) / max(total_days, 1), 1)
    
    # Generate insights
    insights = []
    if meal_frequency >= 3:
        insights.append("🌟 Excellent consistency! You're averaging 3+ meals per day")
    elif meal_frequency >= 2:
        insights.append("💪 Good frequency! Try to add one more meal per day")
    
    if eating_window and eating_window["window_hours"] < 8:
        insights.append("⏰ Your eating window is quite compressed. Consider spacing meals out more")
    elif eating_window and eating_window["window_hours"] > 14:
        insights.append("📅 Your eating window is quite long. Consider earlier dinners for better digestion")
    
    return {
        "insights": insights,
        "typical_eating_window": eating_window,
        "meal_frequency": meal_frequency,
        "total_meals": len(meals),
        "tracking_days": total_days
    }

@app.get("/api/progress/comparison")
def get_progress_comparison(user = Depends(get_current_user)):
    """Compare current week vs previous weeks"""
    meals = list(meals_collection.find({"user_id": user["user_id"]}))
    
    if len(meals) < 7:
        return {
            "message": "Need at least a week of data for comparison",
            "weeks_data": []
        }
    
    now = datetime.utcnow()
    weeks_data = []
    
    # Analyze last 4 weeks
    for week_offset in range(4):
        week_start = now - timedelta(days=7 * (week_offset + 1))
        week_end = now - timedelta(days=7 * week_offset)
        
        week_meals = [m for m in meals if week_start <= datetime.fromisoformat(m["timestamp"]) < week_end]
        
        # Count meals with mood tracking
        meals_with_mood = sum(1 for m in week_meals if m.get("before_mood") or m.get("after_mood"))
        
        # Calculate streak for that week (simplified)
        dates = set(datetime.fromisoformat(m["timestamp"]).date() for m in week_meals)
        
        weeks_data.append({
            "week_label": f"Week {4 - week_offset}",
            "start_date": week_start.date().isoformat(),
            "end_date": week_end.date().isoformat(),
            "total_meals": len(week_meals),
            "days_logged": len(dates),
            "meals_with_mood": meals_with_mood,
            "consistency_score": round((len(dates) / 7) * 100)
        })
    
    # Calculate improvements
    if len(weeks_data) >= 2:
        current_week = weeks_data[0]
        previous_week = weeks_data[1]
        
        improvements = {
            "meals": current_week["total_meals"] - previous_week["total_meals"],
            "days": current_week["days_logged"] - previous_week["days_logged"],
            "consistency": current_week["consistency_score"] - previous_week["consistency_score"]
        }
    else:
        improvements = None
    
    return {
        "weeks_data": weeks_data,
        "improvements": improvements,
        "trending_up": improvements["meals"] > 0 if improvements else None
    }

@app.get("/api/movement/types")
def get_movement_types():
    """Get all joyful movement types"""
    return {"movement_types": MOVEMENT_TYPES, "intentions": MOVEMENT_INTENTIONS}

@app.post("/api/movement")
def log_movement(movement_data: MovementLog, user = Depends(get_current_user)):
    """Log a joyful movement or rest day"""
    movement_id = str(uuid.uuid4())
    movement = {
        "movement_id": movement_id,
        "user_id": user["user_id"],
        "before_mood": movement_data.before_mood,
        "before_energy": movement_data.before_energy,
        "movement_type": movement_data.movement_type,
        "movement_category": movement_data.movement_category,
        "body_craving": movement_data.body_craving,
        "movement_intention": movement_data.movement_intention,
        "after_mood": movement_data.after_mood,
        "after_energy": movement_data.after_energy,
        "was_present": movement_data.was_present,
        "was_social": movement_data.was_social,
        "social_with": movement_data.social_with,
        "body_gratitude": movement_data.body_gratitude,
        "is_rest_day": movement_data.is_rest_day,
        "notes": movement_data.notes,
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    movement_collection.insert_one(movement)
    
    # Award points
    points_earned = 10 if not movement_data.is_rest_day else 15  # Extra points for honoring rest!
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"points": points_earned, "total_points_earned": points_earned}}
    )
    
    # Check for new badges
    new_badges = check_and_award_badges(user["user_id"])
    
    # Award badge points
    if new_badges:
        badge_points = sum(BADGES[b].get("points", 0) for b in new_badges if b in BADGES)
        if badge_points > 0:
            users_collection.update_one(
                {"user_id": user["user_id"]},
                {"$inc": {"points": badge_points, "total_points_earned": badge_points}}
            )
            points_earned += badge_points
    
    # Generate appropriate message
    if movement_data.is_rest_day:
        message = "Thank you for honoring your body's need for rest! 🌙 Rest is just as important as movement."
    else:
        movement_name = next((m["name"] for m in MOVEMENT_TYPES if m["id"] == movement_data.movement_type), "movement")
        message = f"Beautiful! {movement_name} sounds wonderful. 💚 Thank you for moving in a way that felt good."
    
    response = {
        "movement_id": movement_id,
        "message": message,
        "points_earned": points_earned,
        "timestamp": movement["timestamp"]
    }
    
    if new_badges:
        response["new_badges"] = [BADGES[b] for b in new_badges if b in BADGES]
        response["celebration"] = True
    
    return response

@app.get("/api/movement")
def get_movements(user = Depends(get_current_user)):
    """Get user's movement log"""
    movements = list(movement_collection.find({"user_id": user["user_id"]}).sort("timestamp", -1))
    
    for movement in movements:
        movement.pop('_id', None)
    
    return {"movements": movements}

@app.get("/api/movement/insights")
def get_movement_insights(user = Depends(get_current_user)):
    """Get personalized movement insights"""
    movements = list(movement_collection.find({"user_id": user["user_id"]}))
    
    if len(movements) < 3:
        return {
            "insights": ["Log a few movements to see your patterns! 💚"],
            "variety_count": 0,
            "rest_count": 0,
            "social_count": 0,
            "recommendations": []
        }
    
    # Analyze patterns
    movement_types = [m.get("movement_type") for m in movements if m.get("movement_type")]
    variety_count = len(set(movement_types))
    rest_count = sum(1 for m in movements if m.get("is_rest_day"))
    social_count = sum(1 for m in movements if m.get("was_social"))
    
    # Energy patterns
    energizing_movements = []
    exhausting_movements = []
    for m in movements:
        if m.get("before_energy") and m.get("after_energy"):
            energy_map = {"drained": 1, "moderate": 2, "energized": 3}
            before = energy_map.get(m.get("before_energy"), 2)
            after = energy_map.get(m.get("after_energy"), 2)
            if after > before:
                energizing_movements.append(m.get("movement_type"))
            elif after < before:
                exhausting_movements.append(m.get("movement_type"))
    
    # Most common energizing movement
    if energizing_movements:
        from collections import Counter
        most_energizing = Counter(energizing_movements).most_common(1)[0][0]
        energizing_name = next((m["name"] for m in MOVEMENT_TYPES if m["id"] == most_energizing), most_energizing)
    else:
        energizing_name = None
    
    # Generate insights
    insights = []
    if variety_count >= 5:
        insights.append(f"🌈 You've explored {variety_count} different types of movement! Beautiful variety.")
    
    if rest_count >= 3:
        insights.append(f"🌙 You've honored rest {rest_count} times. Your body thanks you!")
    
    if social_count >= 3:
        insights.append(f"🦋 You've enjoyed {social_count} social movement activities. Connection is powerful!")
    
    if energizing_name:
        insights.append(f"⚡ {energizing_name} tends to energize you. Your body knows what it needs!")
    
    # Recommendations
    recommendations = []
    if rest_count == 0:
        recommendations.append("Remember: rest is just as valid as movement. Honor it when needed!")
    
    if social_count == 0:
        recommendations.append("Consider inviting a friend to join you - movement can be social!")
    
    if variety_count < 3:
        recommendations.append("Try exploring different types of joyful movement - variety is the spice of life!")
    
    return {
        "insights": insights if insights else ["Keep listening to your body! 💚"],
        "variety_count": variety_count,
        "rest_count": rest_count,
        "social_count": social_count,
        "energizing_movement": energizing_name,
        "recommendations": recommendations,
        "total_movements": len(movements)
    }

@app.delete("/api/movement/{movement_id}")
def delete_movement(movement_id: str, user = Depends(get_current_user)):
    """Delete a movement log"""
    movement = movement_collection.find_one({"movement_id": movement_id})
    
    if not movement:
        raise HTTPException(status_code=404, detail="Movement not found")
    
    if movement["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    movement_collection.delete_one({"movement_id": movement_id})
    return {"message": "Movement log deleted"}

@app.get("/api/rewards")
def get_rewards_status(user = Depends(get_current_user)):
    """Get user's current points and available rewards"""
    user_data = users_collection.find_one({"user_id": user["user_id"]})
    
    current_points = user_data.get("points", 0)
    total_earned = user_data.get("total_points_earned", 0)
    
    # Define rewards tiers
    rewards_tiers = [
        {"name": "Bronze Status", "points_required": 0, "unlocked": True, "icon": "🥉"},
        {"name": "Silver Status", "points_required": 500, "unlocked": current_points >= 500, "icon": "🥈"},
        {"name": "Gold Status", "points_required": 1500, "unlocked": current_points >= 1500, "icon": "🥇"},
        {"name": "Platinum Status", "points_required": 3000, "unlocked": current_points >= 3000, "icon": "💎"},
        {"name": "Diamond Elite", "points_required": 5000, "unlocked": current_points >= 5000, "icon": "💠"}
    ]
    
    # Calculate next reward
    next_reward = None
    for reward in rewards_tiers:
        if not reward["unlocked"]:
            next_reward = {
                "name": reward["name"],
                "points_needed": reward["points_required"] - current_points,
                "icon": reward["icon"]
            }
            break
    
    return {
        "current_points": current_points,
        "total_points_earned": total_earned,
        "rewards_tiers": rewards_tiers,
        "next_reward": next_reward,
        "points_breakdown": {
            "per_meal": 10,
            "per_badge": "Varies (20-2000)",
            "per_challenge": 20
        }
    }

@app.get("/api/body-prompts/daily")
def get_daily_body_prompt():
    """Get a daily body-positive prompt"""
    import random
    prompt = random.choice(BODY_HONOR_PROMPTS)
    return prompt

@app.get("/api/body-prompts/all")
def get_all_body_prompts():
    """Get all body-positive prompts"""
    return {"prompts": BODY_HONOR_PROMPTS}

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
            "message": f"Thank you for nourishing yourself! 🌸 {nutrition_data.get('food_name', 'Your meal')} looks wonderful. We're here to support you.",
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

@app.get("/api/coach/users/{user_id}/movement")
def get_client_movement(user_id: str, coach = Depends(require_coach)):
    """Coach views client's movement log"""
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    movements = list(movement_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(50))
    
    for movement in movements:
        movement.pop('_id', None)
    
    return {"movements": movements}

@app.get("/api/coach/users/{user_id}/movement-summary")
def get_client_movement_summary(user_id: str, coach = Depends(require_coach)):
    """Coach views summary of client's movement patterns"""
    if user_id not in coach.get("clients", []):
        raise HTTPException(status_code=403, detail="This user is not assigned to you")
    
    movements = list(movement_collection.find({"user_id": user_id}))
    
    if not movements:
        return {
            "total_movements": 0,
            "rest_days_honored": 0,
            "variety_score": 0,
            "social_movements": 0,
            "common_intentions": [],
            "energy_patterns": {}
        }
    
    # Analyze for coach
    movement_types = [m.get("movement_type") for m in movements if m.get("movement_type")]
    variety_score = len(set(movement_types))
    rest_count = sum(1 for m in movements if m.get("is_rest_day"))
    social_count = sum(1 for m in movements if m.get("was_social"))
    
    # Intentions
    from collections import Counter
    intentions = [m.get("movement_intention") for m in movements if m.get("movement_intention")]
    common_intentions = Counter(intentions).most_common(3)
    
    # Energy patterns
    energy_improved = 0
    energy_decreased = 0
    for m in movements:
        if m.get("before_energy") and m.get("after_energy"):
            energy_map = {"drained": 1, "moderate": 2, "energized": 3}
            before = energy_map.get(m.get("before_energy"), 2)
            after = energy_map.get(m.get("after_energy"), 2)
            if after > before:
                energy_improved += 1
            elif after < before:
                energy_decreased += 1
    
    # Body listening
    honored_cravings = sum(1 for m in movements if m.get("body_craving"))
    was_mindful = sum(1 for m in movements if m.get("was_present"))
    
    return {
        "total_movements": len(movements),
        "rest_days_honored": rest_count,
        "variety_score": variety_score,
        "social_movements": social_count,
        "common_intentions": [{"intention": i[0], "count": i[1]} for i in common_intentions],
        "energy_patterns": {
            "improved": energy_improved,
            "decreased": energy_decreased,
            "percentage_energizing": round((energy_improved / max(energy_improved + energy_decreased, 1)) * 100)
        },
        "body_listening": {
            "honored_cravings": honored_cravings,
            "mindful_sessions": was_mindful
        },
        "notes": f"Client has explored {variety_score} different movement types and honored rest {rest_count} times. {social_count} movements were social."
    }

    
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
