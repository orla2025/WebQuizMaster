import logging
from app import db, app
from sqlalchemy import text

logger = logging.getLogger(__name__)

def test_database_connection():
    """Test the database connection and table creation"""
    with app.app_context():
        try:
            # Test basic connection
            logger.info("Testing database connection...")
            result = db.session.execute(text("SELECT 1")).scalar()
            logger.info(f"Database connection test: {result}")

            # Check existing tables
            logger.info("Checking existing tables...")
            tables = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).fetchall()
            logger.info("=== DATABASE TABLES ===")
            logger.info(f"Found tables: {[table[0] for table in tables]}")
            logger.info("=====================")

            # Verify models are registered
            logger.info("=== REGISTERED MODELS ===")
            logger.info(f"Models: {list(db.metadata.tables.keys())}")
            logger.info("========================")

            return True
        except Exception as e:
            logger.error("=== DATABASE ERROR ===")
            logger.error(f"Error details: {str(e)}")
            logger.error("====================")
            return False

if __name__ == "__main__":
    # Set logging to DEBUG for maximum visibility
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    test_database_connection()