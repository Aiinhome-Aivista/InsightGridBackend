# controller/company_user_register.py
from flask import request,g
import uuid, bcrypt
from database.dbConnection import get_master_db, get_company_db
from helper.helperFunctions import build_response, generate_user_id

def company_user_register_controller():
    try:
        if not hasattr(g, "role") or not hasattr(g, "company_db_name"):
            return build_response(False, "Unauthorized", 401)

        if g.role != "companyadmin":
            return build_response(False, "Forbidden: CompanyAdmin only", 403)
        
        data = request.get_json() or {}

        # session_id = data.get("session_id")
        created_by = g.user_id
        company_code = data.get("company_code")

        name = data.get("user_name")
        email = data.get("user_email")
        password = data.get("password")

        if not all([created_by, company_code, name, email, password]):
            return build_response(False, "Required fields missing", 400)

        # =================================================
        # STEP 1: RESOLVE COMPANY (MASTER DB)
        # =================================================
        master = get_master_db()
        cur = master.cursor(dictionary=True)

        cur.execute("""
            SELECT id, company_db_name
            FROM companies
            WHERE company_code=%s AND is_active=1
        """, (company_code,))
        company = cur.fetchone()

        cur.close()
        master.close()

        if not company:
            return build_response(False, "Company not found", 404)

        company_id = company["id"]
        company_db_name = company["company_db_name"]

        # =================================================
        # STEP 2: CONNECT COMPANY DB + VALIDATE ADMIN
        # =================================================
        company_db = get_company_db(company_db_name)
        ccur = company_db.cursor(dictionary=True)

        # ccur.execute("""
        #     SELECT user_id
        #     FROM users
        #     WHERE user_id=%s AND session_id=%s
        # """, (created_by, session_id))

        # if not ccur.fetchone():
        #     return build_response(False, "Invalid session or user", 403)

        # =================================================
        # STEP 3: GET ROLE ID (user)
        # =================================================
        ccur.execute("SELECT id FROM user_roles WHERE role_name='user'")
        role = ccur.fetchone()

        if not role:
            return build_response(False, "User role not found", 500)

        role_id = role["id"]

        # =================================================
        # STEP 4: CHECK DUPLICATE EMAIL
        # =================================================
        ccur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if ccur.fetchone():
            return build_response(False, "Email already exists", 400)

        # =================================================
        # STEP 5: CREATE USER
        # =================================================
        user_id = generate_user_id(name.split()[0])

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        user_session_id = str(uuid.uuid4())

        ccur.execute("""
            INSERT INTO users (
                user_id, full_name, email, password_hash,
                app_role_id, company_id,
                created_by, created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
        """, (
            user_id,
            name,
            email,
            password_hash,
            role_id,
            company_id,
            created_by
        ))

        company_db.commit()

        return build_response(
            True,
            "User created successfully",
            200,
            {
                "user_id": user_id,
                "full_name": name,
                "user_email": email,
                "role": "user",
                "session_id": user_session_id,
                "company_code": company_code
            }
        )

    except Exception as e:
        return build_response(False, "Server error", 500, {"error": str(e)})
