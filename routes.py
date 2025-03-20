from flask import render_template, jsonify, request, Blueprint, url_for, redirect
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, date
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

def calculate_age(birth_date):
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        # Log request information
        logger.debug("=== REGISTRATION REQUEST DEBUG ===")
        logger.debug(f"Headers: {dict(request.headers)}")
        logger.debug(f"Raw Data: {request.get_data(as_text=True)}")
        logger.debug(f"Content Type: {request.content_type}")

        # Basic request validation
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        logger.debug(f"Parsed JSON data: {data}")

        if not data:
            logger.error("No data received")
            return jsonify({'error': 'No data received'}), 400

        # Required fields validation
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'email', 'password']

        # Log all received fields
        logger.debug("Received fields:")
        for field in required_fields:
            logger.debug(f"{field}: {data.get(field, 'MISSING')}")

        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"Missing fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        try:
            # Validate date and age
            dob = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            age = calculate_age(dob)
            logger.debug(f"Calculated age: {age}")

            if age < 14:
                logger.warning(f"Invalid age: {age}")
                return jsonify({'error': 'Devi avere almeno 14 anni per registrarti'}), 400

        except ValueError as e:
            logger.error(f"Date parsing error: {str(e)}")
            return jsonify({'error': 'Invalid date format'}), 400

        # Check for existing email
        from models import User, Player, db
        if User.query.filter_by(email=data['email']).first():
            logger.warning(f"Email already exists: {data['email']}")
            return jsonify({'error': 'Email già registrata'}), 400

        try:
            # Create user
            user = User(
                first_name=data['first_name'],
                last_name=data['last_name'],
                date_of_birth=dob,
                email=data['email'],
                team=data.get('team', ''),
                role='player'
            )
            user.set_password(data['password'])

            db.session.add(user)
            db.session.commit()
            logger.info(f"User created: {user.email}")

            # Create player profile
            player = Player(user_id=user.id)
            db.session.add(player)
            db.session.commit()
            logger.info(f"Player profile created for user: {user.email}")

            # Login user
            login_user(user)
            logger.info(f"User logged in: {user.email}")

            return jsonify({
                'message': 'Registrazione completata con successo',
                'redirect': '/dashboard'
            }), 201

        except Exception as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({'error': 'Error creating user profile'}), 500

    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Registration error occurred'}), 500

# Import models and setup app context
from models import User, Player, db

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        logger.debug(f"Login attempt data: {data}")

        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email e password sono richiesti'}), 400

        user = User.query.filter_by(email=data['email']).first()
        if user and user.check_password(data['password']):
            login_user(user)
            logger.info(f"Login successful: {user.email}")
            return jsonify({
                'message': 'Login effettuato con successo',
                'redirect': '/dashboard'
            })

        logger.warning(f"Failed login attempt for email: {data.get('email')}")
        return jsonify({'error': 'Email o password non validi'}), 401

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Errore durante il login'}), 500

@app.context_processor
def utility_processor():
    return dict(get_locale=lambda: 'it')  # Default to Italian for now

app.register_blueprint(auth_bp)