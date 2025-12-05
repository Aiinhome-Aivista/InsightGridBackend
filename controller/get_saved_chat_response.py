from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response


def get_chat_history_by_user_controller():
    try:
        data = request.get_json()

        created_by = data.get("created_by")

        if not created_by:
            return build_response(False, "created_by is required", 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc("sp_get_chat_history_by_user", [
            created_by
        ])

        result = []
        for rs in cursor.stored_results():
            result = rs.fetchall()

        cursor.close()
        conn.close()

        return build_response(True, "Chat history loaded", 200, data=result)

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)

# def get_chat_history_controller():
#     try:
#         data = request.get_json()

#         session_id = data.get("session_id")
#         session_name = data.get("session_name")
#         file_name = data.get("file_name")

#         if not session_id or not session_name or not file_name:
#             return build_response(False, "Missing required fields", 400)

#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         cursor.callproc("sp_get_chat_history", [
#             session_id,
#             session_name,
#             file_name
#         ])

#         result = []
#         for rs in cursor.stored_results():
#             result = rs.fetchall()

#         cursor.close()
#         conn.close()

#         return build_response(True, "Chat history loaded", 200, data=result)

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)
