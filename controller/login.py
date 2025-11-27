from flask import request
import bcrypt
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def login_controller():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        email = data.get("user_email")
        password = data.get("password")

        if not email or not password:
            return build_response(False, "Email & password required", 400)

    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("sp_login_user", [email])

        user = None
        for result in cursor.stored_results():
            user = result.fetchone()
            break

        if not user:
            return build_response(False, "User not found!", 401)

        stored_hash = user.get("hashed_password")
        print("DB Hash:", stored_hash)

        if not stored_hash:
            return build_response(False, "Invalid password", 401)

        # bcrypt password check
        is_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8")
        )

        if not is_valid:
            return build_response(False, "Invalid email or password", 401)

        # Remove hashed password from response
        user.pop("hashed_password", None)

        return build_response(True, "Login successful", 200, user)

    except Exception as exc:
        print("Error:", exc)
        return build_response(False, "Server error", 500)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
