import pandas as pd
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json
from model.llm_client import call_llm


# ---------- CLEAN LLM JSON ----------
def clean_llm_json(text):
    t = text.strip()

    # remove code fences
    t = t.replace("```json", "")
    t = t.replace("```", "")
    t = t.replace("`", "")

    # extract JSON { ... }
    if "{" in t and "}" in t:
        t = t[t.find("{"): t.rfind("}") + 1]

    return t.strip()


def chat_query_controller():
    try:
        data = request.get_json()

        session_id = data.get("session_id")
        session_name = data.get("session_name")
        file_name = data.get("file_name")
        table_name = data.get("table_name")
        user_query = data.get("query")

        if not session_id or not session_name or not file_name or not table_name or not user_query:
            return build_response(False, "Missing required fields", 400)

        # -----------------------------------
        # STEP-1: FETCH TABLE DATA USING SP
        # -----------------------------------
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc("sp_get_table_data_for_chat_query", [
            session_id,
            session_name,
            file_name,
            table_name
        ])

        sp_result = None
        for res in cursor.stored_results():
            sp_result = res.fetchone()

        cursor.close()
        conn.close()

        if not sp_result:
            return build_response(False, "Table not found", 404)

        row_data = sp_result.get("row_data")

        if isinstance(row_data, str):
            row_data = json.loads(row_data)

        rows = row_data.get("rows", [])
        if not rows:
            return build_response(False, "No rows found", 404)

        df = pd.DataFrame(rows)

        # -----------------------------------
        # STEP-2: AI → Generate Pandas Code
        # -----------------------------------
        llm_prompt = f"""
You are a senior data analyst.

User Query:
"{user_query}"

Available Columns:
{list(df.columns)}

Your task:
- Understand the query
- Generate ONLY valid Pandas code using dataframe: df
- STRICT JSON output:

{{
  "code": "df.groupby('Region')['Sales'].sum()"
}}

NO extra text, NO markdown.
"""

        ai_response = call_llm(llm_prompt)

        # clean LLM output
        cleaned = clean_llm_json(ai_response)

        try:
            pandas_code = json.loads(cleaned)["code"]
        except Exception as e:
            return build_response(False, f"Invalid LLM JSON: {cleaned}", 500)

        # -----------------------------------
        # STEP-3: Execute Code
        # -----------------------------------
        try:
            result_df = eval(pandas_code)
        except Exception as e:
            return build_response(False, f"Execution Error: {str(e)}", 500)

        # dataframe → JSON
        # if hasattr(result_df, "to_dict"):
        #     result_json = result_df.to_dict(orient="records")
        # else:
        #     result_json = result_df
        # ---- SAFE UNIVERSAL RESULT CONVERSION ----
        if isinstance(result_df, pd.DataFrame):
            result_json = result_df.to_dict(orient="records")

        elif isinstance(result_df, pd.Series):
            result_json = result_df.to_frame().to_dict(orient="records")

        else:
            result_json = [{"value": result_df}]

        # -----------------------------------
        # STEP-4: AI → Format Output (InsightGrid Style)
        # -----------------------------------
        format_prompt = f"""
Convert this dataset into a clean, readable InsightGrid Chat UI style summary.

Data:
{result_json}

User Query:
"{user_query}"

FORMAT EXACTLY LIKE:

Sure! Here's a categorized overview based on your data:

Region: North
Top Sales Rep: Bob
Most Sold Category: Clothing

Region: South
Top Sales Rep: David
Most Sold Category: Clothing

No JSON. No code. Only formatted plain text.
"""

        formatted_output = call_llm(format_prompt).strip()

        # -----------------------------------
        # STEP-5: Final Output
        # -----------------------------------
        return build_response(True, "Chat Query Executed", 200, data={
            # "pandas_code": pandas_code,
            # "raw_result": result_json,
            "formatted_output": formatted_output
        })

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)
