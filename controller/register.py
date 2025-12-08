from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response, generate_user_id
import bcrypt

def register_controller():
    try:
        data = request.get_json()

        # CASE 1: Entire payload missing
        if not data:
            return build_response(False, "All fields are required", 400, status="failed")

        name = data.get("user_name")
        role_id = data.get("role_id")
        email = data.get("user_email")
        password = data.get("password")

        # CASE 2: Check missing individual fields
        required_fields = {
            "user_name": "User name is required",
            "role_id": "Role ID is required",
            "user_email": "User email is required",
            "password": "Password is required"
        }

        for field, message in required_fields.items():
            if not data.get(field):
                return build_response(False, message, 400, status="failed")

        # Auto-generate user_id
        firstname = (name.strip().split()[0]) if name and name.strip() else "user"
        user_id = generate_user_id(firstname)

        # Password hashing
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # DB connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Call Stored Procedure
        cursor.callproc("sp_register", (
            user_id,
            name,
            int(role_id),
            email,
            hashed_password
        ))
        conn.commit()

        # Fetch SP result
        sp_result = None
        for result in cursor.stored_results():
            sp_result = result.fetchone()

        cursor.close()
        conn.close()

        if not sp_result:
            return build_response(False, "Registration failed", 500, status="error")

        status_flag, new_user_id = sp_result

        # CASE: Email already exists
        if status_flag == "EMAIL_ALREADY_EXISTS":
            return build_response(False, "Email already exists", 400, status="failed")

        # SUCCESS
        return build_response(
            True,
            "User registered successfully",
            200,
            status="success",
            extra={"new_user_id": new_user_id}
        )

    except Exception as e:
        print("Error:", e)
        return build_response(
            False,
            "Server error",
            500,
            data={"error": str(e)},
            status="error"
        )
