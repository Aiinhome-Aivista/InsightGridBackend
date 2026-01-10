# controller/auth_company_login.py
from flask import request
import uuid, bcrypt
from database.dbConnection import get_master_db, get_company_db
from helper.helperFunctions import build_response
from helper.jwt_helper import generate_token


def company_login_controller():
    data = request.get_json() or {}

    company_code = data.get("company_code")
    email = data.get("user_email")
    password = data.get("password")
    login_type = data.get("login_type", "").strip().lower()  # companyadmin | user

    if not all([company_code, email, password, login_type]):
        return build_response(
            False,
            "company_code, user_email, password & login_type required",
            400
        )

    master = get_master_db()
    cur = master.cursor(dictionary=True)

    cur.execute(
       """
     SELECT 
    id,
    company_name,
    company_code,
    company_email,
    address,
    subscription_type,
    from_date,
    to_date,
    company_db_name,
    phone_number,
    company_logo
    FROM companies
    WHERE company_code=%s AND is_active=1
    """,
        (company_code,),
    )
    company = cur.fetchone()

    if not company:
        return build_response(False, "Company not found", 404)

    try:
        company_db = get_company_db(company["company_db_name"])
    except Exception:
        return build_response(False, "Company database unavailable", 500)
    ccur = company_db.cursor(dictionary=True)

    ccur.execute(
        """
        SELECT u.user_id, u.password_hash,ur.role_name, u.full_name,
        u.email
        FROM users u
        JOIN user_roles ur ON ur.id = u.app_role_id
        WHERE u.email=%s AND u.company_id=%s
    """,
        (email, company["id"]),
    )
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
    # 🔴 ADD THIS BLOCK (AFTER company_db.commit())

    # =========================
    # JWT TOKEN GENERATION
    # =========================
    token = generate_token(
        {
            "user_id": user["user_id"],
            "role": user["role_name"],
            "company_id": company["id"],
            "company_db": company["company_db_name"],
            "scope": "company",
        }
    )
    ccur.close()
    mcur = master.cursor()
    mcur.execute(
    """
    INSERT INTO user_company_sessions
    (user_id, company_id, company_db_name)
    VALUES (%s,%s,%s)
    ON DUPLICATE KEY UPDATE
        company_db_name = VALUES(company_db_name)
    """,
        (user["user_id"], company["id"], company["company_db_name"]),
    )

    master.commit()
    mcur.close()

    # return build_response(True, "Login successful", 200, {
    #     "user_id": user["user_id"],
    #     "role": user["role_name"],
    #     "company_code": company_code,
    #     "session_id": session_id
    # })
    # ---- build full logo url for PDF ----
    base_url = request.host_url.rstrip("/")  # http://127.0.0.1:3008
    logo_path = company["company_logo"]  # /uploads/companies/...

    company_logo_url = f"{base_url}{logo_path}" if logo_path else None

    return build_response(
        True,
        "Login successful",
        200,
        {
            # ---------- USER ----------
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "user_email": user["email"],
            "role": user["role_name"],
            # ---------- COMPANY ----------
            "company_id": company["id"],
            "company_name": company["company_name"],
            "company_code": company["company_code"],
            "company_email": company["company_email"],
            "company_address": company["address"],
            "company_logo": company["company_logo"],
            "company_logo_url": company_logo_url,
            "company_phone": company["phone_number"],
            "subscription_type": company["subscription_type"],
            "subscription_from": str(company["from_date"]),
            "subscription_to": str(company["to_date"]),
            "token": token
        }
    )