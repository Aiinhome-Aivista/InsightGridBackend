import json
import re
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
from model.llm_client import call_llm
import time

def ask_llm_for_sp_name(user_query):
    prompt = f"""
    You must generate ONLY a short MySQL stored procedure name based on this query:

    "{user_query}"

    RULES:
    - Must be short (2-4 meaningful words)
    - Must use snake_case
    - MUST start with: sp_
    - MUST contain ONLY letters, numbers, and underscores
    - Do NOT return explanations
    - Do NOT return SQL
    - Return ONLY the procedure name
    """

    name = call_llm(prompt).strip()
    name = name.replace("`", "").replace(";", "")

    # safety filter
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)

    return name


def chat_endpoint_controller():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        created_by = data.get("created_by")
        user_query = data.get("user_query")

        if not all([session_id, created_by, user_query]):
            return build_response(False, "Missing required fields", 400)

        # ======================================================
        # STEP 1 — Fetch table names from uploaded_files
        # ======================================================
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT table_name 
            FROM uploaded_files  
            WHERE session_id=%s
              AND created_by=%s
              AND table_extraction_status='done'
              AND column_extraction_status='done'
        """, (session_id, created_by))

        table_rows = cursor.fetchall()

        if not table_rows:
            return build_response(False, "No tables found for this session", 404)

        table_names = [t["table_name"] for t in table_rows]

        # ======================================================
        # STEP 2 — Fetch FULL TABLE DATA + schema
        # ======================================================
        full_table_data = {}
        schema_context = {}

        for tname in table_names:
            cursor.execute(f"SELECT * FROM `{tname}`")
            rows = cursor.fetchall()

            full_table_data[tname] = rows
            schema_context[tname] = list(rows[0].keys()) if rows else []

        cursor.close()
        conn.close()

        # ======================================================
        # STEP 3 — Build schema JSON for LLM
        # ======================================================
        schema_json = json.dumps(schema_context, indent=2)
        sp_name = ask_llm_for_sp_name(user_query)
        system_instruction = f"""
You are a MySQL 8.0 expert.

STRICT OUTPUT RULES:
------------------------------------
1. Output MUST be ONLY this format:

DELIMITER ;;
CREATE PROCEDURE {sp_name}()
BEGIN
    <SQL QUERY HERE>
END;;
DELIMITER ;

2. NO extra text
3. NO comments
4. NO markdown
5. NO explanation
6. NEVER change procedure name
7. Use ONLY tables and columns listed below:

TABLES YOU CAN USE:
{schema_json}

COLUMN RULES:
- Map user keywords semantically to correct columns.
- Never invent new columns.
- Always prefix columns with table name.
- Follow ONLY_FULL_GROUP_BY rules.
IMPLICIT FILTER RULES:
- If user gives a column name followed by a value without specifying an operator 
  (e.g., 'name Ali', 'customer Ali', 'status pending'),
  automatically convert it into SQL using LIKE '%value%'.
- Do not output explanation or reasoning; only generate SQL inside the stored procedure.

------------------------------------
"""

        user_prompt = f"User Query: {user_query}\nGenerate MySQL stored procedure only."

        # ======================================================
        # STEP 4 — Merge prompts + Call LLM
        # ======================================================
        final_prompt = system_instruction + "\n" + user_prompt
        ai_sql = call_llm(final_prompt).strip()

        # ======================================================
        # STEP 5 — Response
        # ======================================================
        return build_response(True, "Chat processed", 200, {
            "session_id": session_id,
            "tables": table_names,
            "schema_context": schema_context,
            "ai_response": ai_sql
        })

    except Exception as e:
        return build_response(False, f"Chat Error: {e}", 500)


def format_execution_time(seconds):
    # If below 1 hour
    if seconds < 60:
        return f"{round(seconds, 3)} sec"
    
    # If 1 minute up to 1 hour
    if seconds < 3600:
        minutes = seconds / 60
        return f"{round(minutes, 2)} minutes"
    
    # If more than 1 hour
    hours = seconds / 3600
    return f"{round(hours, 2)} hours"

def extract_select_query(ai_response):
    # Remove delimiters
    clean = ai_response.replace("DELIMITER ;;", "").replace("DELIMITER ;", "")

    # Remove CREATE PROCEDURE and BEGIN / END block
    clean = re.sub(r"CREATE\s+PROCEDURE[\s\S]*?BEGIN", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"END\s*;?", "", clean, flags=re.IGNORECASE)

    # Extract only SELECT query
    match = re.search(r"(SELECT[\s\S]*?);", clean, flags=re.IGNORECASE)
    
    if match:
        return match.group(1).strip()  # return only the SELECT statement
    
    return None  # if not found


# def run_select_query(sql_query):
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         start_time = time.time()

#         query = sql_query.strip()
#         query = re.sub(r"```sql|```", "", query, flags=re.IGNORECASE).strip()

#         # BLOCK unsafe operations
#         forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "TRUNCATE"]
#         if any(query.upper().startswith(k) for k in forbidden_keywords):
#             return False, None, "Only SELECT statements are allowed."

#         if not query.upper().startswith("SELECT"):
#             return False, None, "Query must start with SELECT."

#         cursor.execute(query)
#         rows = cursor.fetchall()

#         end_time = time.time()
#         elapsed = end_time - start_time

#         result = {
#             "rows": rows,
#             "total_rows": len(rows),
#             "execution_time": format_execution_time(elapsed)
#         }

#         return True, result, "Success"

#     except Exception as e:
#         return False, None, f"SQL Execution Error: {e}"

#     finally:
#         cursor.close()
#         conn.close()


def run_select_query(select_query):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(select_query)
        rows = cursor.fetchall()

        # Extract column names even if no rows
        column_names = [desc[0] for desc in cursor.description]

        cursor.close()
        conn.close()

        return True, {
            "columns": column_names,
            "rows": rows
        }, "OK"

    except Exception as e:
        return False, None, str(e)


def execute_sql_endpoint_controller():
    try:
        ai_sql = request.json.get("sql_query")

        if not ai_sql:
            return build_response(False, "Missing sql_query", 400)

        # Extract SELECT query from stored procedure
        select_query = extract_select_query(ai_sql)

        if not select_query:
            return build_response(False, "Failed to extract SELECT query", 400)

        # Run actual extracted SELECT
        success, results, msg = run_select_query(select_query)

        if success:
            return build_response(True, "Success", 200, results)

        return build_response(False, msg, 400)

    except Exception as e:
        return build_response(False, f"Server Error: {e}", 500)
