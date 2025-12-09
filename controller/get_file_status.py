from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def get_file_status_controller():
    try:
        body = request.get_json()

        created_by = body.get("created_by")   # user_id now (NOT email)
        session_id = body.get("session_id")   # session from login

        # --------------------------
        # BASIC VALIDATION
        # --------------------------
        if not created_by:
            return build_response(False, "created_by (user_id) is required", 400, status="failed")

        if not session_id:
            return build_response(False, "session_id is required", 400, status="failed")

        con = get_db_connection()
        cur = con.cursor(dictionary=True)

        # --------------------------
        # 1️⃣ VALIDATE SESSION ID
        # --------------------------
        cur.execute(
            "SELECT user_id FROM users WHERE session_id=%s LIMIT 1",
            (session_id,)
        )
        session_row = cur.fetchone()

        if not session_row:
            cur.close()
            con.close()
            return build_response(False, "Invalid session_id", 400, status="failed")

        # --------------------------
        # 2️⃣ VALIDATE USER_ID MATCHES SESSION OWNER
        # --------------------------
        if session_row["user_id"] != created_by:
            cur.close()
            con.close()
            return build_response(
                False,
                "Unauthorized: session does not belong to this user",
                401,
                status="failed"
            )

        # --------------------------
        # 3️⃣ CALL STORED PROCEDURE SAFELY
        # --------------------------
        cur.callproc("sp_get_uploaded_files_status", [created_by, session_id])

        stored = list(cur.stored_results())
        result = stored[0].fetchall() if stored else []

        cur.close()
        con.close()

        # --------------------------
        # 4️⃣ NO DATA CASE
        # --------------------------
        if not result:
            return build_response(
                True,
                "No files uploaded yet",
                200,
                data=[],
                status="success"
            )

        # --------------------------
        # 5️⃣ SUCCESS
        # --------------------------
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
