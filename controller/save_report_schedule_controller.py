import json
from flask import request, g
from helper.helperFunctions import build_response

def save_report_schedule_controller():
    try:
        data = request.get_json()

        # ফ্রন্টেন্ড থেকে ডাটা সংগ্রহ
        session_id = data.get("session_id")
        user_id = data.get("created_by")
        report_id = data.get("report_id")
        mail_title = data.get("mail_title")
        mail_body = data.get("mail_body")
        recipient_to = data.get("to")
        recipient_cc = data.get("cc", [])
        schedule_time = data.get("schedule_time")
        frequency = data.get("frequency")
        selected_days = data.get("selected_days")
        is_active = data.get("is_active", True)

        # ১. রিকোয়ার্ড ফিল্ড ভ্যালিডেশন
        if not all([session_id, user_id, report_id, mail_title, recipient_to, schedule_time, frequency]):
            return build_response(False, "Missing required scheduling fields", 400)

        # ২. ডাটাবেস কানেকশন চেক
        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        conn = g.company_db
        cur = conn.cursor(dictionary=True)

        # ৩. ইউজার ভ্যালিডেশন
        cur.execute("SELECT 1 FROM users WHERE session_id=%s AND user_id=%s", (session_id, user_id))
        if not cur.fetchone():
            cur.close()
            return build_response(False, "Invalid session or user", 401)

        # ৪. Stored Procedure কল করা
        args = [
            report_id,
            session_id,
            user_id,
            mail_title,
            mail_body,
            json.dumps(recipient_to), # JSON ডাটা MySQL এর জন্য স্ট্রিং করতে হয়
            json.dumps(recipient_cc),
            schedule_time,
            frequency,
            selected_days,
            is_active
        ]

        # sp_save_or_update_report_schedule কল হচ্ছে
        cur.callproc("sp_save_or_update_report_schedule", args)
        
        conn.commit()
        cur.close()

        return build_response(True, "Report schedule processed successfully", 200)

    except Exception as e:
        return build_response(False, "Server Error", 500, {"error": str(e)})