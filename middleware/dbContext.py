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

#     # 🔥 ONLY session_id
#     if request.content_type and request.content_type.startswith("multipart"):
#         session_id = request.form.get("session_id")
#     else:
#         data = request.get_json(silent=True) or {}
#         session_id = data.get("session_id")

#     if not session_id:
#         return

#     master = get_master_db()
#     cur = master.cursor(dictionary=True)

#     cur.execute("""
#         SELECT user_id, company_db_name
#         FROM user_company_sessions
#         WHERE session_id = %s
#         LIMIT 1
#     """, (session_id,))

#     row = cur.fetchone()
#     cur.close()
#     master.close()

#     if row:
#         g.created_by = row["user_id"]
#         g.company_db = get_company_db(row["company_db_name"])

from flask import g, request
from database.dbConnection import get_company_db
from helper.jwt_middleware import jwt_protect


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

    if request.endpoint in skip_routes:
        return

    # 🔐 VERIFY JWT
    auth_error = jwt_protect()
    if auth_error:
        return auth_error

    # 🚫 Superadmin → no company DB
    if g.role == "superadmin":
        return

    # 🏢 Attach company DB
    if getattr(g, "company_db_name", None):
        g.company_db = get_company_db(g.company_db_name)

