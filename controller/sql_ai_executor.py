import os
import json
import requests
import re
import mysql.connector
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response


# =========================================================
# 1. LLM CALL (Mistral Cloud)
# =========================================================
def call_mistral_llm(system_instruction, user_prompt):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "DELIMITER ;;\nSELECT 'Missing MISTRAL_API_KEY' AS error;;\nDELIMITER ;"

    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-tiny",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print("LLM API ERROR:", str(e))
        return "DELIMITER ;;\nSELECT 'LLM Error' AS error;;\nDELIMITER ;"



# =========================================================
# 2. SQL EXECUTOR (FULL — FIXED)
# =========================================================
def execute_generated_sql(sql_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    last_error = None

    try:
        # 1. Remove markdown and DELIMITER lines
        clean_sql = re.sub(r"```sql|```", "", sql_code, flags=re.IGNORECASE)
        clean_sql = re.sub(r"DELIMITER\s+;;", "", clean_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r"DELIMITER\s+;", "", clean_sql, flags=re.IGNORECASE)
        clean_sql = clean_sql.replace("$$", ";;").replace("//", ";;")

        # 2. Extract SQL starting from CREATE / WITH / SELECT
        start = re.search(r"(CREATE\s+PROCEDURE|WITH|SELECT)", clean_sql, flags=re.IGNORECASE)
        if start:
            clean_sql = clean_sql[start.start():]
        else:
            return False, None, "Unable to detect SQL start"

        # 3. Extract until END; only
        end_match = re.search(r"END\s*;", clean_sql, flags=re.IGNORECASE)
        if end_match:
            clean_sql = clean_sql[:end_match.end()]

        # 4. Split SQL statements
        statements = [s.strip() for s in clean_sql.split(";;") if s.strip()]

        proc_name = None
        executed_count = 0

        for stmt in statements:
            if stmt.upper() == "END":
                continue

            # Detect stored procedure name
            match = re.search(r"CREATE\s+PROCEDURE\s+`?(\w+)`?", stmt, re.IGNORECASE)
            if match:
                proc_name = match.group(1)
                cursor.execute(f"DROP PROCEDURE IF EXISTS `{proc_name}`")

            # Skip non-SQL text
            if not re.match(r"^(CREATE|WITH|SELECT|INSERT|UPDATE|DELETE|CALL)", stmt, re.IGNORECASE):
                continue

            cursor.execute(stmt)
            executed_count += 1

        conn.commit()
        cursor.close()

        if executed_count == 0:
            return False, None, "No valid SQL executed"

        if not proc_name:
            return False, None, "Procedure name not found"

        # 5. Execute stored procedure
        cursor2 = conn.cursor(dictionary=True)
        cursor2.callproc(proc_name)

        results = []
        for rs in cursor2.stored_results():
            results.extend(rs.fetchall())

        cursor2.close()
        return True, results, "Success"

    except Exception as e:
        return False, None, f"Server Error: {str(e)}"

    finally:
        if conn.is_connected():
            conn.close()


# =========================================================
# 3. GENERATE SQL FROM AI  (/chat_ai)
# =========================================================
def chat_endpoint():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        session_name = data.get("session_name")
        file_name = data.get("file_name")
        user_query = data.get("user_query")
        table_name = data.get("table_name", "General")

        if not all([session_id, session_name, file_name, user_query]):
            return build_response(False, "Missing required fields", 400)

        # -------- FETCH SCHEMA ----------
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT table_name, column_metadata FROM processed_cleaned_table_data WHERE session_id=%s AND file_name=%s",
            (session_id, file_name)
        )
        db_tables = cursor.fetchall()
        cursor.close()
        conn.close()

        if not db_tables:
            return build_response(False, "No schema found.", 404)

        # -------- Build Schema Context ----------
        schema_info = []

        for t in db_tables:
            t_name = t.get("table_name")
            raw = t.get("column_metadata")
            meta = json.loads(raw) if isinstance(raw, str) else (raw or [])

            col_defs = []
            for c in meta:
                name = c["column_name"]
                ctype = c["column_type"]

                sql_type = "VARCHAR(255)"
                if "id" in name.lower():
                    sql_type = "VARCHAR(255)"
                elif ctype == "number":
                    sql_type = "DECIMAL(65,4)"
                elif ctype == "int":
                    sql_type = "DECIMAL(65,0)"
                elif ctype == "date":
                    sql_type = "DATE"

                col_defs.append(f"`{name}` {sql_type} PATH '$.\"{name}\"'")

            schema_info.append(f"Table Name: '{t_name}'\nColumns: {', '.join(col_defs)}")

        schema_context_str = "\n\n".join(schema_info)

        # ----------------------------------------------
        # System & User Prompt for AI
        # ----------------------------------------------
        system_instruction = f"""
You are a MySQL 8.0 Expert.
Use JSON_TABLE with '$[*]' always.
Stored Procedure MUST take 0 parameters.
Hardcode session_id='{session_id}' and file_name='{file_name}'.
Generate ONLY SQL between:
DELIMITER ;;
... SQL ...
DELIMITER ;
"""

        user_prompt = f"""
Schema:
{schema_context_str}

User Query: "{user_query}"
Generate SQL now.
"""

        ai_sql = call_mistral_llm(system_instruction, user_prompt)
        ai_sql = re.sub(r"```sql|```", "", ai_sql).strip()

        # SAVE CHAT
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.callproc("sp_save_chat", [
            session_id, session_name, file_name, table_name,
            "User Query", user_query, ai_sql, "User"
        ])
        conn.commit()
        cursor.close()
        conn.close()

        return build_response(True, "Chat processed", 200, {
            "session_id": session_id,
            "user_query": user_query,
            "ai_response": ai_sql
        })

    except Exception as e:
        return build_response(False, f"Error: {str(e)}", 500)



# =========================================================
# 4. EXECUTE SQL API
# =========================================================
def execute_sql_endpoint():
    try:
        data = request.get_json() or {}
        sql_query = data.get("sql_query")

        if not sql_query:
            return build_response(False, "Missing sql_query", 400)

        success, results, msg = execute_generated_sql(sql_query)

        if success:
            return build_response(True, "Success", 200, results)
        else:
            return build_response(False, f"Execution Failed: {msg}", 400)

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)
