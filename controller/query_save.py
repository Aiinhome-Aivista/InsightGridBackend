# from flask import request
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response
# import json


# import re

# def extract_table_names_from_ai_response(ai_response: str):
#     if not ai_response:
#         return []

#     pattern = re.compile(
#         r"""
#         \bfrom\s+`?([a-zA-Z0-9_]+)`? |
#         \bjoin\s+`?([a-zA-Z0-9_]+)`? |
#         \bupdate\s+`?([a-zA-Z0-9_]+)`? |
#         \binto\s+`?([a-zA-Z0-9_]+)`?
#         """,
#         re.IGNORECASE | re.VERBOSE
#     )

#     matches = pattern.findall(ai_response)

#     tables = set()
#     for m in matches:
#         for t in m:
#             if t:
#                 tables.add(t.lower())

#     return list(tables)



# def query_save_controller():
#     try:
#         data = request.get_json()

#         query_title = data.get("query_title")
#         user_query = data.get("user_query")
#         ai_response = data.get("ai_response")
#         rows_effected = data.get("rows_effected")
#         query_time = data.get("query_time")
#         is_execute = data.get("is_execute")
#         row_data = data.get("row_data")
#         session_id = data.get("session_id")
#         created_by = data.get("created_by")

#         if not all([query_title, user_query, ai_response, session_id, created_by]):
#             return build_response(False, "Missing required fields", 400)
        
#         table_names = extract_table_names_from_ai_response(ai_response)
#         table_names_json = json.dumps(table_names) if table_names else None

#         row_data_json = json.dumps(row_data) if row_data else None
#         select_sql = extract_select_query(ai_response)

#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         # Validate session + user
#         cursor.execute(
#             "SELECT user_id, session_id FROM users WHERE session_id = %s AND user_id = %s LIMIT 1",
#             (session_id, created_by)
#         )
#         if not cursor.fetchone():
#             return build_response(False, "Invalid session_id or created_by", 400)

#         # Call stored procedure
#         cursor.callproc("sp_save_query", [
#             query_title,
#             table_names_json,  
#             user_query,
#             ai_response,
#             rows_effected,
#             query_time,
#             is_execute,
#             row_data_json,
#             session_id,
#             created_by,
#             select_sql   
#         ])

#         result = list(cursor.stored_results())[0].fetchone()

#         conn.commit()
#         cursor.close()
#         conn.close()

#         return build_response(True, "Chat saved", 200, result)

#     except Exception as e:
#         return build_response(False, f"Save Error: {str(e)}", 500)



# def extract_select_query(ai_response: str):
#     if not ai_response:
#         return None

#     clean = ai_response

#     # Remove DELIMITER
#     clean = clean.replace("DELIMITER ;;", "").replace("DELIMITER ;", "")

#     # Remove CREATE PROCEDURE block
#     clean = re.sub(
#         r"CREATE\s+PROCEDURE[\s\S]*?BEGIN",
#         "",
#         clean,
#         flags=re.IGNORECASE
#     )

#     # Remove END;
#     clean = re.sub(r"\bEND\b\s*;?", "", clean, flags=re.IGNORECASE)

#     # Extract SELECT
#     match = re.search(
#         r"(SELECT[\s\S]*?)(;|$)",
#         clean,
#         flags=re.IGNORECASE
#     )

#     if match:
#         return match.group(1).strip()

#     return None



from flask import request
import json, re
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response


def extract_select_sql(ai_response):
    if not ai_response:
        return None
    clean = ai_response.replace("DELIMITER ;;", "").replace("DELIMITER ;", "")
    clean = re.sub(r"CREATE\s+PROCEDURE[\s\S]*?BEGIN", "", clean, flags=re.I)
    clean = re.sub(r"\bEND\b\s*;?", "", clean, flags=re.I)
    m = re.search(r"(SELECT[\s\S]*?);", clean, flags=re.I)
    return m.group(1).strip() if m else None


def extract_tables(sql):
    if not sql:
        return []
    found = re.findall(r"\bFROM\s+(\w+)|\bJOIN\s+(\w+)", sql, re.I)
    tables = set()
    for f in found:
        for t in f:
            if t:
                tables.add(t.lower())
    return list(tables)


def query_save_controller():
    try:
        data = request.get_json()

        session_id = data.get("session_id")
        created_by = data.get("created_by")
        query_title = data.get("query_title")
        messages = data.get("messages", [])

        if not all([session_id, created_by, query_title, messages]):
            return build_response(False, "Missing required fields", 400)

        conn = get_db_connection()
        cursor = conn.cursor()

        prev_db_id = None
        prev_query_text = None
        response_rows = []

        for idx, msg in enumerate(messages):

            user_query = msg.get("query")
            ai_response = msg.get("ai_response")

            executable_sql = extract_select_sql(ai_response)
            table_names = extract_tables(executable_sql)

            # ---- decide mode ----
            if idx == 0:
                mode = "NEW"
                parent_id = None
            else:
                if user_query == prev_query_text:
                    mode = "EDIT"
                    parent_id = prev_db_id
                else:
                    mode = "CONTEXT"
                    parent_id = prev_db_id

            cursor.callproc("sp_save_query_v2", [
                session_id,
                created_by,
                query_title,

                msg.get("query_id"),
                user_query,
                ai_response,
                executable_sql,
                json.dumps(table_names),

                msg.get("is_execute", 0),
                msg.get("is_success", 0),
                msg.get("row_count", 0),
                msg.get("query_time"),

                mode,
                parent_id
            ])

            result = list(cursor.stored_results())[0].fetchone()
            prev_db_id = result[0]
            prev_query_text = user_query

            response_rows.append({
                "db_id": prev_db_id,
                "mode": mode
            })

        conn.commit()
        cursor.close()
        conn.close()

        return build_response(True, "Messages saved successfully", 200, response_rows)

    except Exception as e:
        return build_response(False, f"Save Error: {e}", 500)
