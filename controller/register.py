from flask import request, jsonify
from database.dbConnection import get_db_connection
import bcrypt

def register_controller():
    try:
        data = request.get_json()

        user_id = data.get("user_id")
        name = data.get("name")
        role_id = int(data.get("role_id"))
        email = data.get("email")
        password = data.get("password")

        if not all([user_id, name, role_id, email, password]):
            return jsonify({
                "status": "failed",
                "statusCode": 400,
                "message": "All fields are required"
            }), 400

        # 🔥 BCRYPT HASH (this produces $2b$12$..... format)
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

        status = sp_result[0]
        new_user_id = sp_result[1]

        if status == "EMAIL_ALREADY_EXISTS":
            return jsonify({
                "isSuccess": False,
                "status": "failed",
                "statusCode": 400,
                "message": "Email already exists"
            }), 400

        return jsonify({
            "isSuccess": True,
            "status": "success",
            "statusCode": 200,
            "message": "User registered successfully",
            "new_user_id": new_user_id
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({
            "isSuccess": False,
            "status": "error",
            "statusCode": 500,
            "message": "Server error",
            "error": str(e)
        }), 500
