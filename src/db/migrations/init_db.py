from src.db.models import init_db, SessionLocal, Token, Opportunity, Trade

def setup_database():
    print("Initializing database tables...")
    init_db()
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    setup_database()
