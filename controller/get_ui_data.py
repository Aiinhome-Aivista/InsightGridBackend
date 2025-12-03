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

        if not all([session_id, session_name, file_name]):
            return build_response(False, "session_id, session_name, file_name required", 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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
            WHERE session_id=%s AND session_name=%s AND file_name=%s
        """, (session_id, session_name, file_name))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        ui_tables = []

        for tbl in results:

            # Fix: clean_columns should be a list (JSON array)
            clean_cols = tbl["clean_columns"]
            if isinstance(clean_cols, str):
                try:
                    clean_cols = json.loads(clean_cols)
                except:
                    clean_cols = []

            # Fix: column_metadata should be list of dicts
            col_meta = tbl["column_metadata"]
            if isinstance(col_meta, str):
                try:
                    col_meta = json.loads(col_meta)
                except:
                    col_meta = []

            # Fix: row_data should be list of rows
            rows = tbl["row_data"]
            if isinstance(rows, str):
                try:
                    rows = json.loads(rows)
                except:
                    rows = []

            ui_tables.append({
                "table_name": tbl["table_name"],
                "columns": clean_cols,
                "column_metadata": col_meta,
                "rows": rows,
                "insights": tbl["insights"],
                "insights_status": tbl["insights_status"],
                "relationships": tbl["relationships"],
                "relationship_extract_status": tbl["relationship_extract_status"]
            })

        return build_response(True, "UI Data fetched", 200, ui_tables)

    except Exception as e:
        return build_response(False, f"Error: {str(e)}", 500)