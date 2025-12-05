import pandas as pd
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json
import re
from model.llm_client import call_llm

def generate_column_summaries_llm(col_name, dtype, samples, call_llm):
    prompt = f"""
You are an expert data analyst. Generate two ONE-LINE summaries for this column.

Column Name: {col_name}
Data Type: {dtype}
Sample Values: {samples[:10]}

Return JSON exactly in this format:
{{
  "contextual_summary": "One-line human meaning",
  "technical_summary": "One-line technical definition"
}}
"""

    try:
        res = call_llm(prompt)
        res = re.sub(r"```json|```", "", res).strip()
        j = json.loads(res)

        return (
            j.get("contextual_summary", "Summary unavailable"),
            j.get("technical_summary", "Summary unavailable")
        )

    except:
        return ("Summary unavailable", "Summary unavailable")



# ============================================================
# SAVE CLEANED DATA → CALL STORED PROCEDURE
# ============================================================
def save_processed_cleaned_data(
    session_id,
    session_name,
    global_operations,
    final_result
):
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
            json.dumps(final_result),  # <-- now includes clean_columns
            upload_status,
            data_insights_status,
            relationship_mapping_status
        ])

        conn.commit()
        cursor.close()
        conn.close()

        return True, None

    except Exception as e:
        return False, str(e)



# ============================================================
# GLOBAL OPERATIONS
# ============================================================
# def build_global_operations(tables, call_llm):
#     datatype_samples = {}

#     for table in tables:
#         df = pd.DataFrame(table["clean_data"])
#         if df.empty:
#             continue

#         for col in df.columns:
#             samples = df[col].head(50).tolist()
#             dtype = infer_type_from_values(samples)

#             if dtype not in datatype_samples:
#                 datatype_samples[dtype] = samples

#     global_ops = {}

#     for dtype, samples in datatype_samples.items():
#         try:
#             ops = get_dynamic_operations_llm(dtype, dtype, samples, call_llm)
#         except:
#             ops = ["LLM Error"]

#         global_ops[dtype] = ops

#     return global_ops

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


# ============================================================
# INSIGHTS + RELATIONSHIPS USING LLM
# ============================================================
def generate_insights_and_relationships(tables, call_llm):

    tables_text = ""
    for table in tables:
        tables_text += f"Table: {table['table_name']}\n"
        df = pd.DataFrame(table["clean_data"])
        if not df.empty:
            tables_text += df.head(50).to_string(index=False)
        tables_text += "\n\n"

    prompt = f"""
    Analyze the following tables and return insights + relationships.
    Return ONLY valid JSON:
    {{
        "table_insights": {{
            "TableName": {{
                "insights": [...],
                "relationships": [...]
            }}
        }}
    }}

    {tables_text}
    """

    try:
        res = call_llm(prompt)
        res = re.sub(r"```json|```", "", res).strip()
        return json.loads(res)
    except:
        return {"table_insights": {}}



# ============================================================
# FETCH RAW DATA FROM DB
# ============================================================
def fetch_raw_data(session_id, session_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc("sp_get_filedata_by_sessionid_sessioname", [session_id, session_name])

        result = []
        for rs in cursor.stored_results():
            result.extend(rs.fetchall())

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        raise Exception(f"Error fetching raw data: {str(e)}")



# ============================================================
# LLM UI OPERATIONS
# ============================================================
# def get_dynamic_operations_llm(col_name, dtype, samples, call_llm):
#     prompt = f"""
#     Suggest UI operations for this datatype.
#     Return JSON array only.

#     Column: {col_name}
#     Type: {dtype}
#     Sample: {samples[:10]}
#     """

#     try:
#         res = call_llm(prompt)
#         res = re.sub(r"```json|```", "", res).strip()
#         ops = json.loads(res)
#         return ops if isinstance(ops, list) else [ops]
#     except:
#         return ["LLM Error"]
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



# ============================================================
# CLEAN RAW DATA
# ============================================================
# def clean_data(raw_data):
#     if not raw_data:
#         return []

#     sheet_rows = {}

#     for row in raw_data:
#         row_json = row.get("row_data")

#         if isinstance(row_json, str):
#             try:
#                 row_json = json.loads(row_json)
#             except:
#                 continue

#         if not row_json or "data" not in row_json:
#             continue

#         for sheet, rows in row_json["data"].items():

#             if sheet not in sheet_rows:
#                 sheet_rows[sheet] = []

#             if isinstance(rows, list):
#                 sheet_rows[sheet].extend(rows)

#     final_tables = []

#     for sheet, rows in sheet_rows.items():

#         df = pd.DataFrame(rows)

#         if df.empty:
#             continue

#         df = df.dropna(how="all").drop_duplicates()
#         df = df.where(pd.notnull(df), None)

#         for col in df.select_dtypes(include="object"):
#             df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

#         final_tables.append({
#             "table_name": sheet,
#             "clean_data": df.to_dict(orient="records")
#         })

#     return final_tables

def clean_data(raw_data):
    if not raw_data:
        return []

    sheet_rows = {}

    # -------------------------------
    # 1. Group rows by sheet
    # -------------------------------
    for row in raw_data:
        row_json = row.get("row_data")

        if isinstance(row_json, str):
            try:
                row_json = json.loads(row_json)
            except:
                continue

        if not row_json or "data" not in row_json:
            continue

        for sheet, rows in row_json["data"].items():

            if sheet not in sheet_rows:
                sheet_rows[sheet] = []

            if isinstance(rows, list):
                sheet_rows[sheet].extend(rows)

    final_tables = []

    # -------------------------------
    # 2. Process each sheet table
    # -------------------------------
    for sheet, rows in sheet_rows.items():

        df = pd.DataFrame(rows)
        if df.empty:
            continue

        df = df.dropna(how="all").drop_duplicates()
        df = df.where(pd.notnull(df), None)

        # Trim whitespace
        for col in df.select_dtypes(include="object"):
            df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

        # ----------------------------------------
        # ⭐ FIX: Convert timestamps + Excel dates
        # ----------------------------------------
        for col in df.columns:

            col_dtype = df[col].dtype

            if col_dtype in ["int64", "float64", "int32", "float32"]:
                sample_vals = df[col].dropna().astype(str).head(10)

                if len(sample_vals) == 0:
                    continue

                # Detect timestamp milliseconds
                is_timestamp = sample_vals.apply(lambda x: x.isdigit() and len(x) >= 12).any()

                if is_timestamp:
                    try:
                        df[col] = pd.to_datetime(df[col], unit='ms').dt.strftime("%Y-%m-%d")
                        continue
                    except:
                        pass

                # Detect Excel serial date (30k–70k)
                is_excel_date = sample_vals.apply(
                    lambda x: x.replace('.', '', 1).isdigit() and 30000 < float(x) < 70000
                ).any()

                if is_excel_date:
                    try:
                        df[col] = pd.TimedeltaIndex(df[col], unit="D") + pd.Timestamp("1899-12-30")
                        df[col] = df[col].dt.strftime("%Y-%m-%d")
                        continue
                    except:
                        pass

        final_tables.append({
            "table_name": sheet,
            "clean_data": df.to_dict(orient="records")
        })

    return final_tables


# ============================================================
# TYPE INFERENCE
# ============================================================
# def infer_type_from_values(values):
#     vals = [v for v in values if pd.notnull(v)]
#     if not vals:
#         return "string"

#     str_vals = list(map(str, vals))

#     # Date / DateTime
#     date_count = 0
#     datetime_count = 0

#     for v in str_vals:
#         try:
#             ts = pd.to_datetime(v, errors='raise')
#             if ts.time() == pd.Timestamp.min.time():
#                 date_count += 1
#             else:
#                 datetime_count += 1
#         except:
#             pass

#     if date_count >= len(vals) * 0.7:
#         return "date"

#     if datetime_count >= len(vals) * 0.7:
#         return "datetime"

#     # Numeric
#     numeric_vals = []
#     for v in str_vals:
#         cleaned = re.sub(r"[^\d\.\-]", "", v)
#         try:
#             numeric_vals.append(float(cleaned))
#         except:
#             pass

#     if len(numeric_vals) >= len(vals) * 0.7:
#         return "number"

#     return "string"
def infer_type_from_values(values):
    vals = [v for v in values if pd.notnull(v)]
    if not vals:
        return "string"

    str_vals = list(map(str, vals))

    # -------------------------------------------------------
    # ⭐ 1. Detect Epoch Timestamps (Milliseconds: 13 digits)
    # -------------------------------------------------------
    if all(v.isdigit() and len(v) >= 12 for v in str_vals):
        return "date"

    # -------------------------------------------------------
    # ⭐ 2. Detect Epoch Timestamps (Seconds: 10 digits)
    # -------------------------------------------------------
    if all(v.isdigit() and len(v) == 10 for v in str_vals):
        return "date"

    # -------------------------------------------------------
    # ⭐ 3. Detect Excel Serial Dates (Integer or Float)
    #       - Normal Date: 30000 < x < 70000
    #       - DateTime: float (with decimal)
    # -------------------------------------------------------
    serial_nums = []
    for v in str_vals:
        if re.match(r"^\d+(\.\d+)?$", v):   # int or float
            serial_nums.append(float(v))

    if len(serial_nums) >= len(vals) * 0.7:
        if all(30000 < x < 70000 for x in serial_nums):
            # Detect datetime based on decimal part
            if any(abs(x - int(x)) > 0 for x in serial_nums):
                return "datetime"
            return "date"

    # -------------------------------------------------------
    # ⭐ 4. Detect ISO Date / Datetime Strings
    # -------------------------------------------------------
    date_count = 0
    datetime_count = 0

    for v in str_vals:
        try:
            ts = pd.to_datetime(v, errors="raise")

            # If time = 00:00 → Date only
            if ts.time() == pd.Timestamp.min.time():
                date_count += 1
            else:
                datetime_count += 1
        except:
            pass

    if date_count >= len(vals) * 0.7:
        return "date"

    if datetime_count >= len(vals) * 0.7:
        return "datetime"

    # -------------------------------------------------------
    # ⭐ 5. Numeric
    # -------------------------------------------------------
    numeric_vals = []
    for v in str_vals:
        cleaned = re.sub(r"[^\d\.\-]", "", v)
        try:
            numeric_vals.append(float(cleaned))
        except:
            pass

    if len(numeric_vals) >= len(vals) * 0.7:
        return "number"

    # -------------------------------------------------------
    # ⭐ 6. Default → string
    # -------------------------------------------------------
    return "string"



# ============================================================
# COLUMN METADATA
# ============================================================
# def build_column_store(df, call_llm):

#     cols = []
#     cid = 1

#     for col in df.columns:
#         samples = df[col].head(20).tolist()
#         dtype = infer_type_from_values(samples)

#         cols.append({
#             "column_id": cid,
#             "column_name": col,
#             "column_type": dtype,
#             "contextual_summary": "",
#             "technical_summary": ""
#         })

#         cid += 1

#     return cols
def build_column_store(df, call_llm):

    cols = []
    cid = 1

    for col in df.columns:
        samples = df[col].head(20).tolist()
        dtype = infer_type_from_values(samples)

        contextual_summary, technical_summary = generate_column_summaries_llm(
            col, dtype, samples, call_llm
        )

        cols.append({
            "column_id": cid,
            "column_name": col,
            "column_type": dtype,
            "contextual_summary": contextual_summary,
            "technical_summary": technical_summary
        })

        cid += 1

    return cols



# ============================================================
# MAIN CONTROLLER
# ============================================================
def process_session_data_controller():
    try:
        body = request.get_json() or {}

        session_id = body.get("session_id")
        session_name = body.get("session_name")

        if not session_id or not session_name:
            return build_response(False, "session_id and session_name required", 400)

        # STEP 1: Fetch raw data
        raw_data = fetch_raw_data(session_id, session_name)

        if not raw_data:
            return build_response(False, "No data found", 404)

        # STEP 2: Clean data
        tables = clean_data(raw_data)

        # STEP 3: Global operations
        global_ops = build_global_operations(tables, call_llm)

        # STEP 4: Insights + relationships
        insights_data = generate_insights_and_relationships(tables, call_llm)

        final_result = []

        # STEP 5: Build final JSON for DB
        for table in tables:

            table_name = table["table_name"]
            rows = table["clean_data"]
            df = pd.DataFrame(rows)

            column_meta = build_column_store(df, call_llm)

            clean_columns = list(df.columns)

            insight_block = insights_data.get("table_insights", {}).get(table_name, {})

            insights = insight_block.get("insights", [])
            relationships = insight_block.get("relationships", [])

            final_result.append({
                "table_name": table_name,
                "column_metadata": column_meta,
                "row_data": rows,
                "unused_row_data": {
                    "clean_total_rows": len(rows),
                    "clean_total_columns": len(clean_columns)
                },
                "clean_columns": clean_columns,             # ⭐ FIXED ⭐
                "insights": insights,
                "insights_status": "Done",
                "relationships": relationships,
                "relationship_extract_status": "Done"
            })

        # STEP 6: Save to DB
        ok, err = save_processed_cleaned_data(
            session_id,
            session_name,
            global_ops,
            final_result
        )

        if not ok:
            print("DB Save Error:", err)

        # STEP 7: Response
        return build_response(True, "Raw data fetched successfully", 200, {
            "global_operations": global_ops,
            "tables": final_result
        })

    except Exception as e:
        return build_response(False, str(e), 500)
