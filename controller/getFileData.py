from flask import request
from database.dbConnection import get_db_connection
from utils.helper import build_response

def get_file_data_controller():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Call Stored Procedure
        cursor.callproc("sp_get_all_files")

        all_files = []
        for result in cursor.stored_results():
            all_files = result.fetchall()

        cursor.close()
        conn.close()

        if not all_files:
            return build_response(True, "No files found in the system", 200, data=[], status="success")

        response_data = []
        exclude_fields = {'id', 'status'}

        for file_data in all_files:
            file_info = {}
            for key, value in file_data.items():
                if key not in exclude_fields:
                    if key in ('created_at', 'updated_at'):
                        file_info[key] = str(value) if value else ''
                    else:
                        file_info[key] = value

            response_data.append(file_info)

        return build_response(
            True,
            f"Retrieved {len(response_data)} file(s) successfully",
            200,
            data=response_data,
            status="success",
        )

    except Exception as e:
        return build_response(False, "Failed to retrieve file data", 500, data={"error": str(e)}, status="error")
