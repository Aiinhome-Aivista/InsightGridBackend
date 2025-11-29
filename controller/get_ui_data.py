import pandas as pd
from flask import request
import json
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response

def get_ui_data_controller():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        session_name = data.get("session_name")
        file_name = data.get("file_name")

        if not session_id or not session_name or not file_name:
            return build_response(False, "session_id, session_name, file_name required", 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc("sp_get_processed_ui_data", [
            session_id,
            session_name,
            file_name
        ])

        result_sets = []
        for rs in cursor.stored_results():
            result_sets.append(rs.fetchall())

        cursor.close()
        conn.close()

        # Result 1 → global operations
        global_operations = {}

        if len(result_sets) > 0 and len(result_sets[0]) > 0:
            global_operations = json.loads(result_sets[0][0]["global_operations"])

        # Result 2 → table list
        tables_raw = result_sets[1]
        tables_output = []

        for tbl in tables_raw:

            # FIX #1: decode JSON fields
            column_meta = json.loads(tbl["column_metadata"]) if tbl["column_metadata"] else []
            row_data = json.loads(tbl["row_data"]) if tbl["row_data"] else {}

            # FIX #2: generate default_columns
            default_columns = [
                {
                    "column_id": col["column_id"],
                    "column_name": col["column_name"],
                    "column_type": col["column_type"]
                }
                for col in column_meta
            ]

            # FIX #3: extract rows safely
            rows = row_data.get("rows", [])

            tables_output.append({
                "table_name": tbl["table_name"],
                "default_columns": default_columns,
                "rows": rows
            })

        return build_response(True, "UI Data Loaded", 200, data={
            "session_id": session_id,
            "session_name": session_name,
            "file_name": file_name,
            "global_operations": global_operations,
            "tables": tables_output
        })

    except Exception as e:
        return build_response(False, f"Error: {str(e)}", 500)