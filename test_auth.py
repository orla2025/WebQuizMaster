import logging
from app import app, db
from models import User
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_auth_routes():
    """Test authentication routes"""
    with app.test_client() as client:
        # Test registration
        logger.info("=== TESTING REGISTRATION ===")
        reg_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123"
        }
        
        response = client.post('/register', 
                             data=json.dumps(reg_data),
                             content_type='application/json')
        
        logger.info(f"Registration Response Status: {response.status_code}")
        logger.info(f"Registration Response Data: {response.get_data(as_text=True)}")

        # Test login
        logger.info("\n=== TESTING LOGIN ===")
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        
        response = client.post('/login',
                             data=json.dumps(login_data),
                             content_type='application/json')
        
        logger.info(f"Login Response Status: {response.status_code}")
        logger.info(f"Login Response Data: {response.get_data(as_text=True)}")

if __name__ == "__main__":
    with app.app_context():
        # Clean up any existing test user
        User.query.filter_by(email="test@example.com").delete()
        db.session.commit()
        
        # Run tests
        test_auth_routes()
