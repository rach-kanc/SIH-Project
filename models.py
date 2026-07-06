from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import shortuuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String, primary_key=True)
    phone_number = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    full_name = db.Column(db.String, nullable=False)
    village = db.Column(db.String, nullable=False)
    district = db.Column(db.String, nullable=False)
    state = db.Column(db.String, nullable=False)
    sustainability_score = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('UserTask', backref='user', lazy=True, cascade='all, delete-orphan')
    badges = db.relationship('UserBadge', backref='user', lazy=True, cascade='all, delete-orphan')
    quiz_attempts = db.relationship('UserQuizAttempt', backref='user', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    category = db.Column(db.String)
    points_reward = db.Column(db.Integer, nullable=False)
    verification_type = db.Column(db.String, nullable=False)
    difficulty = db.Column(db.String, default='Medium')
    
    user_tasks = db.relationship('UserTask', backref='task', lazy=True, cascade='all, delete-orphan')

class UserTask(db.Model):
    __tablename__ = 'user_tasks'
    user_task_id = db.Column(db.String, primary_key=True, default=lambda: shortuuid.uuid())
    user_id = db.Column(db.String, db.ForeignKey('users.user_id'), nullable=False)
    task_id = db.Column(db.String, db.ForeignKey('tasks.task_id'), nullable=False)
    status = db.Column(db.String, nullable=False)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    evidence_path = db.Column(db.String)

class Badge(db.Model):
    __tablename__ = 'badges'
    badge_id = db.Column(db.String, primary_key=True)
    badge_name = db.Column(db.String, unique=True, nullable=False)
    badge_description = db.Column(db.String)
    icon_url = db.Column(db.String)
    
    user_badges = db.relationship('UserBadge', backref='badge', lazy=True, cascade='all, delete-orphan')

class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    user_badge_id = db.Column(db.String, primary_key=True, default=lambda: shortuuid.uuid())
    user_id = db.Column(db.String, db.ForeignKey('users.user_id'), nullable=False)
    badge_id = db.Column(db.String, db.ForeignKey('badges.badge_id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)

class Crop(db.Model):
    __tablename__ = 'crops'
    crop_id = db.Column(db.String, primary_key=True)
    crop_name = db.Column(db.String, unique=True, nullable=False)
    crop_description = db.Column(db.String)
    icon_class = db.Column(db.String)
    difficulty_level = db.Column(db.String, default='Medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    questions = db.relationship('QuizQuestion', backref='crop', lazy=True, cascade='all, delete-orphan')
    quiz_attempts = db.relationship('UserQuizAttempt', backref='crop', lazy=True, cascade='all, delete-orphan')

class QuizCategory(db.Model):
    __tablename__ = 'quiz_categories'
    category_id = db.Column(db.String, primary_key=True)
    category_name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    questions = db.relationship('QuizQuestion', backref='category', lazy=True)

class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'
    question_id = db.Column(db.String, primary_key=True)
    crop_id = db.Column(db.String, db.ForeignKey('crops.crop_id'), nullable=False)
    category_id = db.Column(db.String, db.ForeignKey('quiz_categories.category_id'))
    question_text = db.Column(db.String, nullable=False)
    question_type = db.Column(db.String, default='multiple_choice')
    difficulty = db.Column(db.String, default='Medium')
    explanation = db.Column(db.String)
    points = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    answers = db.relationship('QuizAnswer', backref='question', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('UserQuizResponse', backref='question', lazy=True, cascade='all, delete-orphan')

class QuizAnswer(db.Model):
    __tablename__ = 'quiz_answers'
    answer_id = db.Column(db.String, primary_key=True)
    question_id = db.Column(db.String, db.ForeignKey('quiz_questions.question_id'), nullable=False)
    answer_text = db.Column(db.String, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    explanation = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    responses = db.relationship('UserQuizResponse', backref='answer', lazy=True, cascade='all, delete-orphan')

class UserQuizAttempt(db.Model):
    __tablename__ = 'user_quiz_attempts'
    attempt_id = db.Column(db.String, primary_key=True, default=lambda: shortuuid.uuid())
    user_id = db.Column(db.String, db.ForeignKey('users.user_id'), nullable=False)
    crop_id = db.Column(db.String, db.ForeignKey('crops.crop_id'), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    time_taken = db.Column(db.Integer) # in seconds
    status = db.Column(db.String, default='IN_PROGRESS') # IN_PROGRESS, COMPLETED, ABANDONED
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    responses = db.relationship('UserQuizResponse', backref='attempt', lazy=True, cascade='all, delete-orphan')

class UserQuizResponse(db.Model):
    __tablename__ = 'user_quiz_responses'
    response_id = db.Column(db.String, primary_key=True, default=lambda: shortuuid.uuid())
    attempt_id = db.Column(db.String, db.ForeignKey('user_quiz_attempts.attempt_id'), nullable=False)
    question_id = db.Column(db.String, db.ForeignKey('quiz_questions.question_id'), nullable=False)
    answer_id = db.Column(db.String, db.ForeignKey('quiz_answers.answer_id'), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    time_taken = db.Column(db.Integer) # time spent on this question in seconds
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
