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
# 2. EXECUTE GENERATED SQL
# =========================================================
def execute_generated_sql(sql_code):

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        sql_code = sql_code.replace("$$", ";;").replace("//", ";;")
        sql_code = re.sub(r"```sql|```", "", sql_code, flags=re.IGNORECASE).strip()

        statements = sql_code.split(";;")

        proc_name = None
        executed_count = 0

        for stmt in statements:
            stmt = stmt.strip()
            stmt = re.sub(r"DELIMITER", "", stmt, flags=re.IGNORECASE).strip()

            if not re.match(r"^(CREATE|DROP|SELECT|WITH|INSERT|UPDATE|DELETE|SET)", stmt, re.IGNORECASE):
                continue

            match = re.search(r"CREATE\s+PROCEDURE\s+`?(\w+)`?", stmt, re.IGNORECASE)
            if match:
                proc_name = match.group(1)
                cursor.execute(f"DROP PROCEDURE IF EXISTS `{proc_name}`")

            if stmt.upper() != "END":
                try:
                    cursor.execute(stmt)
                    executed_count += 1
                except mysql.connector.Error as err:
                    print("SQL EXECUTION ERROR:", err)

        conn.commit()
        cursor.close()

        if executed_count == 0:
            return False, None, "No valid SQL statements found."

        # Execute procedure
        results = []
        if proc_name:
            cursor2 = conn.cursor(dictionary=True)
            try:
                cursor2.callproc(proc_name)
                for res in cursor2.stored_results():
                    results.extend(res.fetchall())
            except Exception as e:
                return False, None, f"Stored Procedure Execution Error: {e}"
            finally:
                cursor2.close()

        return True, results, "Executed Successfully"

    except Exception as e:
        return False, None, f"Server Error: {str(e)}"

    finally:
        conn.close()


# =========================================================
# 3. GENERATE SQL FROM AI  (/api/chat)
# =========================================================
def chat_ai_controller():

    try:
        data = request.get_json() or {}

        session_id = data.get("session_id")
        session_name = data.get("session_name")
        file_name = data.get("file_name")
        user_query = data.get("user_query")
        table_name = data.get("table_name", "General")

        if not all([session_id, session_name, file_name, user_query]):
            return build_response(False, "Missing required fields", 400)

        # Fetch schema
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

        # Build schema block
        schema_info = []
        for t in db_tables:
            tname = t["table_name"]
            metadata = json.loads(t["column_metadata"])

            col_defs = []
            for c in metadata:
                cname = c["column_name"]
                ctype = c["column_type"]

                sql_type = "VARCHAR(255)"
                if ctype == "number": sql_type = "DECIMAL(65,4)"
                if ctype == "int": sql_type = "DECIMAL(65,0)"
                if ctype == "date": sql_type = "DATE"

                col_defs.append(f"`{cname}` {sql_type} PATH '$.\"{cname}\"'")

            schema_info.append(f"Table Name: '{tname}'\nColumns: {', '.join(col_defs)}")

        schema_context = "\n\n".join(schema_info)

        # System Prompt
        system_instruction = """
        You are a MySQL 8.0 Expert.
       
        DATA ARCHITECTURE:
        - Table: `processed_cleaned_table_data`
        - Column: `row_data` (JSON). WRAPPED in "rows" key -> Use '$[*]'.
       
        YOUR TASK:
        Write a Stored Procedure to answer the query using `JSON_TABLE` and CTEs.
       
        CRITICAL RULES:
        1. **NO PARAMETERS**: The Stored Procedure must take 0 arguments. Example: `CREATE PROCEDURE my_sp()`
           - HARDCODE the `session_id` and `file_name` provided below directly into the WHERE clauses.
        2. **INCLUDE ALL COLUMNS**: In the `COLUMNS(...)` section, you MUST define **EVERY** column listed in the "Context (Schema)" provided.
        3. **REAL JOIN KEYS ONLY**: Do NOT invent columns like 'JoinID'. Use the actual common column (e.g., 'CustomerID', 'OrderID') from the Schema to perform the JOIN.
       
        STRICT PATTERN:
       
        WITH
        t1 AS (
            SELECT jt.* FROM processed_cleaned_table_data main,
            JSON_TABLE(main.row_data, '$[*]' COLUMNS (
                -- DEFINE ALL COLUMNS FROM SCHEMA HERE
                col1 VARCHAR(255) PATH '$."col1"',
                CustomerID DECIMAL(65,0) PATH '$."CustomerID"'
            )) AS jt
            WHERE main.table_name = 'Table1'
              AND main.session_id = 'HARDCODED_SESSION_ID'
              AND main.file_name = 'HARDCODED_FILE_NAME'
        ),
        t2 AS (
            SELECT jt.* FROM processed_cleaned_table_data main,
            JSON_TABLE(main.row_data, '$[*]' COLUMNS (
                -- DEFINE ALL COLUMNS FROM SCHEMA HERE
                colA VARCHAR(255) PATH '$."colA"',
                CustomerID DECIMAL(65,0) PATH '$."CustomerID"'
            )) AS jt
            WHERE main.table_name = 'Table2'
              AND main.session_id = 'HARDCODED_SESSION_ID'
              AND main.file_name = 'HARDCODED_FILE_NAME'
        )
        SELECT t1.col1, SUM(t2.colA)
        FROM t1
        JOIN t2 ON t1.CustomerID = t2.CustomerID  -- Use the REAL column name
        GROUP BY t1.col1;
       
        RULES:
        1. Output ONLY valid SQL.
        2. Start with 'DELIMITER ;;' and end with 'DELIMITER ;'.
        """




        user_prompt = f"""
        Current Session ID: {session_id}
        Current File Name: {file_name}
       
        Context (Schema):
        {schema_context}
       
        User Query: "{user_query}"
       
        Generate the Stored Procedure now.
        """


        ai_response = call_mistral_llm(system_instruction, user_prompt)
        ai_response = re.sub(r"```sql|```", "", ai_response, flags=re.IGNORECASE).strip()

        # Save chat
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.callproc("sp_save_chat", [
            session_id, session_name, file_name, table_name,
            "User Query", user_query, ai_response, "User"
        ])
        conn.commit()
        cursor.close()
        conn.close()

        return build_response(True, "Chat processed", 200, {
            "session_id": session_id,
            "user_query": user_query,
            "ai_response": ai_response
        })

    except Exception as e:
        return build_response(False, f"Error: {str(e)}", 500)


# =========================================================
# 4. EXECUTE SQL FROM AI (/api/execute-sql)
# =========================================================
def execute_sql_controller():

    try:
        data = request.get_json() or {}
        sql_query = data.get("sql_query")

        if not sql_query:
            return build_response(False, "Missing sql_query", 400)

        success, results, msg = execute_generated_sql(sql_query)

        if success:
            return build_response(True, "Success", 200, results)

        return build_response(False, f"Execution Failed: {msg}", 400)

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)
