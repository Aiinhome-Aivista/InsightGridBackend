# from flask import request,g
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response


# def get_file_status_controller():
#     try:
#         body = request.get_json()

#         created_by = body.get("created_by")
#         session_id = body.get("session_id")

#         # VALIDATION
#         if not created_by:
#             return build_response(False, "created_by is required", 400, status="failed")

#         if not session_id:
#             return build_response(False, "session_id is required", 400, status="failed")
        
#          # -----------------------------
#         # COMPANY DB MUST ALREADY EXIST
#         # (set by attach_company_db)
#         # -----------------------------
#         if not hasattr(g, "company_db"):
#             return build_response(False, "Invalid session", 401)



#         con = g.company_db
#         cursor = con.cursor(dictionary=True)
#         #  VALIDATE SESSION ID & created_by
#         # -----------------------------------
#         cursor.execute(
#             "SELECT user_id, session_id FROM users WHERE session_id = %s AND user_id = %s LIMIT 1",
#             (session_id, created_by)
#         )
#         session_row = cursor.fetchone()

#         if not session_row:
#             cursor.close()
            
#             return build_response(
#                 False,
#                 "Invalid session_id or created_by",
#                 400
#                 # {"status": "failed"}
#             )

#         # CALL SP
#         cursor.callproc("sp_get_uploaded_files_status", [created_by, session_id])

#         stored = list(cursor.stored_results())
#         result = stored[0].fetchall() if stored else []

#         cursor.close()
       

#         # NO DATA FOUND
#         if not result:
#             return build_response(
#                 True,
#                 "No data found",
#                 200,
#                 data=[],
#                 status="success"
#             )
#         # SUCCESS RESPONSE
#         return build_response(
#             True,
#             "Status fetched successfully",
#             200,
#             data=result,
#             status="success"
#         )

#     except Exception as e:
#         return build_response(
#             False,
#             "Server Error",
#             500,
#             data={"error": str(e)},
#             status="error"
#         )

from flask import g
from helper.helperFunctions import build_response

def get_file_status_controller():
    try:
        # 🔐 AUTH CONTEXT FROM JWT
        if not hasattr(g, "company_db") or not hasattr(g, "user_id"):
            return build_response(False, "Unauthorized", 401)

        created_by = g.user_id
        db = g.company_db
        cursor = db.cursor(dictionary=True)

        # 📦 CALL STORED PROCEDURE
        cursor.callproc(
            "sp_get_uploaded_files_status",
            (created_by,)
        )

        stored = list(cursor.stored_results())
        result = stored[0].fetchall() if stored else []
        cursor.close()

        if not result:
            return build_response(
                True,
                "No data found",
                200,
                data=[]
            )

        return build_response(
            True,
            "Status fetched successfully",
            200,
            data=result
        )

    except Exception as e:
        return build_response(
            False,
            "Server Error",
            500,
            {"error": str(e)}
        )
