import os
import logging
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("SESSION_SECRET")

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models
from models import User, Player

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    logger.debug("Serving index page")
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    logger.debug(f"Register attempt with data: {data}")

    # Basic validation
    if not data or 'email' not in data or 'password' not in data or 'username' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if user exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    # Create new user
    user = User(
        username=data['username'],
        email=data['email']
    )
    user.set_password(data['password'])

    # Save to database
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Registration successful'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    logger.debug(f"Login attempt for email: {data.get('email')}")

    # Basic validation
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Missing email or password'}), 400

    # Find user and verify password
    user = User.query.filter_by(email=data['email']).first()
    if user and user.check_password(data['password']):
        login_user(user)
        return jsonify({'message': 'Login successful'})

    return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'})

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created")

# Log all registered routes
for rule in app.url_map.iter_rules():
    logger.info(f"Route registered: {rule}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)