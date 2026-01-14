# from flask import request, g
# from database.dbConnection import get_master_db, get_company_db

# def attach_company_db():
#     skip_routes = (
#        "hello_world",

#         # auth
#         "superadmin_login",
#         "company_login",

#         # company creation
#         "admin_company_register_route",
#         "admin_company_admin_register_route",
#     )

#     if request.endpoint in skip_routes:
#         return

#     data = request.get_json(silent=True) or {}
#     session_id = data.get("session_id")
#     created_by = data.get("created_by")

#     if not session_id or not created_by:
#         return {
#             "isSuccess": False,
#             "message": "session_id & created_by required",
#             "statusCode": 400
#         }

#     master = get_master_db()
#     cur = master.cursor(dictionary=True)

#     cur.execute("""
#         SELECT c.company_db_name
#         FROM users u
#         JOIN companies c ON c.id = u.company_id
#         WHERE u.session_id = %s
#           AND u.user_id = %s
#     """, (session_id, created_by))

#     row = cur.fetchone()
#     cur.close()
#     master.close()

#     if not row:
#         return {
#             "isSuccess": False,
#             "message": "Invalid session",
#             "statusCode": 403
#         }

#     g.company_db = get_company_db(row["company_db_name"])


# from flask import request, g
# from database.dbConnection import get_master_db, get_company_db

# def attach_company_db():
#     skip_routes = (
#         "hello_world",
#         "superadmin_login",
#         "company_login",
#         "admin_company_register_route",
#         "admin_company_admin_register_route",
#     )

#     if request.endpoint in skip_routes:
#         return

#     data = request.get_json(silent=True) or {}
#     session_id = data.get("session_id")
#     created_by = data.get("created_by")

#     # 👉 silently skip, controller will validate
#     if not session_id or not created_by:
#         return

#     master = get_master_db()
#     cur = master.cursor(dictionary=True)

#     cur.execute("""
#         SELECT c.company_db_name
#         FROM users u
#         JOIN companies c ON c.id = u.company_id
#         WHERE u.session_id = %s
#           AND u.user_id = %s
#     """, (session_id, created_by))

#     row = cur.fetchone()
#     cur.close()
#     master.close()

#     if row:
#         g.company_db = get_company_db(row["company_db_name"])

# from flask import request, g
# from database.dbConnection import get_master_db, get_company_db

# def attach_company_db():
#     skip_routes = (
#         "hello_world",
#         "superadmin_login",
#         "company_login",
#         "admin_company_register_route",
#         "admin_company_admin_register_route",
#     )

#     if request.endpoint in skip_routes:
#         return

#     # 🔴 THIS IS THE FIX
#     if request.content_type and request.content_type.startswith("multipart"):
#         session_id = request.form.get("session_id")
#         created_by = request.form.get("created_by")
#     else:
#         data = request.get_json(silent=True) or {}
#         session_id = data.get("session_id")
#         created_by = data.get("created_by")

#     if not session_id or not created_by:
#         return

#     master = get_master_db()
#     cur = master.cursor(dictionary=True)

#     cur.execute("""
#         SELECT company_db_name
#         FROM user_company_sessions
#         WHERE session_id = %s
#           AND user_id = %s
#     """, (session_id, created_by))

#     row = cur.fetchone()
#     cur.close()
#     master.close()

#     if row:
#         g.company_db = get_company_db(row["company_db_name"])


from flask import request, g
from database.dbConnection import get_master_db, get_company_db

def attach_company_db():
    skip_routes = (
        # "hello_world",
        # "superadmin_login",
        # "company_login",
        # "admin_company_register_route",
        # "admin_company_admin_register_route",
        "/",
        "/superadmin/login",
        "/company/login",
        "/admin/company_register",
        "/admin/company/admin_register",
        "/admin/get_companies",
    
    )

    if request.path  in skip_routes:
        return

    # 🔥 ONLY session_id
    if request.content_type and request.content_type.startswith("multipart"):
        session_id = request.form.get("session_id")
    else:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")

    if not session_id:
        return

    master = get_master_db()
    cur = master.cursor(dictionary=True)

    cur.execute("""
        SELECT user_id, company_db_name
        FROM user_company_sessions
        WHERE session_id = %s
        LIMIT 1
    """, (session_id,))

    row = cur.fetchone()
    cur.close()
    master.close()

    if row:
        g.created_by = row["user_id"]
        g.company_db = get_company_db(row["company_db_name"])

