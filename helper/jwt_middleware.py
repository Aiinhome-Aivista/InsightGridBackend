from flask import request, g
from helper.jwt_helper import verify_token
from helper.helperFunctions import build_response


def jwt_protect():
    auth = request.headers.get("Authorization")

    if not auth or not auth.startswith("Bearer "):
        return build_response(False, "Authorization token missing", 401)

    token = auth.split(" ")[1]
    payload = verify_token(token)

    if not payload:
        return build_response(False, "Invalid or expired token", 401)

    # 🔥 attach decoded info globally
    g.user_id = payload.get("user_id")
    g.role = payload.get("role")
    g.company_id = payload.get("company_id")
    g.company_db_name = payload.get("company_db")

    return None
