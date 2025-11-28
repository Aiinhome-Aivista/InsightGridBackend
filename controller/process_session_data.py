import pandas as pd
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json
import numpy as np
import re
from model.llm_client import call_llm 
# def call_llm(prompt):
#     """
#     Dummy LLM caller — replace with OpenAI / Gemini / Azure later.
#     Must ALWAYS return JSON string.
#     """
#     response = {
#         "contextual_summary": "Short meaning of this column based on values.",
#         "technical_summary": "Technical description such as datatype and structure."
#     }
#     return json.dumps(response)



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
# Helper: Clean raw data
# -----------------------------
def clean_data(raw_data):
    """
    Clean file_data returned from DB.
    - Extract nested row_data JSON correctly
    - Handle multiple sheets
    - Remove technical metadata columns
    - Clean values
    """

    if not raw_data:
        return pd.DataFrame()

    extracted_rows = []

    for row in raw_data:
        # row_data is string → convert to dict
        row_json = row.get("row_data")

        if not row_json:
            continue

        # If row_data is a stringified JSON – decode it
        if isinstance(row_json, str):
            try:
                row_json = json.loads(row_json)
            except:
                continue

        # row_json expected structure:
        # {"data": { "Sheet1": [ {..}, {..} ] }}
        if "data" in row_json:
            sheets = row_json["data"]

            # Extract rows from each sheet
            for sheet_name, sheet_rows in sheets.items():
                if isinstance(sheet_rows, list):
                    for r in sheet_rows:
                        # Add sheet tag and technical info if required
                        rec = {
                            **r,
                            "sheet_name": sheet_name,
                            "file_name": row.get("file_name")
                        }
                        extracted_rows.append(rec)

    if not extracted_rows:
        return pd.DataFrame()

    df = pd.DataFrame(extracted_rows)

    # Remove technical system columns
    drop_cols = ["unique_id", "session_id", "session_name"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')

    # ---------------------
    # BASIC CLEANING
    # ---------------------
    df = df.drop_duplicates().copy()

    # Fill missing
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna("Unknown")
        else:
            df[col] = df[col].fillna(0)

    # String trim
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)

    # Convert date-like columns
    for col in df.columns:
        if 'date' in col.lower():
            df[col] = pd.to_datetime(df[col], errors='ignore')

    # Outlier handling (numeric)
    numeric_cols = df.select_dtypes(include=np.number).columns
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        df[col] = df[col].clip(Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)

    # Rare category handling
    cat_cols = df.select_dtypes(include='object').columns
    for col in cat_cols:
        counts = df[col].value_counts()
        rare = counts[counts < 3].index
        df[col] = df[col].replace(rare, "Other")

    # Remove constant columns
    df = df.loc[:, df.nunique() > 1].copy()

    return df





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


# -------------------------------------------------------------
# 2. Build Column Store With AI Descriptions
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

        # Call LLM safely
        try:
            ai_text = call_llm(prompt)
        except Exception as e:
            ai_text = f'{{"contextual_meaning": "[LLM Error] {str(e)}", "technical_description": ""}}'

        # Remove code fences if any
        ai_text = re.sub(r"```json|```", "", ai_text, flags=re.IGNORECASE).strip()

        # Parse JSON safely
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
            "technical_summary": technical
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
        print("Raw Data:", raw_data)
        if not raw_data:
            return build_response(False, "No data found for this session", 404)

          # Clean the data
        df_cleaned = clean_data(raw_data)
        print("Cleaned Data:", df_cleaned)
        data=df_cleaned.to_dict(orient='records')
        column_metadata = build_column_store(df_cleaned, call_llm)
        print("Column Metadata:", column_metadata)
        # 3️⃣ Return raw data in response
        return build_response(True, "Raw data fetched successfully", 200, data=column_metadata)

    except Exception as e:
        return build_response(False, f"Error fetching data: {str(e)}", 500)

