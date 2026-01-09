# controller/auth_company_login.py
from flask import request
import bcrypt
from database.dbConnection import get_master_db, get_company_db
from helper.helperFunctions import build_response
from helper.jwt_helper import generate_token


def company_login_controller():
    data = request.get_json() or {}

    company_code = data.get("company_code")
    email = data.get("user_email")
    password = data.get("password")
    login_type = data.get("login_type")  # companyadmin | user

    if not all([company_code, email, password, login_type]):
        return build_response(
            False,
            "company_code, user_email, password & login_type required",
            400
        )

    # ==================================================
    # STEP 1: Get company from MASTER DB
    # ==================================================
    master = get_master_db()
    mcur = master.cursor(dictionary=True)

    mcur.execute("""
        SELECT id, company_db_name
        FROM companies
        WHERE company_code = %s AND is_active = 1
    """, (company_code,))

    company = mcur.fetchone()

    if not company:
        return build_response(False, "Company not found", 404)

    company_db_name = company["company_db_name"]

    # ==================================================
    # STEP 2: Connect COMPANY DB
    # ==================================================
    company_db = get_company_db(company_db_name)
    ccur = company_db.cursor(dictionary=True)

    # 🔴 IMPORTANT: company_id condition REMOVED
    ccur.execute("""
        SELECT
            u.user_id,
            u.full_name,
            u.email,
            u.password_hash,
            ur.role_name
        FROM users u
        JOIN user_roles ur ON ur.id = u.app_role_id
        WHERE u.email = %s
    """, (email,))

    user = ccur.fetchone()

    if not user:
        return build_response(False, "Invalid credentials", 401)

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return build_response(False, "Invalid credentials", 401)

    # ==================================================
    # STEP 3: LOGIN TYPE vs ROLE VALIDATION
    # ==================================================
    LOGIN_ROLE_MAP = {
        "companyadmin": "companyadmin",
        "user": "user"
    }

    expected_role = LOGIN_ROLE_MAP.get(login_type)

    if not expected_role:
        return build_response(False, "Invalid login type", 400)

    if user["role_name"] != expected_role:
        return build_response(
            False,
            f"{user['role_name']} cannot login as {login_type}",
            403
        )

    # ==================================================
    # STEP 4: JWT TOKEN
    # ==================================================
    token = generate_token({
        "user_id": user["user_id"],
        "role": user["role_name"],
        "company_code": company_code,
        "company_db": company_db_name,
        "scope": "company"
    })

    return build_response(
        True,
        "Login successful",
        200,
        {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role_name"],
            "company_code": company_code,
            "company_db": company_db_name,
            "token": token
        }
    )
