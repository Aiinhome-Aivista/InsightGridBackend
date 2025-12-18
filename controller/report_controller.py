
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response  

def save_report_controller():
    try:
        data = request.get_json()

        session_id = data.get("session_id")
        user_id = data.get("created_by")
        report_id = data.get("report_id")
        report_name = data.get("report_name")
        query_history_id = data.get("query_history_id")

        if not all([session_id, user_id, report_id, report_name, query_history_id]):
            return build_response(False, "Missing required fields", 400)

        conn = get_db_connection()
        # cur = conn.cursor()
        cur = conn.cursor(dictionary=True)
        # Validate session + user
        cur.execute("""
            SELECT 1 FROM users
            WHERE session_id=%s AND user_id=%s
        """, (session_id, user_id))
        if not cur.fetchone():
            return build_response(False, "Invalid session or user", 401)

        # Fetch row_affected
        # cur.execute("""
        #     SELECT rows_effected FROM query_history WHERE id=%s
        # """, (query_history_id,))
        cur.execute("""
            SELECT row_count FROM query_history_v2 WHERE id=%s
        """, (query_history_id,))
        row = cur.fetchone()
        if not row:
            return build_response(False, "Invalid query_history_id", 404)

        rows_effected = row["row_count"]


        # Call SP (save or update)
        args = [
            report_id,
            session_id,
            user_id,
            report_name,
            query_history_id,
            rows_effected,
            None   # OUT param
        ]

        result = cur.callproc("sp_save_or_update_report", args)
        # action = result[-1]   # INSERT / UPDATE / EXISTS
        cur.execute("SELECT @_sp_save_or_update_report_6 AS action")
        action = cur.fetchone()["action"]

        conn.commit()
        cur.close()
        conn.close()

        if action == "EXISTS":
            return build_response(True, "Report already exists", 200)

        if action == "UPDATE":
            return build_response(True, "Report updated successfully", 200)

        return build_response(True, "Report saved successfully", 200)

    except Exception as e:
        return build_response(False, "Server Error", 500, {"error": str(e)})

# def report_list_controller():
#     try:
#         data = request.get_json() or {}
#         session_id = data.get("session_id")
#         user_id = data.get("created_by")

#         if not session_id or not user_id:
#             return build_response(False, "session_id & user_id required", 400)

#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)

#         cur.execute("""
#             SELECT 1 FROM users
#             WHERE session_id=%s AND user_id=%s
#         """, (session_id, user_id))
#         if not cur.fetchone():
#             return build_response(False, "Invalid session or user", 401)
        
#         cur.callproc("sp_get_report_list", [session_id, user_id])

#         rows = []
#         for res in cur.stored_results():
#             rows = res.fetchall()

#         result = []
#         for r in rows:
#             result.append({
#                 "report_id": r["report_id"],
#                 "report_name": r["report_name"],
#                 "row_affected": r["row_affected"],
#                 "group_by": [],
#                 "created_at": r["created_at"],
#                 "actual_created_at": r["actual_created_at"],
#                 "actual_created_date": r["actual_created_date"],
#                 "query": {
#                     "query_id": r["query_id"],
#                     "query_name": r["query_title"],
#                     "ai_responce": r["ai_response"]
#                 }
#             })

#         cur.close()
#         conn.close()

#         return build_response(True, "Report list fetched successfully", 200, {
#             "Report list": result
#         })

#     except Exception as e:
#         return build_response(False, "Server Error", 500, {"error": str(e)})


# v2
def report_list_controller():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        user_id = data.get("created_by")

        if not session_id or not user_id:
            return build_response(False, "session_id & user_id required", 400)

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Validate session + user
        cur.execute("""
            SELECT 1 FROM users
            WHERE session_id=%s AND user_id=%s
        """, (session_id, user_id))
        if not cur.fetchone():
            return build_response(False, "Invalid session or user", 401)

        #  V2 SP call
        cur.callproc("sp_get_report_list_v2", [session_id, user_id])

        rows = []
        for res in cur.stored_results():
            rows = res.fetchall()

        result = []
        for r in rows:
            result.append({
                # ===== SAME AS OLD =====
                "report_id": r["report_id"],
                "report_name": r["report_name"],
                "row_affected": r["row_affected"],
                "group_by": [],
                "created_at": r["created_at"],
                "actual_created_at": r["actual_created_at"],
                "actual_created_date": r["actual_created_date"],

                # ADDITION (non-breaking)
                "query_history_id": r["query_history_id"],

                # ===== SAME AS OLD =====
                "query": {
                    "query_id": r["query_history_id"],   # 🔥 map here
                    "query_name": r["query_title"],
                    "ai_responce": r["ai_response"]
                }
            })

        cur.close()
        conn.close()

        #  SAME response wrapper as OLD
        return build_response(True, "Report list fetched successfully", 200, {
            "Report list": result
        })

    except Exception as e:
        return build_response(False, "Server Error", 500, {"error": str(e)})
