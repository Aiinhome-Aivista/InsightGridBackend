from flask import request,g
from helper.helperFunctions import build_response


def delete_uploaded_file_controller():
    conn = None
    cursor = None

    try:
        if not hasattr(g, "user_id") or not hasattr(g, "company_db"):
            return build_response(False, "Unauthorized", 401)
        
        data = request.get_json() or {}

        # session_id = data.get("session_id")
        # created_by = data.get("created_by")
        file_name = data.get("file_name")

        # -------------------------------
        # REQUIRED VALIDATION → 400 ONLY
        # -------------------------------
        # if not session_id or not created_by or not file_name:
        #     return build_response(
        #         False,
        #         "session_id, created_by & file_name required",
        #         400
        #     )
        if not file_name:
            return build_response(False, "file_name required", 400)
        created_by = g.user_id
        # session_id = None
        conn = g.company_db
        cursor = conn.cursor(dictionary=True)

        # -------------------------------
        # CALL STORED PROCEDURE (v2)
        # -------------------------------
        cursor.callproc(
            "sp_delete_uploaded_file",
            [created_by, file_name]
        )

        results = list(cursor.stored_results())
        conn.commit()
        if not results:
            return build_response(
                False,
                "No response from delete procedure",
                200
            )

        # -------------------------------
        # RESULT SET 1 → STATUS MESSAGE
        # -------------------------------
        status_row = results[0].fetchone()
        status_msg = status_row.get("status", "Unknown status")

        # -------------------------------
        # RESULT SET 2 → DEPENDENCIES (optional)
        # -------------------------------
        dependency_list = []
        if len(results) > 1:
            dependency_list = results[1].fetchall()


        # -------------------------------
        # FINAL RESPONSE → ALWAYS 200
        # -------------------------------
        if dependency_list:
            return build_response(
                False,
                status_msg,
                200,
                data={"dependencies": dependency_list}
            )

        if "deleted successfully" in status_msg.lower():
            return build_response(
                True,
                status_msg,
                200
            )

        # Other blocked cases (table missing, invalid session, etc.)
        return build_response(
            False,
            status_msg,
            200
        )

    except Exception as e:
        # Exception also returns 200 as per requirement
        return build_response(
            False,
            f"Delete Error: {str(e)}",
            200
        )

    finally:
        if cursor:
            cursor.close()
        
# def delete_uploaded_file_controller():
#     try:
#         if not hasattr(g, "user_id") or not hasattr(g, "company_db"):
#             return build_response(False, "Unauthorized", 401)

#         data = request.get_json() or {}
#         file_name = data.get("file_name")

#         if not file_name:
#             return build_response(False, "file_name required", 400)

#         created_by = g.user_id          # ✔ matches uploaded_files.created_by
#         session_id = None      # ✔ REAL session_id (UUID)

#         conn = g.company_db
#         cursor = conn.cursor(dictionary=True)

#         cursor.callproc(
#             "sp_delete_uploaded_file",
#             [session_id, created_by, file_name]
#         )

#         results = list(cursor.stored_results())
#         conn.commit()

#         status_row = results[0].fetchone()
#         status_msg = status_row.get("status", "Unknown status")

#         if len(results) > 1:
#             deps = results[1].fetchall()
#             if deps:
#                 return build_response(False, status_msg, 200, {
#                     "dependencies": deps
#                 })

#         if "deleted successfully" in status_msg.lower():
#             return build_response(True, status_msg, 200)

#         return build_response(False, status_msg, 200)

#     except Exception as e:
#         return build_response(False, f"Delete Error: {str(e)}", 200)

#     finally:
#         if cursor:
#             cursor.close()
