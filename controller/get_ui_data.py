import pandas as pd
from flask import request
import json
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def get_ui_data_controller():
    try:
        body = request.get_json() or {}

        session_id = body.get("session_id")
        session_name = body.get("session_name")
        file_name = body.get("file_name")
        table_name = body.get("table_name")   # <-- NEW

        if not all([session_id, session_name, file_name]):
            return build_response(False, "session_id, session_name, file_name required", 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ----------------------------------------------------------------------
        # MODE 1 → Return only table names for dropdown
        # ----------------------------------------------------------------------
        if not table_name:
            cursor.execute("""
                SELECT DISTINCT table_name 
                FROM processed_cleaned_table_data
                WHERE session_id=%s AND session_name=%s AND file_name=%s
            """, (session_id, session_name, file_name))

            tables = [row["table_name"] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return build_response(True, "Table list fetched", 200, {"tables": tables})


        # ----------------------------------------------------------------------
        # MODE 2 → Return full table data of the selected table
        # ----------------------------------------------------------------------
        cursor.execute("""
            SELECT 
                table_name,
                clean_columns,
                column_metadata,
                row_data,
                insights,
                relationships,
                insights_status,
                relationship_extract_status
            FROM processed_cleaned_table_data
            WHERE session_id=%s AND session_name=%s AND file_name=%s AND table_name=%s
        """, (session_id, session_name, file_name, table_name))

        tbl = cursor.fetchone()

        cursor.close()
        conn.close()

        if not tbl:
            return build_response(False, "No table found", 404)

        # Helper to parse JSON safely
        def parse_json(value):
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except:
                    return []
            return value or []

        response = {
            "table_name": tbl["table_name"],
            "columns": parse_json(tbl["clean_columns"]),
            "column_metadata": parse_json(tbl["column_metadata"]),
            "rows": parse_json(tbl["row_data"]),
            "insights": parse_json(tbl["insights"]),
            "relationships": parse_json(tbl["relationships"]),
            "insights_status": tbl["insights_status"],
            "relationship_extract_status": tbl["relationship_extract_status"]
        }

        return build_response(True, "UI Data fetched", 200, response)

    except Exception as e:
        return build_response(False, f"Error: {str(e)}", 500)
