from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def delete_uploaded_file_controller():
    conn = None
    cursor = None

    try:
        data = request.get_json() or {}

        session_id = data.get("session_id")
        created_by = data.get("created_by")
        file_name = data.get("file_name")

        # Basic validation
        if not session_id or not created_by or not file_name:
            return build_response(False, "session_id, created_by & file_name required", 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔥 Stored Procedure Call
        cursor.callproc("sp_delete_uploaded_file", [
            session_id,
            created_by,
            file_name
        ])

        # Fetch SP Output
        sp_result = None
        for rs in cursor.stored_results():
            sp_result = rs.fetchone()
            break

        conn.commit()

        if not sp_result:
            return build_response(False, "Unexpected: No response from stored procedure", 500)

        status_msg = sp_result.get("status", "No status returned")

        # FINAL RESPONSE → only message, no data
        return build_response(True, status_msg, 200)

    except Exception as e:
        return build_response(False, f"Delete Error: {str(e)}", 500)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
