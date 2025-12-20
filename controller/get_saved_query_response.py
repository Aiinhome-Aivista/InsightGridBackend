from flask import request,g
from helper.helperFunctions import build_response
import json
import pandas as pd
import re
from model.llm_client import call_llm


# ---------------------------------------------------------
# Chart Suggestion Generator (UNCHANGED)
# ---------------------------------------------------------
def generate_chart_suggestions(table_rows):

    if not table_rows:
        return {"possible_charts": []}

    df = pd.DataFrame(table_rows)
    df_text = df.head(40).to_string(index=False)

    prompt = f"""
You are a senior data visualization expert.

Dataset:
{df_text}

Return ONLY this JSON:

{{
  "possible_charts": ["bar","pie","bubble","mixed","box","waterfall","kpi"]
}}
"""

    try:
        result = call_llm(prompt)
        result = re.sub(r"```json|```", "", result).strip()
        return json.loads(result)
    except:
        return {"possible_charts": ["bar"]}

# ---------------------------------------------------------

def get_saved_query_response_controller():
    try:
        body = request.get_json()
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)
        # -----------------------------
        # COMPANY DB MUST ALREADY EXIST
        # (set by attach_company_db)
        # -----------------------------
        if not hasattr(g, "company_db"):
            return build_response(False, "Invalid session", 401)

        
        db = g.company_db
        cursor = db.cursor(dictionary=True)

        cursor.callproc(
            "sp_get_query_details_by_user_session_id",
            (created_by, session_id)
        )

        rows = []
        for rs in cursor.stored_results():
            rows = rs.fetchall()

        cursor.close()
    
        if not rows:
            return build_response(True, "No data found", 200, {"queries": []})

        # =========================
        # GROUP BY QUERY TITLE
        # =========================
        query_map = {}

        for r in rows:
            title = r["query_title"]

            if title not in query_map:
                query_map[title] = {
                    "query_title": title,
                    "session_id": r["session_id"],
                    "created_by": r["created_by"],
                    "created_at": r["created_at"],
                    "created_date": r["created_date"],
                    "latest_time": r["actual_created_at"],  # 👈 IMPORTANT
                    "messages": []
                }

            # update latest time
           # update latest time + display time
            if r["actual_created_at"] > query_map[title]["latest_time"]:
                query_map[title]["latest_time"] = r["actual_created_at"]
                query_map[title]["created_at"] = r["created_at"]
                query_map[title]["created_date"] = r["created_date"]


            query_map[title]["messages"].append({
                "id": r["id"],
                "mode": r["mode"],
                "query": r["query"],
                "ai_response": r["ai_response"],
                "is_execute": r["is_execute"],
                "row_count": r["rows_effected"],
                "query_time": r["query_time"],
                "parent_query_id": r["parent_query_id"],
                "version_no": r["version_no"],
                "is_latest": r["is_latest"],
                "actual_created_at": r["actual_created_at"],
                "updated_by": r["updated_by"],
                "updated_at": r["updated_at"]
            })

        # =========================
        # SORT GROUPS BY LATEST TIME DESC
        # =========================
        sorted_queries = sorted(
            query_map.values(),
            key=lambda x: x["latest_time"],
            reverse=True
        )

        # optional: remove internal field
        for q in sorted_queries:
            q.pop("latest_time", None)

        return build_response(
            True,
            "Chat history loaded",
            200,
            {"queries": sorted_queries}
        )

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)
