from flask import request, g
from helper.helperFunctions import build_response

def get_saved_reports_dropdown_controller():
    try:
        body = request.get_json() or {}
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        # -----------------------------
        # BASIC VALIDATION
        # -----------------------------
        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)

        # -----------------------------
        # COMPANY DB CHECK
        # -----------------------------
        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        db = g.company_db
        cursor = db.cursor(dictionary=True)

        # -----------------------------
        # VALIDATE USER SESSION
        # -----------------------------
        cursor.execute("""
            SELECT 1
            FROM users
            WHERE user_id = %s
              AND session_id = %s
            LIMIT 1
        """, (created_by, session_id))

        if not cursor.fetchone():
            cursor.close()
            return build_response(False, "Invalid session", 401)

        # -----------------------------
        # FETCH REPORTS
        # -----------------------------
        cursor.execute("""
            SELECT 
                report_id AS value,
                report_name AS label
            FROM saved_reports
            WHERE user_id = %s
              AND session_id = %s
            ORDER BY created_at DESC
        """, (created_by, session_id))

        reports = cursor.fetchall()
        cursor.close()

        return build_response(
            True,
            "Saved reports retrieved",
            200,
            reports
        )

    except Exception as e:
        return build_response(
            False,
            "Failed to fetch saved reports",
            500,
            {"error": str(e)}
        )