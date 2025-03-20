import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_babel import Babel, gettext as _

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure SQLAlchemy and other basic settings
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'it']  # English and Italian support
babel = Babel()

def select_locale():
    # Try to get locale from the query parameter
    locale = request.args.get('lang')
    if locale and locale in app.config['BABEL_SUPPORTED_LOCALES']:
        return locale
    # Default to English if no match is found
    return 'en'

# Make select_locale available to templates
@app.context_processor
def utility_processor():
    return dict(get_locale=select_locale)

babel.init_app(app, locale_selector=select_locale)

# Configure upload settings
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Import and initialize models
from models import db, User, Player
db.init_app(app)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import and register blueprints
from video_routes import video_bp
app.register_blueprint(video_bp)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        logger.debug("Dashboard route accessed")
        # Get all players for the current user
        players = Player.query.filter_by(user_id=current_user.id).order_by(Player.created_at.desc()).all()
        return render_template('dashboard.html', players=players)
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}", exc_info=True)
        return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    logger.debug("Register endpoint called")
    data = request.get_json()
    logger.debug(f"Register data: {data}")

    if not data or 'email' not in data or 'password' not in data or 'username' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(
        username=data['username'],
        email=data['email']
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()
    logger.info(f"User registered: {user.email}")

    # Login the user after successful registration
    login_user(user)
    return jsonify({
        'message': 'Registration successful',
        'redirect': url_for('index')  # Redirect to landing page
    }), 201

@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug("Login endpoint called")
    if request.method == 'GET':
        return redirect(url_for('index'))

    data = request.get_json()
    logger.debug(f"Login data: {data}")

    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Missing email or password'}), 400

    user = User.query.filter_by(email=data['email']).first()
    if user and user.check_password(data['password']):
        login_user(user)
        logger.info(f"User logged in: {user.email}")
        return jsonify({
            'message': 'Login successful',
            'redirect': url_for('index')  # Redirect to landing page
        })

    return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/check-auth')
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'username': current_user.username,
                'email': current_user.email
            }
        })
    return jsonify({'authenticated': False})

@app.route('/players/<int:player_id>')
@login_required
def player_profile(player_id):
    player = Player.query.get_or_404(player_id)

    # Ensure the user has access to this player
    if player.user_id != current_user.id:
        return redirect(url_for('index'))

    return render_template('player_profile.html', player=player)

@app.route('/home')
@login_required
def home():
    try:
        logger.debug("Home route accessed")
        players = Player.query.filter_by(user_id=current_user.id).order_by(Player.created_at.desc()).all()
        return render_template('index.html', players=players)
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}", exc_info=True)
        return redirect(url_for('index'))

@app.route('/api/players', methods=['POST'])
@login_required
def create_player():
    logger.debug("Create player endpoint called")
    data = request.get_json()
    logger.debug(f"Player data received: {data}")

    # Basic validation
    if not data or not all(key in data for key in ['name', 'team', 'role']):
        logger.warning("Missing required fields in player data")
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        # Create new player
        player = Player(
            name=data['name'],
            team=data['team'],
            role=data['role'],
            goals=data.get('goals', 0),
            assists=data.get('assists', 0),
            user_id=current_user.id
        )

        # Save to database
        db.session.add(player)
        db.session.commit()
        logger.info(f"Player created: {player.name}")

        return jsonify({
            'message': 'Player created successfully',
            'player': {
                'id': player.id,
                'name': player.name,
                'team': player.team,
                'role': player.role,
                'goals': player.goals,
                'assists': player.assists
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating player: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/scouting')
@login_required  # Added login requirement
def scouting():
    try:
        logger.debug("Scouting page accessed")
        # Get all players from all users
        players = Player.query.order_by(Player.created_at.desc()).all()
        return render_template('scouting.html', players=players)
    except Exception as e:
        logger.error(f"Error in scouting route: {str(e)}", exc_info=True)
        return redirect(url_for('index'))


@app.route('/profile')
@login_required
def user_profile():
    try:
        logger.debug("User profile route accessed")
        # Get all players for the current user
        players = Player.query.filter_by(user_id=current_user.id).order_by(Player.created_at.desc()).all()
        return render_template('user_profile.html', players=players)
    except Exception as e:
        logger.error(f"Error in user profile route: {str(e)}", exc_info=True)
        return redirect(url_for('index'))

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created")

@app.route('/api/players/search')
def search_players():
    try:
        logger.debug("Search players endpoint called")
        name = request.args.get('name', '').lower()
        team = request.args.get('team', '').lower()
        role = request.args.get('role', '')

        # Base query
        query = Player.query

        # Apply filters
        if name:
            query = query.filter(db.func.lower(Player.name).like(f'%{name}%'))
        if team:
            query = query.filter(db.func.lower(Player.team).like(f'%{team}%'))
        if role:
            query = query.filter(Player.role == role)

        # Execute query and get results
        players = query.order_by(Player.created_at.desc()).all()

        # Convert to JSON-serializable format
        players_data = [{
            'id': player.id,
            'name': player.name,
            'team': player.team,
            'role': player.role,
            'goals': player.goals,
            'assists': player.assists
        } for player in players]

        return jsonify(players_data)

    except Exception as e:
        logger.error(f"Error in search players: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)