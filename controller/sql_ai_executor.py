import os
import json
import requests
import re
import mysql.connector
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response


# =========================================================
# 1. 🔥 LLM CALL (Mistral Cloud)
# =========================================================
def call_mistral_llm(system_instruction, user_prompt):
    api_key = os.getenv("MISTRAL_API_KEY", "IotlgX9OC7gWRj0WqHuT5xdhT1LNkNne")

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
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("LLM ERROR:", e)
        return "DELIMITER ;; SELECT 'LLM ERROR' AS error ;; DELIMITER ;"


# =========================================================
# 2. 🔥 FIXED SQL EXECUTOR — FULLY WORKING
# =========================================================
def execute_generated_sql(sql_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    last_error = None

    try:
        # ------------------------------------------------------
        # 1. Extract ONLY SQL block (remove explanation text)
        # ------------------------------------------------------
        match = re.search(r"(DELIMITER|CREATE\s+PROCEDURE)", sql_code, re.IGNORECASE)
        if not match:
            return False, None, "No SQL block found in AI output"

        clean_sql = sql_code[match.start():]

        # ------------------------------------------------------
        # 2. Normalize delimiters
        # ------------------------------------------------------
        clean_sql = clean_sql.replace("$$", ";;").replace("//", ";;")
        clean_sql = re.sub(r"DELIMITER\s+;;", "", clean_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r"DELIMITER\s+;", "", clean_sql, flags=re.IGNORECASE)

        # Remove markdown artifacts
        clean_sql = re.sub(r"```sql|```", "", clean_sql, flags=re.IGNORECASE)
        clean_sql = clean_sql.strip()

        # ------------------------------------------------------
        # 3. Split SQL into statements
        # ------------------------------------------------------
        statements = [s.strip() for s in clean_sql.split(";;") if s.strip()]

        proc_name = None
        executed_count = 0

        for stmt in statements:

            # Skip non-SQL chat text
            if not re.match(r"^(CREATE|DROP|SELECT|WITH|BEGIN|END)", stmt, re.IGNORECASE):
                continue

            # Extract SP name
            m = re.search(r"CREATE\s+PROCEDURE\s+`?(\w+)`?", stmt, re.IGNORECASE)
            if m:
                proc_name = m.group(1)
                try:
                    cursor.execute(f"DROP PROCEDURE IF EXISTS `{proc_name}`")
                except:
                    pass

            # Skip stray END;
            if stmt.upper() == "END":
                continue

            # Execute SQL
            try:
                cursor.execute(stmt)
                executed_count += 1
            except Exception as e:
                last_error = e
                print("SQL EXEC ERROR:", e)

        conn.commit()
        cursor.close()

        if executed_count == 0:
            return False, None, f"No SQL executed. Error: {last_error}"

        if not proc_name:
            return False, None, "Procedure name missing"

        # ------------------------------------------------------
        # 4. Execute stored procedure safely
        # ------------------------------------------------------
        cursor2 = conn.cursor(dictionary=True)

        try:
            cursor2.callproc(proc_name)
        except Exception as e:
            return False, None, f"Procedure Execution Error: {e}"

        results = []

        try:
            for result in cursor2.stored_results():
                results.extend(result.fetchall())
        except:
            pass

        cursor2.close()
        return True, results, "Success"

    except Exception as e:
        return False, None, f"Server Error: {e}"

    finally:
        if conn.is_connected():
            conn.close()




# =========================================================
# 3. 🔥 CHAT ENDPOINT — With corrected schema + prompt
# =========================================================
def chat_endpoint():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        session_name = data.get("session_name")
        file_name = data.get("file_name")
        user_query = data.get("user_query")

        if not all([session_id, session_name, file_name, user_query]):
            return build_response(False, "Missing required fields", 400)

        # fetch schema
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT table_name, column_metadata
            FROM processed_cleaned_table_data
            WHERE session_id=%s AND file_name=%s
        """, (session_id, file_name))

        db_tables = cursor.fetchall()
        cursor.close()
        conn.close()

        if not db_tables:
            return build_response(False, "No schema found", 404)

        # Build schema context
        schema_info = []
        for t in db_tables:
            t_name = t["table_name"]
            raw_meta = t["column_metadata"]
            meta = json.loads(raw_meta)

            col_defs = []
            for c in meta:
                col = c["column_name"]
                ctype = c["column_type"]

                sql_type = "VARCHAR(255)"
                if "id" in col.lower():
                    sql_type = "VARCHAR(255)"
                elif ctype == "number":
                    sql_type = "DECIMAL(65,4)"
                elif ctype == "int":
                    sql_type = "DECIMAL(65,0)"
                elif ctype == "date":
                    sql_type = "DATE"

                col_defs.append(f"`{col}` {sql_type} PATH '$.\"{col}\"'")

            schema_info.append(f"Table: {t_name}\nColumns: {', '.join(col_defs)}")

        schema_context = "\n\n".join(schema_info)

        # SYSTEM PROMPT (Upgraded)
        system_instruction = f"""
You are a MySQL 8.0 expert.
Your job is to ALWAYS generate a stored procedure using ONLY JSON_TABLE + CTEs.

==========================
  NON-NEGOTIABLE RULES
==========================

1. ❌ NEVER USE PHYSICAL TABLES
   Forbidden:
     - Customers
     - Orders
     - Any real SQL table name
     - Any table not coming from JSON_TABLE

   You must ONLY read from:
     processed_cleaned_table_data.row_data (JSON)

2. ✅ YOU MUST ALWAYS USE JSON_TABLE
   - JSON source: main.row_data
   - Path: '$[*]'
   - Columns must match schema EXACTLY as provided.

3. ✅ CTE STRUCTURE IS MANDATORY
   Example pattern (you MUST follow the structure):

WITH CustomersCTE AS (
    SELECT jt.*
    FROM processed_cleaned_table_data main,
         JSON_TABLE(main.row_data, '$[*]' COLUMNS (
             Column1 VARCHAR(255) PATH '$."Column1"',
             Column2 VARCHAR(255) PATH '$."Column2"'
         )) AS jt
    WHERE 
        main.table_name = 'Customers'
        AND main.session_id = '{session_id}'
        AND main.file_name = '{file_name}'
),
OrdersCTE AS (
    SELECT jt.*
    FROM processed_cleaned_table_data main,
         JSON_TABLE(main.row_data, '$[*]' COLUMNS (
             ColumnA VARCHAR(255) PATH '$."ColumnA"',
             ColumnB VARCHAR(255) PATH '$."ColumnB"'
         )) AS jt
    WHERE
        main.table_name = 'Orders'
        AND main.session_id = '{session_id}'
        AND main.file_name = '{file_name}'
)

4. ❌ NEVER USE JSON_EXTRACT(c.*, ...)
   This is invalid. You MUST read JSON using JSON_TABLE only.

5. ✅ FINAL SELECT MUST ONLY USE CTEs:
   Example:

SELECT c.FirstName, o.OrderID
FROM CustomersCTE c
JOIN OrdersCTE o ON c.CustomerID = o.CustomerID;

6. ⚠️ OUTPUT FORMAT MUST BE EXACTLY:

DELIMITER ;;
CREATE PROCEDURE sp_dynamic_query()
BEGIN
    ... CTE definitions ...
    ... final SELECT ...
END;;
DELIMITER ;

7. ❌ NO extra text
   ❌ NO explanation
   ❌ NO comments
   You must output ONLY the SQL procedure between the delimiters.

8. Procedure name is ALWAYS:
   CREATE PROCEDURE sp_dynamic_query()

9. Follow schema EXACTLY.
   You must generate JSON_TABLE column definitions EXACTLY based on schema provided in the prompt.

==========================
END OF RULES
==========================

"""

        user_prompt = f"""
Schema:
{schema_context}

User Query:
{user_query}

Write the Stored Procedure now.
"""

        ai_sql = call_mistral_llm(system_instruction, user_prompt)
        ai_sql = re.sub(r"```sql|```", "", ai_sql).strip()

        return build_response(True, "Chat processed", 200, {
            "session_id": session_id,
            "user_query": user_query,
            "ai_response": ai_sql
        })

    except Exception as e:
        return build_response(False, f"Chat Error: {e}", 500)



# =========================================================
# 4. EXECUTE SQL
# =========================================================
def execute_sql_endpoint():
    try:
        sql_query = request.json.get("sql_query")
        if not sql_query:
            return build_response(False, "Missing sql_query", 400)

        success, results, msg = execute_generated_sql(sql_query)
        if success:
            return build_response(True, "Success", 200, results)
        return build_response(False, f"Execution Failed: {msg}", 400)

    except Exception as e:
        return build_response(False, f"Server Error: {e}", 500)
