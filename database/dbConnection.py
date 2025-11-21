import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ---------- Load Environment Variables ----------
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# ---------- SQLAlchemy Connection String ---------
def get_db_connection():
    try:
        connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(connection_string)
        
        # Test connection
        with engine.connect() as conn:
            print(" Connected successfully!")
        return engine

    except Exception as e:
        # print(" Connection failed. Check log file for details.")
        print(f"Error details: {e}")

