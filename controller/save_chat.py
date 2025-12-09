# from flask import request
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response

# def save_chat_controller():
#     try:
#         data = request.get_json()

#         session_id = data.get("session_id")
#         session_name = data.get("session_name")
#         file_name = data.get("file_name")
#         table_name = data.get("table_name")
#         chat_title = data.get("chat_title")  # NEW FIELD
#         user = data.get("user", "system")

#         messages = data.get("messages", [])

#         if not messages:
#             if not data.get("user_query") or not data.get("user_response"):
#                 return build_response(False, "Missing user_query or user_response", 400)

#             messages = [{
#                 "user_query": data.get("user_query"),
#                 "user_response": data.get("user_response")
#             }]

#         if not session_id or not session_name or not file_name:
#             return build_response(False, "session_id, session_name, file_name required", 400)

#         conn = get_db_connection()
#         cursor = conn.cursor()

#         for msg in messages:
#             cursor.callproc("sp_save_chat", [
#                 session_id,
#                 session_name,
#                 file_name,
#                 table_name,
#                 chat_title,                # NEW FIELD
#                 msg["user_query"],
#                 msg["user_response"],
#                 user
#             ])

#         conn.commit()
#         cursor.close()
#         conn.close()

#         return build_response(True, "Chat saved successfully", 200)

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)

from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json


def save_chat_controller():
    try:
        data = request.get_json()

        chat_title    = data.get("chat_title")
        user_query    = data.get("user_query")
        is_execute    = data.get("is_execute")
        user_response = data.get("ai_response")
        created_by    = data.get("created_by")
        table_data    = data.get("table_data")

        table_data_json = json.dumps(table_data)
        # Validate only required 5 fields
        if not chat_title or not user_query or user_response is None or not table_data:
            return build_response(False, "chat_title, user_query, user_response, table_data required", 400)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Call stored procedure with only 5 values
        cursor.callproc("sp_save_chat", [
            chat_title,
            user_query,
            is_execute,
            user_response,
            created_by,
            table_data_json
        ])

        conn.commit()
        cursor.close()
        conn.close()

        return build_response(True, "Chat saved successfully", 200)

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)