from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def get_tracker_controller():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Call Stored Procedure
        cursor.callproc("sp_get_all_files")

        files_data = []
        for result in cursor.stored_results():
            files_data = result.fetchall()

        cursor.close()
        conn.close()

        if not files_data:
            return build_response(True, "No files found in the system", 200, data=[], status="success")


        return build_response(
            True,
            f"Retrieved {len(files_data)} file(s) successfully",
            200,
            data=files_data,
            status="success",
        )

    except Exception as e:
        return build_response(False, "Failed to retrieve file data", 500, data={"error": str(e)}, status="error")
