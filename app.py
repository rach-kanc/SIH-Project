import sqlite3
import shortuuid
from flask import Flask, jsonify, request, g, render_template, redirect, url_for, session, flash
# In a real application, you MUST use a secure hashing library.
# from werkzeug.security import generate_password_hash, check_password_hash

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['DATABASE'] = 'farm_game.db'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True # Makes API output readable
app.secret_key = "your_secret_key"  # For session management

# In-memory "database" with a default user (for HTML routes compatibility)
users = {
    "farmer": "123"   # Default login account
}

# --- Database Connection Management ---

def get_db():
    """Opens a new database connection if there is none for the current context."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Core Database Logic Functions ---

def create_tables(conn):
    """Sets up all required tables using shortuuid for primary keys."""
    cursor = conn.cursor()
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, phone_number TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL, village TEXT NOT NULL, district TEXT NOT NULL, state TEXT NOT NULL,
            sustainability_score INTEGER DEFAULT 0, points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, category TEXT,
            points_reward INTEGER NOT NULL, verification_type TEXT NOT NULL, difficulty TEXT DEFAULT 'Medium'
        )
    ''')
    # User_tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_tasks (
            user_task_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, task_id TEXT NOT NULL, status TEXT NOT NULL,
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_date TIMESTAMP, evidence_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id), FOREIGN KEY (task_id) REFERENCES tasks (task_id)
        )
    ''')
    # Badges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            badge_id TEXT PRIMARY KEY, badge_name TEXT NOT NULL UNIQUE,
            badge_description TEXT, icon_url TEXT
        )
    ''')
    # User_badges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_badges (
            user_badge_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, badge_id TEXT NOT NULL,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id), FOREIGN KEY (badge_id) REFERENCES badges (badge_id)
        )
    ''')
    conn.commit()

# --- DATABASE FUNCTIONS ---

def get_user_by_phone(conn, phone):
    """Finds a user by their phone number for login."""
    return conn.cursor().execute('SELECT * FROM users WHERE phone_number = ?', (phone,)).fetchone()

def get_user_profile_data(conn, user_id):
    """Fetches all profile data for a specific user."""
    return conn.cursor().execute('SELECT user_id, full_name, village, district, state, sustainability_score, points FROM users WHERE user_id = ?', (user_id,)).fetchone()

def update_user_task_status(conn, user_task_id, new_status, evidence_path=None):
    """Updates the status of a specific user task."""
    cursor = conn.cursor()
    if evidence_path:
        cursor.execute("UPDATE user_tasks SET status = ?, evidence_path = ? WHERE user_task_id = ?", (new_status, evidence_path, user_task_id))
    else:
        cursor.execute("UPDATE user_tasks SET status = ? WHERE user_task_id = ?", (new_status, user_task_id))
    conn.commit()
    return cursor.rowcount > 0 # Returns True if a row was updated

def verify_task_and_award_points(conn, user_task_id):
    """Finalizes a task, updates status to 'VERIFIED', and awards points."""
    cursor = conn.cursor()
    # Get user_id and task_id from the user_task
    user_task = cursor.execute("SELECT user_id, task_id FROM user_tasks WHERE user_task_id = ? AND status = 'COMPLETED'", (user_task_id,)).fetchone()
    if not user_task:
        return None # Task not found or not ready for verification

    # Get points for that task
    task = cursor.execute("SELECT points_reward FROM tasks WHERE task_id = ?", (user_task['task_id'],)).fetchone()
    if not task:
        return None

    points_to_add = task['points_reward']

    # Update task status to VERIFIED
    cursor.execute("UPDATE user_tasks SET status = 'VERIFIED' WHERE user_task_id = ?", (user_task_id,))
    # Award points to the user
    cursor.execute("UPDATE users SET points = points + ?, sustainability_score = sustainability_score + ? WHERE user_id = ?", (points_to_add, points_to_add // 10, user_task['user_id']))

    conn.commit()
    return {"user_id": user_task['user_id'], "points_awarded": points_to_add}

# --- Flask CLI Command ---

@app.cli.command("init-db")
def init_db_command():
    """Initializes the database."""
    db = get_db()
    create_tables(db)
    print("Database has been initialized.")

# --- HTML TEMPLATE ROUTES (from second file) ---

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
        username = request.form['username']
        password = request.form['password']

        if username in users:
            flash("User already exists! Try logging in.", "error")
            return redirect(url_for('signup'))
        
        users[username] = password
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username] == password:
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('welcome'))
        else:
            flash("Invalid credentials! Please try again.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# Welcome route
@app.route('/welcome')
def welcome():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('welcome.html', username=session['username'])

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# --- API ROUTES (from first file) ---

@app.route('/api')
def api_index():
    return "<h1>Sustainable Farming API is running!</h1>"

# --- User & Auth API Routes ---
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not all(k in data for k in ['phone', 'password', 'name', 'village', 'district', 'state']):
        return jsonify({"error": "Missing required fields"}), 400
    db = get_db()
    # In a real app: password_hash = generate_password_hash(data['password'])
    password_hash = data['password'] # Placeholder
    try:
        user_id = shortuuid.uuid()
        db.cursor().execute(
            'INSERT INTO users (user_id, phone_number, password_hash, full_name, village, district, state) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, data['phone'], password_hash, data['name'], data['village'], data['district'], data['state'])
        )
        db.commit()
        return jsonify({"message": "User registered successfully", "user_id": user_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "User with this phone number already exists"}), 409

@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login."""
    data = request.get_json()
    if not data or 'phone' not in data or 'password' not in data:
        return jsonify({"error": "Phone and password are required"}), 400

    db = get_db()
    user = get_user_by_phone(db, data['phone'])

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # In a real app: if not check_password_hash(user['password_hash'], data['password']):
    if user['password_hash'] != data['password']: # Placeholder password check
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "user_id": user['user_id']}), 200

@app.route('/api/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    """API endpoint to get a user's full profile."""
    db = get_db()
    profile = get_user_profile_data(db, user_id)
    if profile:
        return jsonify(dict(profile))
    return jsonify({"error": "User not found"}), 404

# --- Task & Gameplay API Routes ---

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """API endpoint to list all available master tasks."""
    db = get_db()
    tasks = db.cursor().execute("SELECT * FROM tasks").fetchall()
    return jsonify([dict(row) for row in tasks])

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task():
    """API endpoint to mark an assigned task as completed by the user."""
    data = request.get_json()
    if 'user_task_id' not in data:
        return jsonify({"error": "user_task_id is required"}), 400

    db = get_db()
    evidence = data.get('evidence_path') # Optional evidence
    success = update_user_task_status(db, data['user_task_id'], 'COMPLETED', evidence)

    if success:
        return jsonify({"message": "Task marked as complete. Awaiting verification."}), 200
    return jsonify({"error": "Could not update task. Check user_task_id."}), 404

@app.route('/api/tasks/verify', methods=['POST'])
def verify_task():
    """(Simulated AI) Endpoint to verify a task and award points."""
    data = request.get_json()
    if 'user_task_id' not in data:
        return jsonify({"error": "user_task_id is required"}), 400

    db = get_db()
    result = verify_task_and_award_points(db, data['user_task_id'])
    
    if result:
        return jsonify({"message": "Task verified successfully!", "awarded": result}), 200
    return jsonify({"error": "Verification failed. Task may not be 'COMPLETED' or ID is invalid."}), 400

# --- Community API Routes ---
@app.route('/api/dashboard/<user_id>', methods=['GET'])
def get_api_dashboard(user_id):
    db = get_db()
    cursor = db.cursor()
    tasks = cursor.execute('''
        SELECT ut.user_task_id, t.title, t.description, t.points_reward, ut.status
        FROM user_tasks ut JOIN tasks t ON ut.task_id = t.task_id
        WHERE ut.user_id = ?
    ''', (user_id,)).fetchall()
    badges = cursor.execute('SELECT b.badge_name, b.icon_url FROM user_badges ub JOIN badges b ON ub.badge_id = b.badge_id WHERE ub.user_id = ?', (user_id,)).fetchall()
    return jsonify({"tasks": [dict(row) for row in tasks], "badges": [dict(row) for row in badges]})

@app.route('/api/leaderboard/<district>/<village>', methods=['GET'])
def get_leaderboard(district, village):
    db = get_db()
    leaderboard = db.cursor().execute('SELECT full_name, points, sustainability_score FROM users WHERE village = ? AND district = ? ORDER BY points DESC LIMIT 10', (village, district)).fetchall()
    return jsonify([dict(row) for row in leaderboard])

if __name__ == '__main__':
    app.run(debug=True)