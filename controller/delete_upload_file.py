# # from flask import request
# # from database.dbConnection import get_db_connection
# # from helper.helperFunctions import build_response

# # def delete_uploaded_file_controller():
# #     conn = None
# #     cursor = None

# #     try:
# #         data = request.get_json() or {}

# #         session_id = data.get("session_id")
# #         created_by = data.get("created_by")
# #         file_name = data.get("file_name")

# #         # Basic validation
# #         if not session_id or not created_by or not file_name:
# #             return build_response(False, "session_id, created_by & file_name required", 400)

# #         conn = get_db_connection()
# #         cursor = conn.cursor(dictionary=True)

# #         # 🔥 Stored Procedure Call
# #         cursor.callproc("sp_delete_uploaded_file", [
# #             session_id,
# #             created_by,
# #             file_name
# #         ])

# #         # Fetch SP Output
# #         sp_result = None
# #         for rs in cursor.stored_results():
# #             sp_result = rs.fetchone()
# #             break

# #         conn.commit()

# #         if not sp_result:
# #             return build_response(False, "Unexpected: No response from stored procedure", 500)

# #         status_msg = sp_result.get("status", "No status returned")

# #         # FINAL RESPONSE → only message, no data
# #         return build_response(True, status_msg, 200)

# #     except Exception as e:
# #         return build_response(False, f"Delete Error: {str(e)}", 500)

# #     finally:
# #         if cursor:
# #             cursor.close()
# #         if conn:
# #             conn.close()

# from flask import request
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response


# def delete_uploaded_file_controller():
#     conn = None
#     cursor = None

#     try:
#         data = request.get_json() or {}

#         session_id = data.get("session_id")
#         created_by = data.get("created_by")
#         file_name = data.get("file_name")

#         if not session_id or not created_by or not file_name:
#             return build_response(False, "session_id, created_by & file_name required", 400)

#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         # CALL STORED PROCEDURE
#         cursor.callproc(
#             "sp_delete_uploaded_file",
#             [session_id, created_by, file_name]
#         )

#         results = list(cursor.stored_results())

#         if not results:
#             return build_response(False, "No response from delete procedure", 500)

#         # -------------------------------
#         # RESULT SET 1 → STATUS MESSAGE
#         # -------------------------------
#         status_row = results[0].fetchone()
#         status_msg = status_row.get("status") if status_row else "Unknown status"

#         # -------------------------------
#         # RESULT SET 2 → DEPENDENCIES (optional)
#         # -------------------------------
#         dependency_list = []
#         if len(results) > 1:
#             dependency_list = results[1].fetchall()

#         conn.commit()

#         # --------------------------------
#         # FINAL RESPONSE (dynamic)
#         # --------------------------------
#         if dependency_list:
#             return build_response(
#                 False,
#                 status_msg,
#                 409,
#                 data={
#                     "dependencies": dependency_list
#                 }
#             )

#         return build_response(True, status_msg, 200)

#     except Exception as e:
#         return build_response(False, f"Delete Error: {str(e)}", 500)

#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()




# v2

from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response


def delete_uploaded_file_controller():
    conn = None
    cursor = None

    try:
        data = request.get_json() or {}

        session_id = data.get("session_id")
        created_by = data.get("created_by")
        file_name = data.get("file_name")

        # -------------------------------
        # REQUIRED VALIDATION → 400 ONLY
        # -------------------------------
        if not session_id or not created_by or not file_name:
            return build_response(
                False,
                "session_id, created_by & file_name required",
                400
            )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # -------------------------------
        # CALL STORED PROCEDURE (v2)
        # -------------------------------
        cursor.callproc(
            "sp_delete_uploaded_file_v2",
            [session_id, created_by, file_name]
        )

        results = list(cursor.stored_results())

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

        conn.commit()

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
        if conn:
            conn.close()

