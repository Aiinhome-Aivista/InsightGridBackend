from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json


def get_uploaded_table_with_tabledata_controller():
    try:
        body = request.get_json()
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)

        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        # -----------------------------
        # VALIDATE USER SESSION
        # -----------------------------
        cur.execute("""
            SELECT user_id FROM users
            WHERE user_id=%s AND session_id=%s
            LIMIT 1
        """, (created_by, session_id))

        if not cur.fetchone():
            cur.close(); db.close()
            return build_response(False, "Invalid session", 400)

        # -----------------------------
        # CALL STORED PROCEDURE
        # -----------------------------
        cur.callproc("sp_get_uploaded_file_with_table_data", (session_id, created_by))

    #     result_sets = []
    #     for rs in cur.stored_results():
    #         result_sets.append(rs.fetchall())

    #     cur.close()
    #     db.close()

    #     if len(result_sets) < 3:
    #         return build_response(False, "Unexpected SP result", 500)

    #     # ----------------------------------------
    #     # RESULTSET 1 → uploaded_files metadata
    #     # ----------------------------------------
    #     uploaded_files = result_sets[0]

    #     # ----------------------------------------
    #     # RESULTSET 2 → table names
    #     # ----------------------------------------
    #     table_names = [row["table_name"] for row in result_sets[1]]

    #     # build dropdown
    #     tables_dropdown = [
    #         {"label": t, "value": t} for t in table_names
    #     ]

    #     # ----------------------------------------
    #     # RESULTSET 3 → all table rows (union)
    #     # ----------------------------------------
    #     all_table_rows = result_sets[2]  # full merged rows

    #     # # Group by table_name → table data object
    #     # tables_data = {t: [] for t in table_names}

    #     # for row in all_table_rows:
    #     #     tbl = row.get("table_name") if "table_name" in row else None
    #     #     if tbl in tables_data:
    #     #         # Remove table_name extra column if exists
    #     #         clean_row = {k: v for k, v in row.items() if k != "table_name"}
    #     #         tables_data[tbl].append(clean_row)

    #      # Group by table_name → table data object with title + rows
    #     tables_data = {
    #     t: {
    #         "title": t,
    #         "columns": [],
    #         "rows": []
    #     }
    #     for t in table_names
    # }


    #     for row in all_table_rows:
    #         tbl = row.get("table_name")

    #         if tbl in tables_data:
    #             # remove internal table_name column
    #             clean_row = {k: v for k, v in row.items() if k != "table_name"}

    #             # append row
    #             tables_data[tbl]["rows"].append(clean_row)

    #             # if columns not set yet → set from first row
    #             if not tables_data[tbl]["columns"]:
    #                 tables_data[tbl]["columns"] = [
    #                     {"column_name": col} for col in clean_row.keys()
    #                 ]

    #     # ----------------------------------------
    #     # FINAL RESPONSE
    #     # ----------------------------------------
    #     return build_response(True, "Uploaded tables loaded", 200, {
    #         "dropdown_options": tables_dropdown,   # for dropdown UI
    #         "tables_data": tables_data            # grouped rows by table name
    #     })
    # since this SP returns ONLY ONE RESULTSET:
        titles = []
        for rs in cur.stored_results():
            titles = rs.fetchall()

        cur.close()
        db.close()

        # -----------------------------
        # FINAL RESPONSE
        # -----------------------------
        return build_response(True, "Query titles loaded", 200, {
            "titles": titles
        })


    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)
