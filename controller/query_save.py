from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json

def query_save_controller():
    try:
        data = request.get_json()

        query_title = data.get("query_title")
        user_query = data.get("user_query")
        ai_response = data.get("ai_response")
        rows_effected = data.get("rows_effected")
        query_time = data.get("query_time")
        is_execute = data.get("is_execute")
        row_data = data.get("row_data")
        session_id = data.get("session_id")
        created_by = data.get("created_by")

        if not all([query_title, user_query, ai_response, session_id, created_by]):
            return build_response(False, "Missing required fields", 400)
        
        row_data_json = json.dumps(row_data) if row_data else None

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Validate session + user
        cursor.execute(
            "SELECT user_id, session_id FROM users WHERE session_id = %s AND user_id = %s LIMIT 1",
            (session_id, created_by)
        )
        if not cursor.fetchone():
            return build_response(False, "Invalid session_id or created_by", 400)

        # Call stored procedure
        cursor.callproc("sp_save_query", [
            query_title,
            user_query,
            ai_response,
            rows_effected,
            query_time,
            is_execute,
            row_data_json,
            session_id,
            created_by
        ])

        result = list(cursor.stored_results())[0].fetchone()

        conn.commit()
        cursor.close()
        conn.close()

        return build_response(True, "Chat saved", 200, result)

    except Exception as e:
        return build_response(False, f"Save Error: {str(e)}", 500)

