from flask import request, g
from helper.helperFunctions import build_response
import time
import re
from controller.sql_ai_executor import extract_select_query,extract_main_table_from_query
AGG_FUNCS = {"count", "sum", "avg", "min", "max"}

def execute_aggregation_controller():
    try:
        data = request.get_json() or {}

        session_id = data.get("session_id")
        column = data.get("column")
        agg = data.get("agg")
        base_sql = data.get("base_sql")   # ✅ NEW

        if not all([session_id, column, agg, base_sql]):
            return build_response(False, "Missing fields", 400)

        agg = agg.lower()
        if agg not in {"count", "sum", "avg", "min", "max"}:
            return build_response(False, "Invalid aggregation", 400)

        # 🔥 extract SELECT from SP SQL
        select_query = extract_select_query(base_sql)
        if not select_query:
            return build_response(False, "Invalid base SQL", 400)

        # 🔥 extract table from SELECT
        table = extract_main_table_from_query(select_query)
        if not table:
            return build_response(False, "Table not found in query", 400)

        conn = g.company_db
        cursor = conn.cursor(dictionary=True)

        sql = f"SELECT {agg.upper()}({column}) AS value FROM `{table}`"
        cursor.execute(sql)

        row = cursor.fetchone()
        value = row["value"] if row else 0

        cursor.close()

        return build_response(True, "Aggregation success", 200, {
            "column": column,
            "agg": agg,
            "value": value
        })

    except Exception as e:
        return build_response(False, str(e), 500)
