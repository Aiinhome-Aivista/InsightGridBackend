from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def get_dashboard_data_controller():
    try:
        body = request.get_json()
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        #  VALIDATE SESSION ID & created_by
        # -----------------------------------
        cursor.execute(
            "SELECT user_id, session_id FROM users WHERE session_id = %s AND user_id = %s LIMIT 1",
            (session_id, created_by)
        )
        session_row = cursor.fetchone()

        if not session_row:
            cursor.close()
            db.close()
            return build_response(
                False,
                "Invalid session_id or created_by",
                400
            )


        cursor.callproc("sp_get_dashboard_data", (created_by,))

        result_sets = []
        for result in cursor.stored_results():
            result_sets.append(result.fetchall())  # list of 6 lists

        cursor.close()
        conn.close()

        # SAFE EXTRACTION
        dashboard_data = {
            "total_uploaded_files": result_sets[0][0].get("total_uploaded_files", 0),
            "total_extracted_files": result_sets[1][0].get("table_extract_status", 0),
            "total_reports_generated": result_sets[2][0].get("total_reports_generated", 0),
            "total_queries": result_sets[3][0].get("total_queries", 0),
            "working_queries": result_sets[4][0].get("working_queries", 0),
            "latest_file": result_sets[5][0] if len(result_sets[5]) > 0 else None
        }

        return build_response(True, "Dashboard data retrieved", 200, data=dashboard_data)

    except Exception as e:
        return build_response(False, "Failed to retrieve dashboard data", 500, data={"error": str(e)})