import pandas as pd
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json
import numpy as np
import re
from model.llm_client import call_llm 

import json
from database.dbConnection import get_db_connection

def save_processed_cleaned_data(
    session_id,
    session_name,
    global_operations,
    final_result
):
    """
    Save processed cleaned data into database using stored procedure.
    This function ONLY handles DB saving logic.
    """

    # file_master status values (coming directly from your final_result)
    upload_status = "Done"
    data_insights_status = final_result[0]["insights_status"] if final_result else "Failed"
    relationship_mapping_status = final_result[0]["relationship_extract_status"] if final_result else "Failed"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.callproc("sp_store_processed_cleaned_data", [
            session_id,
            session_name,
            json.dumps(global_operations),
            json.dumps(final_result),
            upload_status,
            data_insights_status,
            relationship_mapping_status
        ])

        conn.commit()
        cursor.close()
        conn.close()

        return True, None  # success

    except Exception as e:
        return False, str(e)  # failed


def build_global_operations(tables, call_llm):
    """
    Extract ALL distinct datatypes from ALL tables
    and generate suggested operations ONCE per datatype.
    """

    datatype_samples = {}  # { "number": [values], "date": [...], ... }

    # Collect samples for each datatype
    for table in tables:
        df = pd.DataFrame(table["clean_data"])
        if df.empty:
            continue

        for col in df.columns:
            sample_vals = df[col].head(50).tolist()
            detected_type = infer_type_from_values(sample_vals)

            if detected_type not in datatype_samples:
                datatype_samples[detected_type] = sample_vals

    # Now call LLM ONCE per distinct datatype
    global_operations = {}

    for dtype, samples in datatype_samples.items():
        try:
            ops = get_dynamic_operations_llm(dtype, dtype, samples, call_llm)
        except:
            ops = ["LLM Error"]

        global_operations[dtype] = ops

    return global_operations

def generate_insights_and_relationships(tables, call_llm):
     # Build tables_text for LLM input
    tables_text = ""
    for table in tables:
        tables_text += f"Table: {table['table_name']}\n"
        df = pd.DataFrame(table["clean_data"])
        if not df.empty:
            # Take only first 50 rows to avoid token limit
            df_sample = df.head(50)
            tables_text += df_sample.to_string(index=False)
        tables_text += "\n\n"
    prompt = f"""
    You are a professional data analyst.

    I will provide you with tables from one or more CSV/Excel files.
    The tables may have arbitrary columns and data.

    TASK:
    1. Analyze all the tables and detect important patterns or trends.
    2. Summarize notable insights per table about:
    - Key entities (customers, products, locations)
    - Quantities, counts, numerical patterns
    - Dates, sequences, peaks
    3. Detect possible relationships between tables:
    - Columns that could serve as join keys
    - Suggest the type of join for each relationship (INNER JOIN, LEFT JOIN, RIGHT JOIN, FULL OUTER JOIN, EXTERNAL JOIN,SELF JOIN)
    - Provide reasoning if possible

    Return a JSON object:
    {{
    "table_insights": {{
        "Sheet1": {{
        "insights": ["..."],
        "relationships": [
            {{
            "target_table": "Sheet2",
            "join_column": "CustomerID",
            "join_type": "LEFT JOIN",
            "reason": "Sheet1 has all customers, Sheet2 has sales only for some customers"
            }}
        ]
        }},
        "Sheet2": {{
        "insights": ["..."],
        "relationships": []
        }}
    }}
    }}

    Only return valid JSON. Do not include code fences or explanations.

    Tables:
    {tables_text}
    """
    try:
        llm_response = call_llm(prompt)
        llm_response = re.sub(r"```json|```", "", llm_response, flags=re.IGNORECASE).strip()
        return json.loads(llm_response)
    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# Helper: Fetch raw data from DB
# -----------------------------
def fetch_raw_data(session_id, session_name):
    """
    Fetch data using stored procedure for a given session_id and session_name
    Returns a list of dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("sp_get_filedata_by_sessionid_sessioname", [session_id, session_name])

        result = []
        for res in cursor.stored_results():
            result.extend(res.fetchall())

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        raise Exception(f"Error fetching data: {str(e)}")

# -----------------------------
# LLM-based dynamic operations
# -----------------------------
def get_dynamic_operations_llm(col_name, detected_type, sample_values, call_llm):
    """
    Ask LLM to suggest UI operations/filters for a column dynamically.
    """
    prompt = f"""
You are a data analyst. Based on the column name, detected type, and sample values,
suggest appropriate operations or filters that can be applied to this column in a UI.
Return ONLY as a JSON array of strings. Example: ["Sum", "Filter by Range", "Top N"]

Column Name: {col_name}
Detected Type: {detected_type}
Sample Values: {sample_values[:10]}
"""
    try:
        response = call_llm(prompt)
    except Exception as e:
        return ["LLM Error: " + str(e)]

    response = re.sub(r"```json|```", "", response, flags=re.IGNORECASE).strip()

    try:
        ops = json.loads(response)
        if not isinstance(ops, list):
            ops = [str(ops)]
    except:
        ops = [response]

    return ops


# -----------------------------
# Helper: Clean raw data
# -----------------------------
def clean_data(raw_data):
    """
    Convert stored DB raw file_data into:
    [
        {
            "table_name": "Sheet1",
            "clean_data": [ {...}, {...} ]
        },
        {
            "table_name": "Sheet2",
            "clean_data": [ {...}, {...} ]
        }
    ]
    """

    if not raw_data:
        return []

    # STEP 1: Extract rows grouped by sheet
    sheet_wise_rows = {}

    for row in raw_data:

        row_json = row.get("row_data")

        # Decode if string
        if isinstance(row_json, str):
            try:
                row_json = json.loads(row_json)
            except:
                continue

        if not row_json or "data" not in row_json:
            continue

        sheets = row_json["data"]

        # Each sheet inside the file
        for sheet_name, sheet_rows in sheets.items():

            if not isinstance(sheet_rows, list):
                continue

            if sheet_name not in sheet_wise_rows:
                sheet_wise_rows[sheet_name] = []

            # Add all rows for this sheet
            for r in sheet_rows:
                clean_record = {**r}
                sheet_wise_rows[sheet_name].append(clean_record)

    # STEP 2: Clean each sheet independently
    final_output = []

    for sheet_name, rows in sheet_wise_rows.items():

        df = pd.DataFrame(rows)

        # ---------- CLEANING ----------
        if df.empty:
            continue

        df = df.dropna(how="all").drop_duplicates()

        # Replace NaN
        df = df.where(pd.notnull(df), None)

        # Trim strings
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

        # Convert dates
        for col in df.columns:
            if "date" in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime("%Y-%m-%d")
                except:
                    pass

        # Remove constant columns
        df = df.loc[:, df.nunique() > 1]

        # Convert DF back to array of objects
        clean_array = df.to_dict(orient="records")

        final_output.append({
            "table_name": sheet_name,
            "clean_data": clean_array
        })

    return final_output

# -------------------------------------------------------------
# 1. AI-Based Type Inference (NO HARDCODED NAME-BASED RULES)
# -------------------------------------------------------------

def infer_type_from_values(values):
    """
    AI-style dynamic column type detection based only on real data values.
    No keyword rules. Fully pattern/statistics based.
    """

    vals = [v for v in values if pd.notnull(v)]
    if len(vals) == 0:
        return "string"

    str_vals = list(map(str, vals))

    # ---------- 1️⃣ DATE / DATETIME ----------
    date_count, datetime_count = 0, 0
    for v in str_vals:
        try:
            parsed = pd.to_datetime(v, errors='raise')
            if parsed.time() == pd.Timestamp.min.time():
                date_count += 1
            else:
                datetime_count += 1
        except:
            pass

    if date_count >= len(vals) * 0.7:
        return "date"
    if datetime_count >= len(vals) * 0.7:
        return "datetime"

    # ---------- 2️⃣ NUMERIC ----------
    numeric_vals = []
    for v in str_vals:
        # Remove currency, %, commas, etc.
        v2 = re.sub(r"[^\d\.\-]", "", v)
        try:
            numeric_vals.append(float(v2))
        except:
            pass

    if len(numeric_vals) >= len(vals) * 0.7:
        return "number"

    # ---------- 3️⃣ BOOLEAN ----------
    bool_set = {"yes", "no", "true", "false", "0", "1", "y", "n"}
    if all(v.lower() in bool_set for v in str_vals):
        return "boolean"

    # ---------- 4️⃣ CATEGORY ----------
    unique_ratio = len(set(str_vals)) / len(vals)
    if unique_ratio < 0.2:
        return "category"

    # ---------- 5️⃣ DEFAULT ----------
    return "string"

# 2. Build Column Store With AI Descriptions & Dynamic Operations
# -------------------------------------------------------------
def build_column_store(df, call_llm):
    column_store = []
    col_id = 1
    skip_cols = {"sheet_name", "file_name"}


    for col in df.columns:
        if col in skip_cols:
            continue

        sample_vals = df[col].head(50).tolist()
        detected_type = infer_type_from_values(sample_vals)

        # ---------- LLM for contextual & technical description ----------
        prompt = f"""
You are a data analyst. 
Given this column name and sample values, write:
1) short contextual meaning (1 line)
2) short technical description (1 line)
Return ONLY as JSON like this:

{{
  "contextual_meaning": "...",
  "technical_description": "..."
}}

column_name: {col}
sample_values: {sample_vals[:5]}
detected_type: {detected_type}
"""

        try:
            ai_text = call_llm(prompt)
        except Exception as e:
            ai_text = f'{{"contextual_meaning": "[LLM Error] {str(e)}", "technical_description": ""}}'

        ai_text = re.sub(r"```json|```", "", ai_text, flags=re.IGNORECASE).strip()

        try:
            ai_json = json.loads(ai_text)
            contextual = ai_json.get("contextual_meaning", "")
            technical = ai_json.get("technical_description", "")
        except:
            contextual = ai_text
            technical = ""
        column_store.append({
            "column_id": col_id,
            "column_name": col,
            "column_type": detected_type,
            "contextual_summary": contextual,
            "technical_summary": technical,
        })

        col_id += 1

    return column_store

# -----------------------------
# Controller: Return raw data only
# -----------------------------
def process_session_data_controller():
    try:
        # 1️⃣ Get request data
        data = request.get_json() or {}
        session_id = data.get("session_id")
        session_name = data.get("session_name")

        if not session_id or not session_name:
            return build_response(False, "session_id and session_name are required", 400)

        # 2️⃣ Fetch raw data
        raw_data = fetch_raw_data(session_id, session_name)
        # print("Raw Data:", raw_data)
        if not raw_data:
            return build_response(False, "No data found for this session", 404)

        tables = clean_data(raw_data)
        # NEW: Build suggested operations globally (all tables, all columns)
        global_operations = build_global_operations(tables, call_llm)
        # Generate insights and relationships
        insights_data = generate_insights_and_relationships(tables, call_llm)

        final_result = []

        for table in tables:

            table_name = table["table_name"]
            rows = table["clean_data"]

            # Build column metadata
            df = pd.DataFrame(rows)
            column_meta = build_column_store(df, call_llm)

            # Extract insights safely
            table_insight_block = insights_data.get("table_insights", {}).get(table_name, {})

            insights = table_insight_block.get("insights")
            relationships = table_insight_block.get("relationships")

            # ---------- INSIGHTS STATUS ----------
            if isinstance(insights, list):
                insights_status = "Done"
            else:
                insights_status = "Failed"
                insights = []
            
            # ---------- RELATIONSHIP STATUS ----------
            if isinstance(relationships, list):
                relationship_extract_status = "Done"
            else:
                relationship_extract_status = "Failed"
                relationships = []
            clean_total_rows = len(rows)
            clean_total_columns = len(rows[0]) if rows else 0
            clean_columns = list(rows[0].keys()) if rows else []
            final_result.append({
                "table_name": table_name,
                "column_metadata": column_meta,
                "clean_data": {
                    "rows": rows,
                    "clean_total_rows": clean_total_rows,
                    "clean_total_columns": clean_total_columns,
                    "clean_columns": clean_columns
                },
                "insights": insights,
                "insights_status": insights_status,
                "relationships": relationships,
                "relationship_extract_status": relationship_extract_status
            })

        # return build_response(True, "Raw data fetched successfully", 200, data={
        #     "global_operations": global_operations,
        #     "tables": final_result
        # })

        # 3️⃣ Return raw data in response
        # return build_response(True, "Raw data fetched successfully", 200, data=final_result)
           # --------------------------------------
        # 3️⃣ SAVE INTO DATABASE
        # --------------------------------------
        save_success, save_error = save_processed_cleaned_data(
            session_id,
            session_name,
            global_operations,
            final_result
        )

        if not save_success:
            print("DB Save Error:", save_error)


        # --------------------------------------
        # 4️⃣ Return Response
        # --------------------------------------
       
        return build_response(True, "Raw data fetched successfully", 200, data={
            "global_operations": global_operations,
            "tables": final_result
        })
    except Exception as e:
        return build_response(False, f"Error fetching data: {str(e)}", 500)

