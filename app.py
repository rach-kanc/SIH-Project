import sqlite3
import shortuuid
from flask import Flask, jsonify, request, g

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['DATABASE'] = 'farm_game.db'

# --- Database Connection Management ---

def get_db():
    """Opens a new database connection if there is none for the current context."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row  # Allows accessing columns by name
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Core Database Logic Functions ---
# These functions contain the raw database operations.

def create_tables(conn):
    """Sets up all required tables using shortuuid for primary keys."""
    cursor = conn.cursor()
    print("Verifying all tables...")
    # (Table creation statements remain the same as before)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, phone_number TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL, village TEXT NOT NULL, district TEXT NOT NULL, state TEXT NOT NULL,
            sustainability_score INTEGER DEFAULT 0, points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, category TEXT,
            points_reward INTEGER NOT NULL, verification_type TEXT NOT NULL, difficulty TEXT DEFAULT 'Medium'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_tasks (
            user_task_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, task_id TEXT NOT NULL, status TEXT NOT NULL,
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_date TIMESTAMP, evidence_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id), FOREIGN KEY (task_id) REFERENCES tasks (task_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            badge_id TEXT PRIMARY KEY, badge_name TEXT NOT NULL UNIQUE,
            badge_description TEXT, icon_url TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_badges (
            user_badge_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, badge_id TEXT NOT NULL,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id), FOREIGN KEY (badge_id) REFERENCES badges (badge_id)
        )
    ''')
    conn.commit()
    print("Tables verified successfully.")

def add_user(conn, phone, password, name, village, district, state):
    """Adds a new user. Hashes the password."""
    cursor = conn.cursor()
    user_id = shortuuid.uuid()
    # In a real app: password_hash = generate_password_hash(password)
    password_hash = password  # Placeholder
    try:
        cursor.execute(
            'INSERT INTO users (user_id, phone_number, password_hash, full_name, village, district, state) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, phone, password_hash, name, village, district, state)
        )
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None

def get_user_dashboard_data(conn, user_id):
    """Fetches dashboard data for a specific user."""
    cursor = conn.cursor()
    assigned_tasks = cursor.execute('''
        SELECT t.title, t.description, t.points_reward, ut.status
        FROM user_tasks ut JOIN tasks t ON ut.task_id = t.task_id
        WHERE ut.user_id = ? AND ut.status = 'ASSIGNED'
    ''', (user_id,)).fetchall()
    earned_badges = cursor.execute('''
        SELECT b.badge_name, b.icon_url
        FROM user_badges ub JOIN badges b ON ub.badge_id = b.badge_id
        WHERE ub.user_id = ?
    ''', (user_id,)).fetchall()
    return {
        "tasks": [dict(row) for row in assigned_tasks],
        "badges": [dict(row) for row in earned_badges]
    }

def get_village_leaderboard_data(conn, village, district):
    """Gets top 10 users in a village."""
    cursor = conn.cursor()
    leaderboard = cursor.execute('''
        SELECT full_name, points, sustainability_score FROM users
        WHERE village = ? AND district = ?
        ORDER BY points DESC LIMIT 10
    ''', (village, district)).fetchall()
    return [dict(row) for row in leaderboard]

# --- Flask CLI Commands ---

@app.cli.command("init-db")
def init_db_command():
    """Flask CLI command to initialize the database."""
    db = get_db()
    create_tables(db)
    print("Database has been initialized.")

# --- API Routes ---

@app.route('/api/register', methods=['POST'])
def register_user():
    """API endpoint to register a new user."""
    data = request.get_json()
    if not all(k in data for k in ['phone', 'password', 'name', 'village', 'district', 'state']):
        return jsonify({"error": "Missing required fields"}), 400
    
    db = get_db()
    user_id = add_user(db, data['phone'], data['password'], data['name'], data['village'], data['district'], data['state'])
    
    if user_id:
        return jsonify({"message": "User registered successfully", "user_id": user_id}), 201
    else:
        return jsonify({"error": "User with this phone number already exists"}), 409

@app.route('/api/dashboard/<user_id>', methods=['GET'])
def get_dashboard(user_id):
    """API endpoint to get a user's dashboard."""
    db = get_db()
    dashboard_data = get_user_dashboard_data(db, user_id)
    return jsonify(dashboard_data)

@app.route('/api/leaderboard/<district>/<village>', methods=['GET'])
def get_leaderboard(district, village):
    """API endpoint to get the village leaderboard."""
    db = get_db()
    leaderboard = get_village_leaderboard_data(db, village, district)
    return jsonify(leaderboard)
  
@app.route('/')
def index():
    return "<h1>Sustainable Farming API is running!</h1>"

# --- Main execution block ---
if __name__ == '__main__':
    app.run(debug=True)
