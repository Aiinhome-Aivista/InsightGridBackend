import json
from flask import request, g
from helper.helperFunctions import build_response

def save_report_schedule_controller():
    try:
        data = request.get_json() or {}

        schedule_id = data.get("schedule_id")   #  ADD হলে None, EDIT হলে id
        schedule_name = data.get("schedule_name")   

        session_id = data.get("session_id")
        user_id = data.get("created_by")

        report_id = data.get("report_id")
        # mail_title = data.get("mail_title")
        # mail_body = data.get("mail_body")
        recipient_to = data.get("to")
        recipient_cc = data.get("cc", [])
        schedule_time = data.get("schedule_time")
        frequency = data.get("frequency")
        selected_days = data.get("selected_days")
        is_active = data.get("is_active", True)

        # ✅ Required validation
        if not all([session_id, user_id, report_id, recipient_to, schedule_time, frequency]):
            return build_response(False, "Missing required scheduling fields", 400)

        # ✅ DB check
        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        conn = g.company_db
        cur = conn.cursor()

        # ✅ User validation
        cur.execute(
            "SELECT 1 FROM users WHERE session_id=%s AND user_id=%s",
            (session_id, user_id)
        )
        if not cur.fetchone():
            cur.close()
            return build_response(False, "Invalid session or user", 401)

        # ✅ SP call
        args = (
            schedule_id,
            schedule_name,
            report_id,
            user_id,
            " ",
            " ",
            json.dumps(recipient_to),
            json.dumps(recipient_cc),
            schedule_time,
            frequency,
            selected_days,
            int(is_active),
            session_id
        )

        cur.callproc("sp_save_or_update_report_schedule", args)
        conn.commit()
        cur.close()

        return build_response(True, "Report schedule saved successfully", 200)

    except Exception as e:
        return build_response(False, "Server Error", 500, {"error": str(e)})