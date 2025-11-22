from flask import request, jsonify
from werkzeug.security import check_password_hash
from database.dbConnection import get_db_connection

def login_controller():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"isSuccess": False, "message": "Email & password required","statusCode":400}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc("sp_login_user", [email])

        user = None
        for result in cursor.stored_results():
            user = result.fetchone()
            break

        if not user:
            return jsonify({"isSuccess": False, "message": "Invalid email or password","statusCode":401}), 401

        stored_hash = user.get("hashed_password")
        if not stored_hash or not check_password_hash(stored_hash, password):
            return jsonify({"isSuccess": False, "message": "Invalid email or password","statusCode":401}), 401

        user.pop("hashed_password", None)

        return jsonify({
            "isSuccess": True,
            "message": "Login successful",
            "data": user,
            "statusCode":200
            
        })

    except Exception as exc:
        print("Error:", exc)
        return jsonify({"isSuccess": False, "message": "Server error","statusCode":500}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()