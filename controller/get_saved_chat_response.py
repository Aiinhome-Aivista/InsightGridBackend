from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import pandas as pd
import json
import re
from model.llm_client import call_llm
import os
import requests

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
    
def generate_insights_only(tables):
    tables_text = ""
    for table in tables:
        tables_text += f"Table: {table['table_name']}\n"
        df = pd.DataFrame(table["clean_data"])
        if not df.empty:
            tables_text += df.head(50).to_string(index=False)
        tables_text += "\n\n"

    system_instruction = "You are an expert data analyst. Your job is to generate insights only."

    user_prompt = f"""
Analyze the following tables and generate ONLY insights.

Return ONLY valid JSON in EXACTLY this format:

{{
  "table_insights": {{
      "TableName": {{
          "insights": [
              "insight 1",
              "insight 2",
              "insight 3"
          ]
      }}
  }}
}}

STRICT RULES:
- Use the REAL table names.
- Minimum 3 insights per table.
- NO relationships.
- NO explanations.
- NO text outside JSON.

Here is the data:
{tables_text}
"""

    try:
        llm_output = call_llm(system_instruction, user_prompt)
        llm_output = re.sub(r"```json|```", "", llm_output).strip()
        return json.loads(llm_output)
    except Exception as e:
        print("INSIGHTS PARSE ERROR:", e)
        return {"table_insights": {}}
    
    
    
    
# ---------------------------------------------------------
# MAIN CONTROLLER — Chat History + Insights + Chart Suggestions
# ---------------------------------------------------------
def get_chat_history_by_user_controller():
    try:
        body = request.get_json()
        created_by = body.get("created_by")
        session_id = body.get("session_id")
   
        
        if not created_by or not session_id:
            return build_response(False, "created_by & session_id required", 400)


        # Fetch chat history
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        #  VALIDATE SESSION ID & created_by
        # -----------------------------------
        cursor.execute(
            "SELECT user_id, session_id FROM users WHERE session_id = %s AND user_id = %s LIMIT 1",
            (session_id, created_by)
        )
        session_row = cursor.fetchone()

        if not session_row:
            cursor.close()
            db.close()
            return build_response(
                False,
                "Invalid session_id or created_by",
                400
            )
        
        cursor.callproc("sp_get_chat_history_by_user", [created_by])

        rows = []
        for rs in cursor.stored_results():
            rows = rs.fetchall()

        cursor.close()
        conn.close()

        if not rows:
            return build_response(True, "No chat history", 200, data={
                "created_by": created_by,
                "chat_titles": [],
                "conversations": [],
                "insights": {}
            })

        chat_titles = []
        conversations = []
        insight_tables = []

        # Process each row
        for r in rows:
            try:
                table_data = json.loads(r.get("table_data")) if r.get("table_data") else {}
            except:
                table_data = {}

            # --- ADD INDIVIDUAL CHART SUGGESTION FOR THIS TABLE ---
            chart_suggestions = {}
            if "rows" in table_data and len(table_data["rows"]) > 0:
                chart_suggestions = generate_chart_suggestions(table_data["rows"])

                # attach inside table_data
                table_data["chart_suggestions"] = chart_suggestions

            # collect titles
            if r["chat_title"] not in chat_titles:
                chat_titles.append(r["chat_title"])

            conversations.append({
                "chat_title": r["chat_title"],
                "user_query": r["user_query"],
                "ai_response": r["ai_response"],
                "table_data": table_data,
                "created_at": r["created_at"]
            })

            # prepare for insights (same as before)
            if "rows" in table_data and len(table_data["rows"]) > 0:
                insight_tables.append({
                    "table_name": r["chat_title"],
                    "clean_data": table_data["rows"]
                })

        # Generate Insights
        insights = generate_insights_only(insight_tables) if insight_tables else {}

        # Final Combined Response
        return build_response(True, "Chat history loaded", 200, data={
            "created_by": created_by,
            "chat_titles": chat_titles,
            "conversations": conversations,
            "insights": insights
        })

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)

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
#                 "insights": {},
#                 "chart_suggestions": {}
#             })

#         chat_titles = []
#         conversations = []
#         insight_tables = []
#         chart_suggestion_tables = []

#         # Process each row
#         for r in rows:

#             # Parse table_data
#             try:
#                 table_data = json.loads(r.get("table_data")) if r.get("table_data") else {}
#             except:
#                 table_data = {}

#             # Collect chat titles
#             if r["chat_title"] not in chat_titles:
#                 chat_titles.append(r["chat_title"])

#             # Add conversation object
#             conversations.append({
#                 "chat_title": r["chat_title"],
#                 "user_query": r["user_query"],
#                 "ai_response": r["ai_response"],
#                 "table_data": table_data,
#                 "created_at": r["created_at"]
#             })

#             # Prepare insights tables
#             if "rows" in table_data and len(table_data["rows"]) > 0:
#                 insight_tables.append({
#                     "table_name": r["chat_title"],
#                     "clean_data": table_data["rows"]
#                 })

#                 chart_suggestion_tables.append(table_data["rows"])


#         # Generate Insights
#         insights = generate_insights_only(insight_tables) if insight_tables else {}

#         # Generate Chart Suggestions for last query dataset
#         chart_suggestions = {}
#         if len(chart_suggestion_tables) > 0:
#             last_table_rows = chart_suggestion_tables[-1]
#             chart_suggestions = generate_chart_suggestions(last_table_rows)

#         # Final Combined Response
#         return build_response(True, "Chat history loaded", 200, data={
#             "created_by": created_by,
#             "chat_titles": chat_titles,
#             "conversations": conversations,
#             "insights": insights,
#             "chart_suggestions": chart_suggestions
#         })

#     except Exception as e:
#         return build_response(False, f"Server Error: {str(e)}", 500)    
# def get_chat_history_by_user_controller():
    try:
        data = request.get_json()
        created_by = data.get("created_by")

        if not created_by:
            return build_response(False, "created_by is required", 400)

        # Fetch chat history
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("sp_get_chat_history_by_user", [created_by])

        rows = []
        for rs in cursor.stored_results():
            rows = rs.fetchall()

        cursor.close()
        conn.close()

        if not rows:
            return build_response(True, "No chat history", 200, data={
                "created_by": created_by,
                "chat_titles": [],
                "conversations": [],
                "insights": {}
            })

        chat_titles = []
        conversations = []
        insight_tables = []

        for r in rows:
            # Parse table_data
            try:
                table_data = json.loads(r.get("table_data")) if r.get("table_data") else {}
            except:
                table_data = {}

            # collect titles
            if r["chat_title"] not in chat_titles:
                chat_titles.append(r["chat_title"])

            # Add conversation object
            conversations.append({
                "chat_title": r["chat_title"],
                "user_query": r["user_query"],
                "ai_response": r["ai_response"],
                "table_data": table_data,
                "created_at": r["created_at"]
            })

            # prepare for insights
            if "rows" in table_data and len(table_data["rows"]) > 0:
                insight_tables.append({
                    "table_name": r["chat_title"],
                    "clean_data": table_data["rows"]
                })

        # Generate insights using LLM
        insights = {}
        if insight_tables:
            insights = generate_insights_only(insight_tables)

        # Final response
        return build_response(True, "Chat history loaded", 200, data={
            "created_by": created_by,
            "chat_titles": chat_titles,
            "conversations": conversations,
            "insights": insights
        })

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)

    try:
        data = request.get_json()

        created_by = data.get("created_by")

        if not created_by:
            return build_response(False, "created_by is required", 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc("sp_get_chat_history_by_user", [created_by])

        result = []
        for rs in cursor.stored_results():
            result = rs.fetchall()

        cursor.close()
        conn.close()

        return build_response(True, "Chat history loaded", 200, data=result)

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)
    

# def get_chat_history_by_user_controller():
    try:
        data = request.get_json()

        created_by = data.get("created_by")

        if not created_by:
            return build_response(False, "created_by is required", 400)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc("sp_get_chat_history_by_user", [
            created_by
        ])

        result = []
        for rs in cursor.stored_results():
            result = rs.fetchall()

        cursor.close()
        conn.close()

        return build_response(True, "Chat history loaded", 200, data=result)

    except Exception as e:
        return build_response(False, f"Server Error: {str(e)}", 500)