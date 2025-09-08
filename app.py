import os
import sqlite3
from dotenv import load_dotenv
from flask import Flask, g

# --- Initial Configuration ---

# Load environment variables from a .env file
load_dotenv()

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['DATABASE'] = os.environ.get('DATABASE_FILE', 'sustainability.db')

# --- Database Connection Management ---

def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row # Allows accessing columns by name
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Database Initialization Function ---

def create_tables():
    """Connects to the database and creates all tables for SQLite."""
    db = get_db()
    cursor = db.cursor()
    
    # --- CREATE TABLE SQL Statements (SQLite compatible) ---

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        village TEXT,
        district TEXT,
        state TEXT,
        sustainability_score INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sustainable_practices (
        practice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS challenges (
        challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        practice_id INTEGER,
        challenge_type TEXT NOT NULL,
        points_reward INTEGER NOT NULL,
        verification_method TEXT,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (practice_id) REFERENCES sustainable_practices(practice_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_challenges (
        user_challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        challenge_id INTEGER NOT NULL,
        status TEXT DEFAULT 'in_progress',
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completion_date TIMESTAMP,
        submission_proof_url TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (challenge_id) REFERENCES challenges(challenge_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS badges (
        badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        icon_url TEXT,
        criteria_description TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_badges (
        user_badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        badge_id INTEGER NOT NULL,
        date_earned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (badge_id) REFERENCES badges(badge_id) ON DELETE CASCADE,
        UNIQUE(user_id, badge_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rewards (
        reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        reward_type TEXT,
        points_cost INTEGER NOT NULL,
        provider TEXT,
        stock_quantity INTEGER
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS community_progress (
        community_id INTEGER PRIMARY KEY AUTOINCREMENT,
        community_name TEXT NOT NULL,
        community_level TEXT,
        total_water_saved_liters INTEGER DEFAULT 0,
        total_members INTEGER DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    db.commit()
    print("Database tables checked and created successfully in SQLite!")

# --- FLASK COMMANDS AND ROUTES ---

@app.cli.command("init-db")
def init_db_command():
    """Flask CLI command to initialize the SQLite database."""
    # To ensure tables are fresh, we can delete the file first.
    db_file = app.config['DATABASE']
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed existing database file '{db_file}'.")
    
    with app.app_context():
        create_tables()

@app.route('/')
def home():
    """Basic route to check if the app is running."""
    try:
        get_db()
        db_status = "Database connection successful."
    except Exception as e:
        db_status = f"Database connection failed: {e}"
        
    return f"<h1>Sustainable Farming Platform API</h1><p>Setup is using SQLite.</p><p>{db_status}</p>"

if __name__ == '__main__':
    app.run(debug=True)

