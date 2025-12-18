# from flask import request
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response
# import json
# import pandas as pd
# import re
# from model.llm_client import call_llm


# # ---------------------------------------------------------
# # Chart Suggestion Generator
# # ---------------------------------------------------------
# def generate_chart_suggestions(table_rows):

#     if not table_rows:
#         return {"possible_charts": []}

#     df = pd.DataFrame(table_rows)
#     df_text = df.head(40).to_string(index=False)

#     prompt = f"""
# You are a senior data visualization expert.

# Dataset:
# {df_text}

# Return ONLY this JSON:

# {{
#   "possible_charts": ["bar","pie","bubble","mixed","box","waterfall","kpi"]
# }}
# """

#     try:
#         result = call_llm(prompt)
#         result = re.sub(r"```json|```", "", result).strip()
#         return json.loads(result)
#     except:
#         return {"possible_charts": ["bar"]}  # fallback



# # ---------------------------------------------------------
# # FINAL CONTROLLER — ONLY DATA + CHART SUGGESTIONS
# # ---------------------------------------------------------
# def get_saved_query_response_controller():
#     try:
#         body = request.get_json()
#         created_by = body.get("created_by")
#         session_id = body.get("session_id")

#         if not created_by or not session_id:
#             return build_response(False, "created_by & session_id required", 400)

#         db = get_db_connection()
#         cursor = db.cursor(dictionary=True)

#         # -----------------------------------------
#         # VALIDATE SESSION
#         # -----------------------------------------
#         cursor.execute(
#             """
#             SELECT user_id FROM users
#             WHERE user_id = %s AND session_id = %s
#             LIMIT 1
#             """,
#             (created_by, session_id)
#         )

#         if not cursor.fetchone():
#             cursor.close()
#             db.close()
#             return build_response(False, "Invalid session_id or created_by", 400)

#         # -----------------------------------------
#         # CALL YOUR STORED PROCEDURE
#         # -----------------------------------------
#         cursor.callproc(
#             "sp_get_query_details_by_user_session_id",
#             (created_by, session_id)
#         )

#         rows = []
#         for rs in cursor.stored_results():
#             rows = rs.fetchall()

#         cursor.close()
#         db.close()

#         if not rows:
#             return build_response(True, "No chat history", 200, {
#                 "created_by": created_by,
#                 "session_id": session_id,
#                 "queries": []
#             })

#         final_queries = []

#         # -----------------------------------------
#         # PROCESS EACH ROW
#         # -----------------------------------------
#         for r in rows:

#             # Attempt to parse row_data JSON
#             try:
#                 parsed_rows = json.loads(r["row_data"]) if r["row_data"] else []
#             except:
#                 parsed_rows = []

#             # Generate chart suggestions only based on row_data
#             chart_suggestions = generate_chart_suggestions(parsed_rows)

#             final_queries.append({
#                 "id": r["id"],
#                 "query_title": r["query_title"],
#                 "user_query": r["user_query"],
#                 "ai_response": r["ai_response"],
#                 "is_execute": r["is_execute"],
#                 "rows_effected": r["rows_effected"],
#                 "query_time": r["query_time"],
#                 "row_data": parsed_rows,
#                 "chart_suggestions": chart_suggestions,
#                 "created_at": r["created_at"],
#                 "created_date": r["created_date"],
#                 "actual_created_at": r["actual_created_at"]
#             })

#         return build_response(True, "Chat history loaded", 200, {
#             "created_by": created_by,
#             "session_id": session_id,
#             "queries": final_queries
#         })

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)



from flask import request
from database.dbConnection import get_db_connection
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
# FINAL CONTROLLER — v4 compatible
# ---------------------------------------------------------
# def get_saved_query_response_controller():
#     try:
#         body = request.get_json()
#         created_by = body.get("created_by")
#         session_id = body.get("session_id")

#         if not created_by or not session_id:
#             return build_response(False, "created_by & session_id required", 400)

#         db = get_db_connection()
#         cursor = db.cursor(dictionary=True)

#         cursor.callproc(
#             "sp_get_query_details_by_user_session_id_v2",
#             (created_by, session_id)
#         )

#         rows = []
#         for rs in cursor.stored_results():
#             rows = rs.fetchall()

#         cursor.close()
#         db.close()

#         if not rows:
#             return build_response(True, "No data found", 200, {})

#         # ---- OUTER FIELDS (once) ----
#         response = {
#             "query_title": rows[0]["query_title"],
#             "session_id": rows[0]["session_id"],
#             "created_by": rows[0]["created_by"],
#             "created_at": rows[0]["created_at"],
#             "created_date": rows[0]["created_date"],
#             "messages": []
#         }

#         # ---- INNER MESSAGES ARRAY ----
#         for r in rows:
#             response["messages"].append({
#                 "id": r["id"],
#                 "query": r["query"],
#                 "ai_response": r["ai_response"],
#                 "is_execute": r["is_execute"],
#                 "row_count": r["rows_effected"],
#                 "query_time": r["query_time"],
#                 "actual_created_at": r["actual_created_at"],
#                 "updated_by": r["updated_by"],
#                 "updated_at": r["updated_at"]
#             })

#         return build_response(True, "Chat history loaded", 200, {"queries": [response]})

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)

# FINAL CONTROLLER — v2 compatible
# def get_saved_query_response_controller():
#     try:
#         body = request.get_json()
#         created_by = body.get("created_by")
#         session_id = body.get("session_id")

#         if not created_by or not session_id:
#             return build_response(False, "created_by & session_id required", 400)

#         db = get_db_connection()
#         cursor = db.cursor(dictionary=True)

#         cursor.callproc(
#             "sp_get_query_details_by_user_session_id_v2",
#             (created_by, session_id)
#         )

#         rows = []
#         for rs in cursor.stored_results():
#             rows = rs.fetchall()

#         cursor.close()
#         db.close()

#         if not rows:
#             return build_response(True, "No data found", 200, {"queries": []})

#         # =========================
#         # GROUP BY PARENT QUERY
#         # =========================
#         query_map = {}

#         # for r in rows:
#         #     parent_id = r["parent_query_id"] or r["id"]

#         #     if parent_id not in query_map:
#         #         query_map[parent_id] = {
#         #             "id": parent_id,
#         #             "query_title": r["query_title"],
#         #             "session_id": r["session_id"],
#         #             "created_by": r["created_by"],
#         #             "created_at": r["created_at"],
#         #             "created_date": r["created_date"],
#         #             "messages": []
#         #         }

#         #     query_map[parent_id]["messages"].append({
#         #         "id": r["id"],
#         #         "mode": r["mode"],
#         #         "query": r["query"],
#         #         "ai_response": r["ai_response"],
#         #         "is_execute": r["is_execute"],
#         #         "row_count": r["rows_effected"],
#         #         "query_time": r["query_time"],
#         #         "actual_created_at": r["actual_created_at"],
#         #         "updated_by": r["updated_by"],
#         #         "updated_at": r["updated_at"]
#         #     })
#         for r in rows:
#             if r["mode"] == "NEW":
#                 parent_id = r["id"]
#             else:
#                 parent_id = r["parent_query_id"]

#             if parent_id not in query_map:
#                 query_map[parent_id] = {
#                     "id": parent_id,
#                     "query_title": r["query_title"],
#                     "session_id": r["session_id"],
#                     "created_by": r["created_by"],
#                     "created_at": r["created_at"],
#                     "created_date": r["created_date"],
#                     "messages": []
#                 }

#             query_map[parent_id]["messages"].append({
#                 "id": r["id"],
#                 "mode": r["mode"],
#                 "query": r["query"],
#                 "ai_response": r["ai_response"],
#                 "is_execute": r["is_execute"],
#                 "row_count": r["rows_effected"],
#                 "query_time": r["query_time"],
#                 "actual_created_at": r["actual_created_at"],
#                 "updated_by": r["updated_by"],
#                 "updated_at": r["updated_at"]
#             })

#         return build_response(
#             True,
#             "Chat history loaded",
#             200,
#             {"queries": list(query_map.values())}
#         )

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)


# def get_saved_query_response_controller():
#     try:
#         body = request.get_json()
#         created_by = body.get("created_by")
#         session_id = body.get("session_id")

#         if not created_by or not session_id:
#             return build_response(False, "created_by & session_id required", 400)

#         db = get_db_connection()
#         cursor = db.cursor(dictionary=True)

#         cursor.callproc(
#             "sp_get_query_details_by_user_session_id_v2",
#             (created_by, session_id)
#         )

#         rows = []
#         for rs in cursor.stored_results():
#             rows = rs.fetchall()

#         cursor.close()
#         db.close()

#         if not rows:
#             return build_response(True, "No data found", 200, {"queries": []})

#         # =========================
#         # GROUP BY QUERY TITLE
#         # =========================
#         query_map = {}

#         for r in rows:
#             title = r["query_title"]

#             if title not in query_map:
#                 query_map[title] = {
#                     "query_title": title,
#                     "session_id": r["session_id"],
#                     "created_by": r["created_by"],
#                     "created_at": r["created_at"],
#                     "created_date": r["created_date"],
#                     "messages": []
#                 }

#             query_map[title]["messages"].append({
#                 "id": r["id"],
#                 "mode": r["mode"],
#                 "query": r["query"],
#                 "ai_response": r["ai_response"],
#                 "is_execute": r["is_execute"],
#                 "row_count": r["rows_effected"],
#                 "query_time": r["query_time"],
#                 "parent_query_id": r["parent_query_id"],
#                 "version_no": r["version_no"],
#                 "is_latest": r["is_latest"],
#                 "actual_created_at": r["actual_created_at"],
#                 "updated_by": r["updated_by"],
#                 "updated_at": r["updated_at"]
#             })

#         return build_response(
#             True,
#             "Chat history loaded",
#             200,
#             {"queries": list(query_map.values())}
#         )

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)


def get_saved_query_response_controller():
    try:
        body = request.get_json()
        created_by = body.get("created_by")
        session_id = body.get("session_id")

        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.callproc(
            "sp_get_query_details_by_user_session_id_v2",
            (created_by, session_id)
        )

        rows = []
        for rs in cursor.stored_results():
            rows = rs.fetchall()

        cursor.close()
        db.close()

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
