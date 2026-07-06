import shortuuid
from flask import Flask, jsonify, request, g, render_template, redirect, url_for, session, flash
from datetime import datetime
import requests
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env file (if it exists)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Models ---
from models import db, User, Task, UserTask, Badge, UserBadge, Crop, QuizCategory, QuizQuestion, QuizAnswer, UserQuizAttempt, UserQuizResponse

# --- AI Model Imports ---
# NOTE: You must install these libraries: pip install torch torchvision transformers Pillow
from transformers import ViTForImageClassification, ViTImageProcessor
from PIL import Image
import torch
import io

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True  # Makes API output readable
# Use environment variable for secret key, fallback to a generated local secret for non-production
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(32))

# --- Database Configuration ---
# Fallback to local SQLite if DATABASE_URL is not set
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///farm_game.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# --- AI Model Configuration ---
MODEL_NAME = "wambugu71/crop_leaf_diseases_vit"

disease_processor = None
disease_model = None
model_load_attempted = False

def load_ai_model():
    global disease_processor, disease_model, model_load_attempted
    if model_load_attempted:
        return
    model_load_attempted = True

    try:
        print(f"Loading Crop Disease Model: {MODEL_NAME}...")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        disease_processor = ViTImageProcessor.from_pretrained(MODEL_NAME)
        disease_model = ViTForImageClassification.from_pretrained(MODEL_NAME).to(device)
        disease_model.eval()
        print("Crop Disease Model loaded successfully.")
    except Exception as e:
        print(f"ERROR: Failed to load AI model. Predictions will fail. Make sure you have PyTorch and Hugging Face libraries installed. Error: {e}")
        disease_processor = None
        disease_model = None

# --- Database initialization is handled by SQLAlchemy db.create_all() ---

# --- DATABASE FUNCTIONS (omitted for brevity, assume unchanged) ---

# --- QUIZ DATABASE FUNCTIONS ---
def get_all_crops():
    return Crop.query.order_by(Crop.crop_name).all()

def get_crop_by_id(crop_id):
    return Crop.query.get(crop_id)

def get_quiz_questions_for_crop(crop_id, limit=10):
    from sqlalchemy.sql.expression import func
    return QuizQuestion.query.filter_by(crop_id=crop_id).order_by(func.random()).limit(limit).all()

def get_question_answers(question_id):
    return QuizAnswer.query.filter_by(question_id=question_id).order_by(QuizAnswer.answer_id).all()

def create_quiz_attempt(user_id, crop_id, total_questions=10):
    attempt = UserQuizAttempt(user_id=user_id, crop_id=crop_id, total_questions=total_questions)
    db.session.add(attempt)
    db.session.commit()
    return attempt.attempt_id

def save_quiz_response(attempt_id, question_id, answer_id, time_taken=None):
    answer = QuizAnswer.query.get(answer_id)
    is_correct = answer.is_correct if answer else False
    
    response = UserQuizResponse(
        attempt_id=attempt_id,
        question_id=question_id,
        answer_id=answer_id,
        is_correct=is_correct,
        time_taken=time_taken
    )
    db.session.add(response)
    db.session.commit()
    return is_correct

def complete_quiz_attempt(attempt_id, time_taken=None):
    attempt = UserQuizAttempt.query.get(attempt_id)
    if not attempt:
        return None
        
    stats = db.session.query(
        db.func.count(UserQuizResponse.response_id).label('total_responses'),
        db.func.sum(db.cast(UserQuizResponse.is_correct, db.Integer)).label('correct_answers')
    ).filter(UserQuizResponse.attempt_id == attempt_id).first()
    
    correct_answers = stats.correct_answers or 0
    total_responses = stats.total_responses or 0
    score = int((correct_answers / max(total_responses, 1)) * 100)
    
    attempt.correct_answers = correct_answers
    attempt.score = score
    attempt.time_taken = time_taken
    attempt.status = 'COMPLETED'
    attempt.completed_at = datetime.utcnow()
    
    if score >= 70:
        user = User.query.get(attempt.user_id)
        if user:
            user.points += (correct_answers * 5)
            
    db.session.commit()
    return {"correct_answers": correct_answers, "total_questions": total_responses, "score": score}

def get_user_quiz_history(user_id, limit=10):
    return UserQuizAttempt.query.join(Crop).filter(
        UserQuizAttempt.user_id == user_id, 
        UserQuizAttempt.status == 'COMPLETED'
    ).order_by(UserQuizAttempt.completed_at.desc()).limit(limit).all()

def get_user_by_phone(phone):
    return User.query.filter_by(phone_number=phone).first()

def get_user_profile_data(user_id):
    return User.query.get(user_id)

def update_user_task_status(user_task_id, new_status, evidence_path=None):
    task = UserTask.query.get(user_task_id)
    if not task: return False
    task.status = new_status
    if evidence_path:
        task.evidence_path = evidence_path
    db.session.commit()
    return True

def verify_task_and_award_points(user_task_id):
    user_task = UserTask.query.filter_by(user_task_id=user_task_id, status='COMPLETED').first()
    if not user_task: return None
    
    task = Task.query.get(user_task.task_id)
    if not task: return None
    
    points_to_add = task.points_reward
    user_task.status = 'VERIFIED'
    
    user = User.query.get(user_task.user_id)
    user.points += points_to_add
    user.sustainability_score += (points_to_add // 10)
    
    db.session.commit()
    return {"user_id": user.user_id, "points_awarded": points_to_add}

def get_leaderboard(limit=10):
    return User.query.order_by(User.points.desc(), User.sustainability_score.desc()).limit(limit).all()

# --- Flask CLI Command ---
@app.cli.command("init-db")
def init_db_command():
    """Initializes the database."""
    db.create_all()
    print("Database has been initialized.")

# --- HTML TEMPLATE ROUTES (omitted for brevity, assume unchanged) ---

# Splash screen route
@app.route('/splash')
def splash():
    return render_template('splash.html')

# Root → Redirects to splash
@app.route('/')
def index():
    return redirect(url_for('splash'))

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        name = request.form['name']
        village = request.form['village']
        district = request.form['district']
        state = request.form['state']
        
        # Check if user exists
        existing = User.query.filter_by(phone_number=phone).first()
        if existing:
            flash("User already exists! Try logging in.", "error")
            return redirect(url_for('signup'))
        
        user_id = shortuuid.uuid()
        password_hash = generate_password_hash(password)
        
        new_user = User(
            user_id=user_id,
            phone_number=phone,
            password_hash=password_hash,
            full_name=name,
            village=village,
            district=district,
            state=state
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        
        user = User.query.filter_by(phone_number=phone).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.user_id
            session['username'] = user.full_name
            flash("Login successful!", "success")
            return redirect(url_for('welcome'))
        else:
            flash("Invalid credentials! Please try again.", "error")
            return redirect(url_for('login'))
    
    return render_template('login.html')

# Welcome route
@app.route('/welcome')
def welcome():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('welcome.html', username=session.get('username'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

# Quiz route
@app.route('/quiz')
def quiz():
    if 'user_id' not in session:
        flash('Please log in to access the quiz.', 'error')
        return redirect(url_for('login'))
    return render_template('quiz.html')

# Leaderboard route
@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('leaderboard.html', username=session.get('username'))

@app.route('/emergency_levels')
def emergency_levels():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('emergency_levels.html', username=session.get('username'))

@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('marketplace.html', username=session.get('username'))

# Badges route (placeholder)
@app.route('/badges')
def badges():
    if 'user_id' not in session:
        flash('Please log in to access badges.', 'error')
        return redirect(url_for('login'))
    return render_template('badges.html', username=session.get('username'))

# Profile route
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))

    # Convert the user object to a dictionary for the template
    user_data = {
        'user_id': user.user_id,
        'phone_number': user.phone_number,
        'full_name': user.full_name,
        'village': user.village,
        'district': user.district,
        'state': user.state,
        'sustainability_score': user.sustainability_score,
        'points': user.points,
        'created_at': user.created_at
    }
    
    # Get completed tasks count
    completed_tasks = UserTask.query.filter_by(user_id=session['user_id'], status='VERIFIED').count()
    
    return render_template('profile.html', 
                         user=user_data, 
                         completed_tasks=completed_tasks,
                         min=min)

# Edit Profile route
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        try:
            user.full_name = request.form.get('full_name')
            user.village = request.form.get('village')
            user.district = request.form.get('district')
            user.state = request.form.get('state')
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('edit_profile'))
            
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
            return redirect(url_for('edit_profile'))
    
    # GET request - fetch user data
    user_data = {
        'user_id': user.user_id,
        'phone_number': user.phone_number,
        'full_name': user.full_name,
        'village': user.village,
        'district': user.district,
        'state': user.state,
        'sustainability_score': user.sustainability_score,
        'points': user.points,
        'created_at': user.created_at
    }
    
    # Get completed tasks count
    completed_tasks = UserTask.query.filter_by(user_id=user_id, status='VERIFIED').count()
    
    return render_template('edit_profile.html', 
                         user_data=user_data, 
                         user_preferences=None,  # Will be None for now
                         completed_tasks=completed_tasks)

# Settings route
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Return JSON for AJAX requests only
        if request.is_json:
            return jsonify({'success': True, 'message': 'Settings saved successfully!'})
        
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('settings'))
    
    # For GET request, return settings page with default values
    return render_template('settings.html', settings=None)

# Clear cache route (minimal implementation)
@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    return jsonify({'success': True, 'message': 'Cache cleared successfully'})

# Export data route (minimal implementation)
@app.route('/export_data')
def export_data():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    flash('Export functionality will be available soon!', 'info')
    return redirect(url_for('settings'))

# Delete account route (minimal implementation)
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    try:
        user = User.query.get(user_id)
        if user:
            # We defined cascade='all, delete-orphan' in models.py
            # So deleting the user will delete all associated data automatically!
            db.session.delete(user)
            db.session.commit()
        
        # Clear session
        session.clear()
        
        flash('Your account has been deleted successfully.', 'info')
        return redirect(url_for('signup'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting account: {str(e)}', 'error')
        return redirect(url_for('edit_profile'))

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# --- API ROUTES ---
@app.route('/api')
def api_index():
    return jsonify({
        "message": "KhetSetu Farm Game API",
        "version": "1.0",
        "endpoints": {
            "/api/users": "User management",
            "/api/tasks": "Task management", 
            "/api/quiz": "Quiz functionality",
            "/api/detect_disease": "AI Crop Health Detector" # Added new endpoint
        }
    })

# --- NEW AI CROP HEALTH DETECTION ROUTE ---
@app.route('/api/detect_disease', methods=['POST'])
def detect_disease():
    load_ai_model()
    if not disease_model or not disease_processor:
        # 503 Service Unavailable if model failed to load
        return jsonify({"success": False, "error": "AI Model not initialized on server."}), 503

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No image file provided in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No image selected"}), 400
    
    try:
        # 1. Read the image stream and open it with PIL
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB") # Ensure it's RGB

        # 2. Process the image for the Vision Transformer model
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        inputs = disease_processor(images=image, return_tensors="pt").to(device)

        # 3. Perform prediction (inference)
        with torch.no_grad():
            outputs = disease_model(**inputs)
        
        # 4. Get the predicted class label
        logits = outputs.logits
        predicted_class_idx = logits.argmax(-1).item()
        predicted_label = disease_model.config.id2label[predicted_class_idx]
        
        # Extract the raw probability for confidence score
        probabilities = torch.softmax(logits, dim=1)
        confidence = probabilities[0][predicted_class_idx].item()
        
        # 5. Return the result
        return jsonify({
            "success": True,
            "predicted_label": predicted_label,
            "confidence_score": f"{confidence * 100:.2f}%",
            "message": f"Disease Detected: {predicted_label}. Confidence: {confidence * 100:.2f}%"
        })

    except Exception as e:
        app.logger.error(f"Prediction failed: {e}")
        return jsonify({"success": False, "error": f"Internal server error during prediction: {str(e)}"}), 500

your_weatherapi_key = os.environ.get("WEATHERAPI_KEY")

# WeatherAPI key and base URL
API_KEY = your_weatherapi_key or os.environ.get("WEATHERAPI_KEY_FALLBACK")
BASE_URL = "https://api.weatherapi.com/v1"

MOCK_DATA = {
    "location": {
        "name": "DemoFarm",
        "region": "Kerala",
        "country": "India",
        "localtime": "2025-09-08 10:00"
    },
    "current": {
        "temp_c": 28,
        "temp_f": 82.4,
        "condition": {"text": "Partly Cloudy", "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png"},
        "humidity": 65,
        "precip_mm": 2.0,
        "wind_kph": 10,
        "wind_dir": "NE"
    },
    "forecast": {
        "forecastday": [
            {
                "date": "2025-09-08",
                "day": {
                    "avgtemp_c": 28,
                    "condition": {"text": "Partly Cloudy", "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png"},
                    "daily_chance_of_rain": 45
                }
            },
            {
                "date": "2025-09-09",
                "day": {
                    "avgtemp_c": 30,
                    "condition": {"text": "Sunny", "icon": "//cdn.weatherapi.com/weather/64x64/day/113.png"},
                    "daily_chance_of_rain": 10
                }
            },
            {
                "date": "2025-09-10",
                "day": {
                    "avgtemp_c": 26,
                    "condition": {"text": "Moderate rain", "icon": "//cdn.weatherapi.com/weather/64x64/day/302.png"},
                    "daily_chance_of_rain": 75
                }
            }
        ]
    }
}
@app.route("/get_weather")
def get_weather():
    location = request.args.get("q", "Delhi")
    try:
        url = f"{BASE_URL}/forecast.json?key={API_KEY}&q={location}&days=3&aqi=yes&alerts=yes"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise Exception(data["error"]["message"])
        return jsonify(data)
    except Exception as e:
        print("⚠️ Using MOCK DATA because API failed:", e)
        return jsonify(MOCK_DATA)

@app.route('/weather')
def weather():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('weather.html', username=session.get('username'))

@app.route('/levels')
def levels():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('levels.html', username=session.get('username'))

if __name__ == "__main__":
    # Get port from environment variable for Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)