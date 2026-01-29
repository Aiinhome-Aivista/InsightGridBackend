from flask import request, g
from helper.helperFunctions import build_response
from datetime import timedelta, datetime


def get_report_schedules_controller():
    try:
        body = request.get_json() or {}
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)

        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        db = g.company_db
        cursor = db.cursor(dictionary=True)

        # -----------------------------
        # VALIDATE USER SESSION
        # -----------------------------
        cursor.execute(
            """
            SELECT 1
            FROM users
            WHERE user_id = %s
              AND session_id = %s
            LIMIT 1
            """,
            (created_by, session_id)
        )

        if not cursor.fetchone():
            cursor.close()
            return build_response(False, "Invalid session", 401)

        # -----------------------------
        # FETCH SCHEDULES (NO DATE_FORMAT / NO %)
        # -----------------------------
        cursor.execute(
            """
            SELECT
                rs.id,
                rs.report_id,
                sr.report_name,
                rs.schedule_name,
                rs.recipient_to,
                rs.recipient_cc,
                rs.schedule_time,
                rs.frequency,
                rs.selected_days,
                rs.is_active,
                rs.last_run,
                rs.created_at
            FROM report_schedules rs
            LEFT JOIN saved_reports sr
              ON rs.report_id = sr.report_id
             AND sr.user_id = %s
             AND sr.session_id = %s
            WHERE rs.created_by = %s
              AND rs.user_session_id = %s
            ORDER BY rs.created_at DESC
            """,
            (created_by, session_id, created_by, session_id)
        )

        schedules = cursor.fetchall()
        cursor.close()

        # -----------------------------
        # PYTHON SIDE SERIALIZATION
        # -----------------------------
        for row in schedules:
            if isinstance(row.get("schedule_time"), timedelta):
                total_seconds = int(row["schedule_time"].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                row["schedule_time"] = f"{hours:02d}:{minutes:02d}"

            if isinstance(row.get("created_at"), datetime):
                row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(row.get("last_run"), datetime):
                row["last_run"] = row["last_run"].strftime("%Y-%m-%d %H:%M:%S")

        return build_response(
            True,
            "Report schedules retrieved",
            200,
            schedules
        )

    except Exception as e:
        return build_response(
            False,
            "Failed to fetch report schedules",
            500,
            {"error": str(e)}
        )