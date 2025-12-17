from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response


def get_file_status_controller():
    try:
        body = request.get_json()

        created_by = body.get("created_by")
        session_id = body.get("session_id")

        # VALIDATION
        if not created_by:
            return build_response(False, "created_by is required", 400, status="failed")

        if not session_id:
            return build_response(False, "session_id is required", 400, status="failed")

        con = get_db_connection()
        cursor = con.cursor(dictionary=True)
        #  VALIDATE SESSION ID & created_by
        # -----------------------------------
        cursor.execute(
            "SELECT user_id, session_id FROM users WHERE session_id = %s AND user_id = %s LIMIT 1",
            (session_id, created_by)
        )
        session_row = cursor.fetchone()

        if not session_row:
            cursor.close()
            con.close()
            return build_response(
                False,
                "Invalid session_id or created_by",
                400
                # {"status": "failed"}
            )

        # CALL SP
        cursor.callproc("sp_get_uploaded_files_status", [created_by, session_id])

        stored = list(cursor.stored_results())
        result = stored[0].fetchall() if stored else []

        cursor.close()
        con.close()

        # NO DATA FOUND
        if not result:
            return build_response(
                True,
                "No data found",
                200,
                data=[],
                status="success"
            )
        # if not result:
        #     return build_response(
        #         True,
        #         "No metadata yet, default pending status",
        #         200,
        #         data=[{
        #             "file_id": None,
        #             "file_name": None,
        #             "table_name": None,
        #             "total_rows": 0,
        #             "total_columns": 0,
        #             "table_extraction_status": "pending",
        #             "column_extraction_status": "pending",
        #             "data_insights_status": "pending"
        #         }],
        #         status="success"
        #     )

        # SUCCESS RESPONSE
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