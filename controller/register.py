from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response, generate_user_id
import bcrypt

def register_controller():
    try:
        data = request.get_json()
        # print("Received registration data:", data)
        name = data["user_name"]
        role_id = int(data["role_id"])
        email = data["user_email"]
        password = data["password"]

         # CASE 1: Entire payload missing
        if not data:
            return build_response(
                False, "All fields are required", 400, status="failed"
            )

        # Required fields
        required_fields = {
            "user_name": "User name is required",
            "role_id": "Role ID is required",
            "user_email": "User email is required",
            "password": "Password is required"
        }

        # CASE 2: Individual missing fields
        for field, error_msg in required_fields.items():
            if not data.get(field):
                return build_response(
                    False, error_msg, 400, status="failed"
                )
        # Auto-generate user_id using firstname
        firstname = (name or "").strip().split()[0] if (name and name.strip()) else None
        # take first name from full name
        user_id = generate_user_id(firstname)

        # BCRYPT HASH 
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.callproc("sp_register_procedure", (
            user_id,
            name,
            role_id,
            email,
            hashed_password
        ))
        conn.commit()
        sp_result = None
        for result in cursor.stored_results():
            sp_result = result.fetchone()
        print("SP Result:", sp_result)
        cursor.close()
        conn.close()

        if not sp_result:
            return build_response(False, "Registration failed", 500, status="error")

        status_flag, new_user_id = sp_result

        if status_flag.strip().lower() == "email already exists":
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