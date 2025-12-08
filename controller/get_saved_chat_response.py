from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import pandas as pd
import json
import re
from model.llm_client import call_llm
import os
import requests

def call_mistral_llm(system_instruction: str, user_prompt: str) -> str:
    api_key = os.getenv("MISTRAL_API_KEY", "")

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
        r = requests.post(url, json=payload, headers=headers, timeout=40)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("LLM ERROR:", e)
        return "[LLM ERROR] Unable to generate response."

# def get_chat_history_controller():
#     try:
#         data = request.get_json()

#         session_id = data.get("session_id")
#         session_name = data.get("session_name")
#         file_name = data.get("file_name")

#         if not session_id or not session_name or not file_name:
#             return build_response(False, "Missing required fields", 400)

#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         cursor.callproc("sp_get_chat_history", [
#             session_id,
#             session_name,
#             file_name
#         ])

#         result = []
#         for rs in cursor.stored_results():
#             result = rs.fetchall()

#         cursor.close()
#         conn.close()

#         return build_response(True, "Chat history loaded", 200, data=result)

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)

# ---------------------------------------------------------
# LLM — Chart Suggestion (based on table rows)
# ---------------------------------------------------------
def generate_chart_suggestions(table_rows):

    df = pd.DataFrame(table_rows)
    df_text = df.head(40).to_string(index=False)

    prompt = f"""
You are a senior data visualization expert.

Your task is to decide which chart types are POSSIBLE for visualizing the dataset.

Dataset:
{df_text}

Return ONLY valid JSON:

{{
  "possible_charts": [
      "bar",
      "pie",
      "bubble",
      "mixed",
      "box",
      "waterfall",
      "kpi"
  ]
}}

Rules:
- Use ONLY these chart IDs.
- Select only those which logically apply.
- No explanation text.
"""

    try:
        llm_output = call_llm(prompt)
        llm_output = re.sub(r"```json|```", "", llm_output).strip()
        return json.loads(llm_output)

    except:
        return {"possible_charts": ["bar"]}  # fallback
    
# def generate_insights_only(tables):
#     tables_text = ""
#     for table in tables:
#         tables_text += f"Table: {table['table_name']}\n"
#         df = pd.DataFrame(table["clean_data"])
#         if not df.empty:
#             tables_text += df.head(50).to_string(index=False)
#         tables_text += "\n\n"

#     system_instruction = "You are an expert data analyst. Your job is to generate insights only."

#     user_prompt = f"""
# Analyze the following tables and generate ONLY insights.

# Return ONLY valid JSON in EXACTLY this format:

# {{
#   "table_insights": {{
#       "TableName": {{
#           "insights": [
#               "insight 1",
#               "insight 2",
#               "insight 3"
#           ]
#       }}
#   }}
# }}

# STRICT RULES:
# - Use the REAL table names.
# - Minimum 3 insights per table.
# - NO relationships.
# - NO explanations.
# - NO text outside JSON.

# Here is the data:
# {tables_text}
# """

#     try:
#         llm_output = call_mistral_llm(system_instruction, user_prompt)
#         llm_output = re.sub(r"```json|```", "", llm_output).strip()
#         return json.loads(llm_output)
#     except Exception as e:
#         print("INSIGHTS PARSE ERROR:", e)
#         return {"table_insights": {}}
    
def generate_insights_only(tables):
    tables_text = ""
    for table in tables:
        tables_text += f"Table: {table['table_name']}\n"
        df = pd.DataFrame(table["clean_data"])
        if not df.empty:
            tables_text += df.to_string(index=False)
        tables_text += "\n\n"

    system_instruction = "You are a senior data analyst. Generate insights strictly based on the data."

    user_prompt = f"""
Analyze the following tables and generate insights based ONLY on their content.

Return ONLY valid JSON in EXACTLY this format:

{{
  "table_insights": [
      {{
          "table_name": "name",
          "insights": ["insight 1", "insight 2"]
      }}
  ]
}}

RULES:
- MUST return an entry for EVERY table.
- NEVER skip any table.
- If table has few rows, generate simple factual insights.
- If table has many rows, generate 2–3 insights.
- Insights MUST be strictly based on provided data.
- NO explanations.
- NO extra text outside JSON.

Here is the data:
{tables_text}
"""

    try:
        # llm_output = call_mistral_llm(system_instruction, user_prompt)
        llm_output = call_llm(system_instruction + "\n\n" + user_prompt)

        llm_output = re.sub(r"```json|```", "", llm_output).strip()
        result = json.loads(llm_output)

        # flat = {}
        # for table, value in result.get("table_insights", {}).items():
        #     flat[table] = value.get("insights", [])
        flat = {}
        for item in result.get("table_insights", []):
            name = item.get("table_name")
            insights = item.get("insights", [])
            flat[name] = insights
        return flat

    except Exception as e:
        print("INSIGHTS PARSE ERROR:", e)
        return {}
  
    
    
# ---------------------------------------------------------
# MAIN CONTROLLER — Chat History + Insights + Chart Suggestions
# ---------------------------------------------------------
# def get_chat_history_by_user_controller():
#     try:
#         data = request.get_json()
#         created_by = data.get("created_by")

#         if not created_by:
#             return build_response(False, "created_by is required", 400)

#         # Fetch chat history
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.callproc("sp_get_chat_history_by_user", [created_by])

#         rows = []
#         for rs in cursor.stored_results():
#             rows = rs.fetchall()

#         cursor.close()
#         conn.close()

#         if not rows:
#             return build_response(True, "No chat history", 200, data={
#                 "created_by": created_by,
#                 "chat_titles": [],
#                 "conversations": [],
#                 "insights": {}
#             })

#         chat_titles = []
#         conversations = []
#         insight_tables = []

#         # Process each row
#         for r in rows:
#             try:
#                 table_data = json.loads(r.get("table_data")) if r.get("table_data") else {}
#             except:
#                 table_data = {}

#             # --- ADD INDIVIDUAL CHART SUGGESTION FOR THIS TABLE ---
#             chart_suggestions = {}
#             if "rows" in table_data and len(table_data["rows"]) > 0:
#                 chart_suggestions = generate_chart_suggestions(table_data["rows"])

#                 # attach inside table_data
#                 table_data["chart_suggestions"] = chart_suggestions

#             # collect titles
#             if r["chat_title"] not in chat_titles:
#                 chat_titles.append(r["chat_title"])

#             conversations.append({
#                 "chat_title": r["chat_title"],
#                 "user_query": r["user_query"],
#                 "ai_response": r["ai_response"],
#                 "table_data": table_data,
#                 "created_at": r["created_at"]
#             })

#             # prepare for insights (same as before)
#             if "rows" in table_data and len(table_data["rows"]) > 0:
#                 insight_tables.append({
#                     "table_name": r["chat_title"],
#                     "clean_data": table_data["rows"]
#                 })

#         # Generate Insights
#         insights = generate_insights_only(insight_tables) if insight_tables else {}

#         # Final Combined Response
#         return build_response(True, "Chat history loaded", 200, data={
#             "created_by": created_by,
#             "chat_titles": chat_titles,
#             "conversations": conversations,
#             "insights": insights
#         })

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)

# 2nddd

def get_chat_history_by_user_controller():
    try:
        data = request.get_json()
        created_by = data.get("created_by")

        if not created_by:
            return build_response(False, "created_by is required", 400)

        # -----------------------------------
        # Fetch chat history
        # -----------------------------------
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("sp_get_chat_history_by_user", [created_by])

        rows = []
        for rs in cursor.stored_results():
            rows = rs.fetchall()
        print('rows-->' , rows)
        cursor.close()
        conn.close()

        if not rows:
            return build_response(True, "No chat history", 200, data={
                "tables": {},
                "dropdown_options": []
            })

        tables = {}
        insight_input = []

        # -----------------------------------
        # Process each chat result
        # -----------------------------------
        for r in rows:
            title = r["chat_title"]  # REAL table title (required for insights)
            
            # key for frontend
            # table_key = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower())
            table_key = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')


            # Parse table JSON
            try:
                table_data = json.loads(r["table_data"]) if r["table_data"] else {}
            except:
                table_data = {}

            rows_data = table_data.get("rows", [])
            columns_data = [col.get("column_name") for col in table_data.get("columns", [])]

            # Correct SQL field
            procedure_sql = r.get("ai_response", "")

            # Chart suggestions
            chart_suggestions = []
            if rows_data:
                chart_suggestions = generate_chart_suggestions(rows_data).get("possible_charts", [])

            # Build table object
            tables[table_key] = {
                "title": title,
                "procedure_sql": procedure_sql,
                "columns": columns_data,
                "rows": rows_data,
                "chart_suggestions": chart_suggestions,
                "insights": []  # will fill later
            }

            # Prepare insight input
            if rows_data:
                insight_input.append({
                    "table_name": title,   # EXACT title sent for matching
                    "clean_data": rows_data
                })

        # -----------------------------------
        # Generate Insights
        # -----------------------------------
        # insights_result = generate_insights_only(insight_input)
        # table_insights = insights_result.get("table_insights", {})
        insights_result = generate_insights_only(insight_input)
        table_insights = insights_result

        # Attach insights
        # for key, tbl in tables.items():
        #     title = tbl["title"]
        #     if title in table_insights:
        #         tbl["insights"] = table_insights[title]["insights"]
        for key, tbl in tables.items():
          title = tbl["title"]
          if title in table_insights:
           tbl["insights"] = table_insights[title]
        # -----------------------------------
        # Dropdown options
        # -----------------------------------
        dropdown_options = [
            {"label": tbl["title"], "value": key}
            for key, tbl in tables.items()
        ]

        # -----------------------------------
        # Final Response
        # -----------------------------------
        return build_response(True, "Chat history loaded", 200, data={
            "tables": tables,
            "dropdown_options": dropdown_options
        })

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)