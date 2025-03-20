from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), nullable=False)  # 'player', 'parent', 'coach', 'scout'
    team = db.Column(db.String(100))  # Optional team field

    # Add relationship to players
    players = db.relationship('Player', backref='user', lazy=True)
    # Add relationship for parent-child
    parent_relationships = db.relationship('PlayerParent', backref='parent', lazy=True, foreign_keys='PlayerParent.parent_id')
    # Add relationship for coach access requests
    access_requests = db.relationship('AccessRequest', backref='coach', lazy=True, foreign_keys='AccessRequest.coach_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def age(self):
        """Calculate user's age"""
        today = datetime.now()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}"

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    # Player statistics
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)

    # Add relationship with videos
    videos = db.relationship('Video', backref='player', lazy=True)
    # Add relationship for parent-child
    parent_relationships = db.relationship('PlayerParent', backref='player', lazy=True)
    # Add relationship for coach access
    access_requests = db.relationship('AccessRequest', backref='player', lazy=True)

class PlayerParent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Unique constraint to prevent duplicate relationships
    __table_args__ = (db.UniqueConstraint('player_id', 'parent_id'),)

class AccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Unique constraint to prevent duplicate requests
    __table_args__ = (db.UniqueConstraint('coach_id', 'player_id'),)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=True)  # Made optional
    video_url = db.Column(db.String(500), nullable=True)  # Added for YouTube URLs
    video_type = db.Column(db.String(20), nullable=False, default='file')  # 'file' or 'youtube'
    youtube_id = db.Column(db.String(20), nullable=True)  # Store YouTube video ID
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Float)  # Video duration in seconds
    filesize = db.Column(db.Integer)  # File size in bytes
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Video metadata
    tags = db.Column(db.JSON, default=list)  # Store tags as JSON array
    notes = db.Column(db.Text)  # Additional notes about the video/action