from flask import request
from database.dbConnection import get_db_connection
from utils.helper import build_response
import bcrypt

def register_controller():
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        name = data.get("name")
        role_id = int(data.get("role_id"))
        email = data.get("email")
        password = data.get("password")

        if not all([user_id, name, role_id, email, password]):
            return build_response(False, "All fields are required", 400, status="failed")

        # BCRYPT HASH 
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "CALL register_procedure(%s, %s, %s, %s, %s)",
            (user_id, name, role_id, email, hashed_password)
        )

        sp_result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not sp_result:
            return build_response(False, "Registration failed", 500, status="error")

        status_flag, new_user_id = sp_result

        if status_flag == "EMAIL_ALREADY_EXISTS":
            return build_response(False, "Email already exists", 400, status="failed")

        return build_response(
            True,
            "User registered successfully",
            200,
            status="success",
            extra={"new_user_id": new_user_id},
        )

    except Exception as e:
        print("Error:", e)
        return build_response(False, "Server error", 500, data={"error": str(e)}, status="error")
