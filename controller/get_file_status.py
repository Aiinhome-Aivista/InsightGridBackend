from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def get_file_status_controller():
    try:
        body = request.get_json() or {}

        created_by = body.get("created_by")
        session_id = body.get("session_id")

        # VALIDATION
        if not created_by:
            return build_response(False, "created_by is required", 400, status="failed")

        if not session_id:
            return build_response(False, "session_id is required", 400, status="failed")

        con = get_db_connection()
        cur = con.cursor(dictionary=True)

        # CALL SP
        cur.callproc("sp_get_uploaded_files_status", [created_by, session_id])

        stored = list(cur.stored_results())
        result = stored[0].fetchall() if stored else []

        cur.close()
        con.close()

        # --------------------------------------------
        # NO DATA FOUND CASE
        # --------------------------------------------
        if not result:
            return build_response(
                False,
                "No data found",
                404,
                data=[],
                status="failed"
            )

        # --------------------------------------------
        # SUCCESS RESPONSE
        # --------------------------------------------
        return build_response(
            True,
            "Status fetched successfully",
            200,
            data=result,
            status="success"
        )

    except Exception as e:
        return build_response(
            False,
            "Server Error",
            500,
            data={"error": str(e)},
            status="error"
        )
