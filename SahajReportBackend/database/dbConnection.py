import os
from dotenv import load_dotenv
import mysql.connector
# ---------- Load Environment Variables ----------
load_dotenv()
# ---------- Database Configuration ----------
MYSQL_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),  # default 3306 if not set
    "database": os.getenv("DB_NAME")
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        print("Database connection established.")
        return conn
    except mysql.connector.Error as err:
        raise Exception(f"Database connection error: {err}")