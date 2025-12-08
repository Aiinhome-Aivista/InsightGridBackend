# import pandas as pd
# from flask import request
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response
# import json
# import re
# from model.llm_client import call_llm


# def sanitize_for_json(data):
#     return json.loads(json.dumps(data, default=str))
# def sanitize_json_for_mysql(data):
#     json_text = json.dumps(data, ensure_ascii=False)
#     json_text = json_text.replace("\\", "\\\\")
#     json_text = json_text.replace("\"", "\\\"")
#     return json_text

# def mysql_safe_json(data):
#     txt = json.dumps(data, ensure_ascii=False)

#     txt = txt.replace("\u0000", "")    
#     txt = txt.replace("\\\\", "\\")    
#     txt = txt.replace("\\'", "'")      
#     txt = txt.replace("\n", " ")       
#     txt = txt.replace("\r", " ")

#     return txt

# def normalize(name):
#     return str(name).strip().lower().replace(" ", "_")    
# def clean_insight_text(text):
#     if not isinstance(text, str):
#         return text
#     return text.replace("\n", " ").replace("\r", " ").strip()
# def generate_column_summaries_llm(col_name, dtype, samples, call_llm):
#     prompt = f"""
# You are an expert data analyst. Generate two ONE-LINE summaries for this column.

# Column Name: {col_name}
# Data Type: {dtype}
# Sample Values: {samples[:10]}

# Return JSON exactly in this format:
# {{
#   "contextual_summary": "One-line human meaning",
#   "technical_summary": "One-line technical definition"
# }}
# """

#     try:
#         res = call_llm(prompt)
#         res = re.sub(r"```json|```", "", res).strip()
#         j = json.loads(res)

#         return (
#             j.get("contextual_summary", "Summary unavailable"),
#             j.get("technical_summary", "Summary unavailable")
#         )

#     except:
#         return ("Summary unavailable", "Summary unavailable")

# # def save_processed_cleaned_data(
# #     session_id,
# #     session_name,
# #     created_by,
# #     global_operations,
# #     final_result
# # ):

# #     upload_status = "Done"
# #     data_insights_status = final_result[0].get("insights_status", "Failed")

# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()

# #         cursor.callproc("sp_store_processed_cleaned_data", [
# #             session_id,
# #             session_name,
# #             mysql_safe_json(global_operations),   # FIXED
# #             mysql_safe_json(final_result),        # FIXED
# #             upload_status,
# #             data_insights_status,
# #             created_by
# #         ])

# #         conn.commit()
# #         cursor.close()
# #         conn.close()
# #         return True, None

# #     except Exception as e:
# #         return False, str(e)

# # def save_processed_cleaned_data(
# #     session_id,
# #     session_name,
# #     created_by,
# #     global_operations,
# #     final_result
# # ):
# #     # ----------------------------
# #     # DECIDE UPLOAD STATUS
# #     # ----------------------------
# #     all_ok = (
# #         final_result and                      # tables cleaned
# #         len(final_result) > 0 and
# #         global_operations is not None and     # global ops generated
# #         isinstance(global_operations, dict) and
# #         any(global_operations.values())       # at least one operation exists
# #     )

# #     upload_status = "Done" if all_ok else "Failed"

# #     # Data insights status
# #     data_insights_status = final_result[0]["insights_status"] if final_result else "Failed"
# #     # safe_final_result = sanitize_for_json(final_result)
# #     # safe_global_ops = sanitize_for_json(global_operations)
# #     print('sp call',final_result)
# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()

# #         cursor.callproc("sp_store_processed_cleaned_data", [
# #             session_id,
# #             session_name,
# #             # safe_global_ops,
# #             # safe_final_result,
# #             json.dumps(global_operations),
# #             json.dumps(final_result),
# #         #   json.dumps(safe_global_ops, ensure_ascii=False),     # FIXED
# #         #   json.dumps(safe_final_result, ensure_ascii=False),
# #             upload_status,                # <-- NOW CORRECT
# #             data_insights_status,
# #             created_by
# #         ])

# #         conn.commit()
# #         cursor.close()
# #         conn.close()

# #         return True, None

# #     except Exception as e:
# #         return False, str(e)




# def build_global_operations(tables, call_llm):
#     """
#     Extract ALL distinct datatypes from ALL tables
#     and generate suggested operations ONCE per datatype.
#     """

#     datatype_samples = {}  # { "number": [values], "date": [...], ... }

#     # Collect samples for each datatype
#     for table in tables:
#         df = pd.DataFrame(table["clean_data"])
#         if df.empty:
#             continue

#         for col in df.columns:
#             sample_vals = df[col].head(50).tolist()
#             detected_type = infer_type_from_values(sample_vals)

#             if detected_type not in datatype_samples:
#                 datatype_samples[detected_type] = sample_vals

#     # Now call LLM ONCE per distinct datatype
#     global_operations = {}

#     for dtype, samples in datatype_samples.items():
#         try:
#             ops = get_dynamic_operations_llm(dtype, dtype, samples, call_llm)
#         except:
#             ops = ["LLM Error"]

#         global_operations[dtype] = ops

#     return global_operations


# # ============================================================
# # INSIGHTS + RELATIONSHIPS USING LLM
# # ============================================================
# # def generate_insights_and_relationships(tables, call_llm):

# #     tables_text = ""
# #     for table in tables:
# #         tables_text += f"Table: {table['table_name']}\n"
# #         df = pd.DataFrame(table["clean_data"])
# #         if not df.empty:
# #             tables_text += df.head(50).to_string(index=False)
# #         tables_text += "\n\n"

# #     prompt = f"""
# # You are a data analyst. Analyze the following tables and generate meaningful insights.

# # Return ONLY valid JSON in EXACTLY this format:

# # {{
# #   "table_insights": {{
# #              "TableName": {{
# #                 "insights": [...],
# #                 "relationships": [...]
# #             }}
# #           }}
# # }}

# # Important rules:
# # - Use the REAL table names from the input (Sheet names).
# # - Always return at least 2–3 insights per table.
# # - Do NOT include relationships.
# # - Do NOT add extra text or explanation.

# # Here is the data:
# # {tables_text}
# # """

# #     try:
# #         res = call_llm(prompt)
# #         res = re.sub(r"```json|```", "", res).strip()
# #         return json.loads(res)
# #     except Exception as e:
# #         print("INSIGHTS PARSE ERROR:", e)
# #         return {"table_insights": {}}
# # def generate_insights_and_relationships(tables, call_llm):
# #     print('generate_insights_and_relationships:-----> ',tables)
# #     tables_text = ""
# #     for table in tables:
# #         tables_text += f"Table: {table['table_name']}\n"
# #         df = pd.DataFrame(table["clean_data"])
# #         if not df.empty:
# #             tables_text += df.head(50).to_string(index=False)
# #         tables_text += "\n\n"

# #     prompt = f"""
# #     Analyze the following tables and return insights + relationships.
# #     Return ONLY valid JSON:
# #     {{
# #         "table_insights": {{
# #             "TableName": {{
# #                 "insights": [...],
# #                 "relationships": [...]
# #             }}
# #         }}
# #     }}

# #     {tables_text}
# #     """

# #     try:
# #         res = call_llm(prompt)
# #         res = re.sub(r"```json|```", "", res).strip()
# #         return json.loads(res)
# #     except:
# #         return {"table_insights": {}}

# def generate_insights_and_relationships(tables, call_llm):
#     tables_text = ""
#     for table in tables:
#         tables_text += f"Table: {table['table_name']}\n"
#         df = pd.DataFrame(table["clean_data"])
#         if not df.empty:
#             tables_text += df.head(50).to_string(index=False)
#         tables_text += "\n\n"

#     prompt = f"""
#     Analyze the following tables and return insights + relationships.
#     Return ONLY valid JSON:
#     {{
#         "table_insights": {{
#             "TableName": {{
#                 "insights": [...],
#                 "relationships": [...]
#             }}
#         }}
#     }}
#     {tables_text}
#     """

#     try:
#         res = call_llm(prompt)
#         cleaned = re.sub(r"```json|```", "", res).strip()
#         result = json.loads(cleaned)
#         return result, None   # ⭐ No error
#     except Exception as e:
#         error_reason = str(e)
#         return {"table_insights": {}}, error_reason   # ⭐ Return failure reason


# def get_dynamic_operations_llm(col_name, detected_type, sample_values, call_llm):
#     """
#     Ask LLM to suggest UI operations/filters for a column dynamically.
#     """
#     prompt = f"""
# You are a data analyst. Based on the column name, detected type, and sample values,
# suggest appropriate operations or filters that can be applied to this column in a UI.
# Return ONLY as a JSON array of strings. Example: ["Sum", "Filter by Range", "Top N"]

# Column Name: {col_name}
# Detected Type: {detected_type}
# Sample Values: {sample_values[:10]}
# """
#     try:
#         response = call_llm(prompt)
#     except Exception as e:
#         return ["LLM Error: " + str(e)]

#     response = re.sub(r"```json|```", "", response, flags=re.IGNORECASE).strip()

#     try:
#         ops = json.loads(response)
#         if not isinstance(ops, list):
#             ops = [str(ops)]
#     except:
#         ops = [response]

#     return ops


# def clean_data(raw_data):
#     if not raw_data:
#         return []

#     sheet_rows = {}

#     for row in raw_data:
#         row_json = row.get("row_data")

#         # Convert string JSON
#         if isinstance(row_json, str):
#             try:
#                 row_json = json.loads(row_json)
#             except:
#                 continue

#         if not row_json:
#             continue

#         # --------------------------------------------
#         # CASE 1: Excel Upload → {"data": {"Sheet1": [...], ...}}
#         # --------------------------------------------
#         if isinstance(row_json, dict) and "data" in row_json and isinstance(row_json["data"], dict):
#             for sheet, rows in row_json["data"].items():

#                 if sheet not in sheet_rows:
#                     sheet_rows[sheet] = []

#                 if isinstance(rows, list):
#                     sheet_rows[sheet].extend(rows)

#         # --------------------------------------------
#         # CASE 2: CSV Upload → flat list or dict rows
#         # --------------------------------------------
#         else:
#             sheet = "CSV_File"

#             if sheet not in sheet_rows:
#                 sheet_rows[sheet] = []

#             if isinstance(row_json, list):
#                 sheet_rows[sheet].extend(row_json)
#             else:
#                 sheet_rows[sheet].append(row_json)

#     # --------------------------------------------
#     # CLEAN AND FORMAT EACH TABLE
#     # --------------------------------------------
#     final_tables = []

#     for sheet, rows in sheet_rows.items():
#         df = pd.DataFrame(rows)
#         if df.empty:
#             continue

#         df = df.dropna(how="all").drop_duplicates()
#         df = df.where(pd.notnull(df), None)

#         # Clean text columns
#         for col in df.select_dtypes(include="object"):
#             df[col] = (
#                 df[col]
#                 .astype(str)
#                 .str.strip()
#                 .str.replace(r"\s+", " ", regex=True)
#             )

#         # Convert timestamps / Excel serial dates
#         for col in df.columns:
#             sample_vals = df[col].dropna().astype(str).head(10)

#             if sample_vals.empty:
#                 continue

#             # Timestamp (ms)
#             if sample_vals.apply(lambda x: x.isdigit() and len(x) >= 12).any():
#                 try:
#                     df[col] = pd.to_datetime(df[col], unit="ms").dt.strftime("%Y-%m-%d")
#                     continue
#                 except:
#                     pass

#             # Excel serial date
#             try:
#                 nums = sample_vals.astype(float)
#                 if nums.between(30000, 70000).mean() > 0.7:
#                     df[col] = (
#                         pd.TimedeltaIndex(df[col].astype(float), unit="D")
#                         + pd.Timestamp("1899-12-30")
#                     ).strftime("%Y-%m-%d")
#             except:
#                 pass

#         final_tables.append({
#             "table_name": sheet,
#             "clean_data": df.to_dict(orient="records")
#         })

#     return final_tables


# # def clean_data(raw_data):
# #     if not raw_data:
# #         return []

# #     sheet_rows = {}

# #     # -------------------------------
# #     # 1. Group rows by sheet
# #     # -------------------------------
# #     for row in raw_data:
# #         row_json = row.get("row_data")

# #         if isinstance(row_json, str):
# #             try:
# #                 row_json = json.loads(row_json)
# #             except:
# #                 continue

# #         if not row_json or "data" not in row_json:
# #             continue

# #         for sheet, rows in row_json["data"].items():

# #             if sheet not in sheet_rows:
# #                 sheet_rows[sheet] = []

# #             if isinstance(rows, list):
# #                 sheet_rows[sheet].extend(rows)

# #     final_tables = []

# #     # -------------------------------
# #     # 2. Process each sheet table
# #     # -------------------------------
# #     for sheet, rows in sheet_rows.items():

# #         df = pd.DataFrame(rows)
# #         if df.empty:
# #             continue

# #         df = df.dropna(how="all").drop_duplicates()
# #         df = df.where(pd.notnull(df), None)

# #         # Trim whitespace
# #         for col in df.select_dtypes(include="object"):
# #             df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

# #         # ----------------------------------------
# #         # ⭐ FIX: Convert timestamps + Excel dates
# #         # ----------------------------------------
# #         for col in df.columns:

# #             col_dtype = df[col].dtype

# #             if col_dtype in ["int64", "float64", "int32", "float32"]:
# #                 sample_vals = df[col].dropna().astype(str).head(10)

# #                 if len(sample_vals) == 0:
# #                     continue

# #                 # Detect timestamp milliseconds
# #                 is_timestamp = sample_vals.apply(lambda x: x.isdigit() and len(x) >= 12).any()

# #                 if is_timestamp:
# #                     try:
# #                         df[col] = pd.to_datetime(df[col], unit='ms').dt.strftime("%Y-%m-%d")
# #                         continue
# #                     except:
# #                         pass

# #                 # Detect Excel serial date (30k–70k)
# #                 is_excel_date = sample_vals.apply(
# #                     lambda x: x.replace('.', '', 1).isdigit() and 30000 < float(x) < 70000
# #                 ).any()

# #                 if is_excel_date:
# #                     try:
# #                         df[col] = pd.TimedeltaIndex(df[col], unit="D") + pd.Timestamp("1899-12-30")
# #                         df[col] = df[col].dt.strftime("%Y-%m-%d")
# #                         continue
# #                     except:
# #                         pass

# #         final_tables.append({
# #             "table_name": sheet,
# #             "clean_data": df.to_dict(orient="records")
# #         })

# #     return final_tables

# def infer_type_from_values(values):
#     vals = [v for v in values if pd.notnull(v)]
#     if not vals:
#         return "string"

#     str_vals = list(map(str, vals))

#     # -------------------------------------------------------
#     # ⭐ 1. Detect Epoch Timestamps (Milliseconds: 13 digits)
#     # -------------------------------------------------------
#     if all(v.isdigit() and len(v) >= 12 for v in str_vals):
#         return "date"

#     # -------------------------------------------------------
#     # ⭐ 2. Detect Epoch Timestamps (Seconds: 10 digits)
#     # -------------------------------------------------------
#     if all(v.isdigit() and len(v) == 10 for v in str_vals):
#         return "date"

#     # -------------------------------------------------------
#     # ⭐ 3. Detect Excel Serial Dates (Integer or Float)
#     #       - Normal Date: 30000 < x < 70000
#     #       - DateTime: float (with decimal)
#     # -------------------------------------------------------
#     serial_nums = []
#     for v in str_vals:
#         if re.match(r"^\d+(\.\d+)?$", v):   # int or float
#             serial_nums.append(float(v))

#     if len(serial_nums) >= len(vals) * 0.7:
#         if all(30000 < x < 70000 for x in serial_nums):
#             # Detect datetime based on decimal part
#             if any(abs(x - int(x)) > 0 for x in serial_nums):
#                 return "datetime"
#             return "date"

#     # -------------------------------------------------------
#     # ⭐ 4. Detect ISO Date / Datetime Strings
#     # -------------------------------------------------------
#     date_count = 0
#     datetime_count = 0

#     for v in str_vals:
#         try:
#             ts = pd.to_datetime(v, errors="raise")

#             # If time = 00:00 → Date only
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

#     # -------------------------------------------------------
#     # ⭐ 5. Numeric
#     # -------------------------------------------------------
#     numeric_vals = []
#     for v in str_vals:
#         cleaned = re.sub(r"[^\d\.\-]", "", v)
#         try:
#             numeric_vals.append(float(cleaned))
#         except:
#             pass

#     if len(numeric_vals) >= len(vals) * 0.7:
#         return "number"

#     # -------------------------------------------------------
#     # ⭐ 6. Default → string
#     # -------------------------------------------------------
#     return "string"



# def build_column_store(df, call_llm):

#     cols = []
#     cid = 1

#     for col in df.columns:
#         samples = df[col].head(20).tolist()
#         dtype = infer_type_from_values(samples)

#         contextual_summary, technical_summary = generate_column_summaries_llm(
#             col, dtype, samples, call_llm
#         )

#         cols.append({
#             "column_id": cid,
#             "column_name": col,
#             "column_type": dtype,
#             "contextual_summary": contextual_summary,
#             "technical_summary": technical_summary
#         })

#         cid += 1

#     return cols



# # ============================================================
# # MAIN CONTROLLER
# # ============================================================
# def fetch_raw_data(session_id, session_name, created_by):
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)

#         cursor.callproc("sp_get_filedata_by_sessionid_sessioname", [session_id, session_name, created_by])
#         result = []
#         for rs in cursor.stored_results():
#             result.extend(rs.fetchall())

#         cursor.close()
#         conn.close()
#         return result

#     except Exception as e:
#         raise Exception(f"Error fetching raw data: {str(e)}")

# def save_processed_cleaned_data(
#     session_id,
#     session_name,
#     created_by,
#     global_operations,
#     final_result
# ):

#     upload_status = "Done"

#     if final_result:
#         data_insights_status = final_result[0].get("insights_status", "Failed")
#     else:
#         data_insights_status = "Failed"


#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         cursor.callproc("sp_store_processed_cleaned_data", [
#             session_id,
#             session_name,
#             json.dumps(global_operations, ensure_ascii=False),
#             json.dumps(final_result, ensure_ascii=False),
#             upload_status,
#             data_insights_status,
#             created_by
#         ])

#         conn.commit()
#         cursor.close()
#         conn.close()
#         return True, None

#     except Exception as e:
#         print("SAVE ERROR:", e)
#         return False, str(e)

# def process_session_data_controller():
#     try:
#         body = request.get_json() or {}

#         session_id = body.get("session_id")
#         session_name = body.get("session_name")
#         created_by = body.get("created_by")
#         if not session_id or not session_name or not created_by:
#             return build_response(False, "session_id, session_name, and created_by required", 400)

#         # STEP 1: Fetch raw data
#         raw_data = fetch_raw_data(session_id, session_name, created_by)
#         # print('raw_data',raw_data)
#         if not raw_data:
#             return build_response(False, "No data found", 404)

#         # STEP 2: Clean data
#         tables = clean_data(raw_data)
#         # print('tables',tables)

#         # STEP 3: Global operations
#         global_ops = build_global_operations(tables, call_llm)
#         # print('global_ops',global_ops)

#         # STEP 4: Insights + relationships
#         insights_data, insights_error = generate_insights_and_relationships(tables, call_llm)
#         print('insights_data',insights_data)
#         if insights_error:
#            insights_status = "Failed"
#         else:
#             insights_status = "Done"
#         final_result = []

       
#         for table in tables:

#             table_name = table["table_name"]
#             rows = table["clean_data"]
#             df = pd.DataFrame(rows)

#             column_meta = build_column_store(df, call_llm)
#             clean_columns = list(df.columns)

#             insight_block = insights_data.get("table_insights", {}).get(table_name, {})
#             print('insight_block',insight_block)
#             # --- FIX: CLEAN INSIGHTS BEFORE SAVING ---
#             raw_insights = insight_block.get("insights", [])
#             print('raw_insights',raw_insights)

#             insights = [clean_insight_text(i) for i in raw_insights if i]
#             print('insights',insights)

#             final_result.append({
#                 "table_name": table_name,
#                 "column_metadata": column_meta,
#                 "row_data": rows,
#                 "unused_row_data": {
#                     "clean_total_rows": len(rows),
#                     "clean_total_columns": len(clean_columns)
#                 },
#                 "clean_columns": clean_columns,
#                 "insights": insights,
#                 # "insights_status": "Done"
#                 "insights_status": insights_status,
#                 "insights_error": insights_error
#             })
#         # print('final_result',final_result)
#         # STEP 6: Save to DB
#         ok, err = save_processed_cleaned_data(
#             session_id,
#             session_name,
#             created_by,
#             global_ops,
#             final_result
#         )

#         if not ok:
#             print("DB Save Error:", err)

#         # STEP 7: Response
#         return build_response(True, "Raw data fetched successfully", 200, {
#             "global_operations": global_ops,
#             "tables": final_result
#         })

#     except Exception as e:
#         return build_response(False, str(e), 500)

import pandas as pd
import math
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
import json
import re
from model.llm_client import call_llm


# =====================================================================
#                       JSON SANITIZATION HELPERS
# =====================================================================
def clean_nan(obj):
    """
    Recursively replaces NaN, Infinity with None for valid JSON.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]

    return obj


def safe_mysql_json(data):
    """
    Converts Python object into a CLEAN JSON string suitable for MySQL JSON_TABLE.
    Removes NaN, \u0000, newlines, control chars.
    """
    try:
        cleaned_obj = clean_nan(data)

        txt = json.dumps(
            cleaned_obj,
            ensure_ascii=False,
            allow_nan=False  # <-- THIS prevents NaN errors
        )
    except Exception as e:
        print("JSON ERROR:", e)
        txt = json.dumps(
            json.loads(json.dumps(data, default=str)),
            ensure_ascii=False,
            allow_nan=False
        )

    txt = txt.replace("\u0000", "")
    txt = txt.replace("\n", " ")
    txt = txt.replace("\r", " ")
    return txt


# =====================================================================
#                          GENERAL HELPERS
# =====================================================================
def clean_insight_text(text):
    if not isinstance(text, str):
        return text
    return text.replace("\n", " ").replace("\r", " ").strip()


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


# =====================================================================
#                 BUILD GLOBAL OPERATIONS (UNIQUE TYPE BASED)
# =====================================================================

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



# =====================================================================
#                LLM-based INSIGHTS + RELATIONSHIPS
# =====================================================================
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
        cleaned = re.sub(r"```json|```", "", res).strip()
        result = json.loads(cleaned)
        return result, None
    except Exception as e:
        return {"table_insights": {}}, str(e)


# =====================================================================
#            LLM-based DYNAMIC COLUMN OPERATIONS
# =====================================================================
def get_dynamic_operations_llm(col_name, detected_type, sample_values, call_llm):
    prompt = f"""
You are a data analyst. Based on the column name, detected type, and sample values,
suggest appropriate operations or filters that can be applied to this column in a UI.
Return ONLY as a JSON array of strings.
Column Name: {col_name}
Detected Type: {detected_type}
Sample Values: {sample_values[:10]}
"""
    try:
        res = call_llm(prompt)
        res = re.sub(r"```json|```", "", res).strip()
        ops = json.loads(res)
        return ops if isinstance(ops, list) else [str(ops)]
    except:
        return ["LLM Error"]


# =====================================================================
#                        CLEAN UP RAW DATA
# =====================================================================
def clean_data(raw_data):
    if not raw_data:
        return []

    sheet_rows = {}

    for row in raw_data:
        row_json = row.get("row_data")

        if isinstance(row_json, str):
            try:
                row_json = json.loads(row_json)
            except:
                continue

        if not row_json:
            continue

        # Excel format → {"data": {"Sheet1": [...], ...}}
        if isinstance(row_json, dict) and "data" in row_json:
            for sheet, rows in row_json["data"].items():
                sheet_rows.setdefault(sheet, []).extend(rows)

        else:
            # CSV → flat rows
            sheet_rows.setdefault("CSV_File", []).append(row_json)

    final_tables = []

    for sheet, rows in sheet_rows.items():
        df = pd.DataFrame(rows)
        if df.empty:
            continue

        df = df.dropna(how="all").drop_duplicates()
        df = df.where(pd.notnull(df), None)

        # clean text
        for col in df.select_dtypes(include="object"):
            df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

        # convert timestamp / excel serial
        for col in df.columns:
            sample_vals = df[col].dropna().astype(str).head(10)
            if sample_vals.empty:
                continue

            # timestamp in ms
            if sample_vals.apply(lambda x: x.isdigit() and len(x) >= 12).any():
                try:
                    df[col] = pd.to_datetime(df[col], unit="ms").dt.strftime("%Y-%m-%d")
                except:
                    pass

            # excel serial
            try:
                nums = sample_vals.astype(float)
                if nums.between(30000, 70000).mean() > 0.7:
                    df[col] = (
                        pd.TimedeltaIndex(df[col].astype(float), unit="D")
                        + pd.Timestamp("1899-12-30")
                    ).strftime("%Y-%m-%d")
            except:
                pass

        final_tables.append({
            "table_name": sheet,
            "clean_data": df.to_dict(orient="records")
        })

    return final_tables


# =====================================================================
#                TYPE DETECTOR FOR COLUMNS
# =====================================================================
def infer_type_from_values(values):
    vals = [v for v in values if pd.notnull(v)]
    if not vals:
        return "string"

    sv = list(map(str, vals))

    if all(v.isdigit() and len(v) >= 12 for v in sv):
        return "date"
    if all(v.isdigit() and len(v) == 10 for v in sv):
        return "date"

    nums = []
    for v in sv:
        if re.match(r"^\d+(\.\d+)?$", v):
            nums.append(float(v))

    if nums and len(nums) >= len(vals) * 0.7:
        if all(30000 < n < 70000 for n in nums):
            return "date"

    return "number" if any(v.replace(".", "").isdigit() for v in sv) else "string"


# =====================================================================
#                BUILD COLUMN METADATA
# =====================================================================
def build_column_store(df, call_llm):
    cols = []
    cid = 1

    for col in df.columns:
        samples = df[col].head(20).tolist()
        dtype = infer_type_from_values(samples)

        contextual, technical = generate_column_summaries_llm(col, dtype, samples, call_llm)

        cols.append({
            "column_id": cid,
            "column_name": col,
            "column_type": dtype,
            "contextual_summary": contextual,
            "technical_summary": technical
        })

        cid += 1

    return cols


# =====================================================================
#                FETCH RAW DATA
# =====================================================================
def fetch_raw_data(session_id, session_name, created_by):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.callproc("sp_get_filedata_by_sessionid_sessioname", [session_id, session_name, created_by])
    result = []
    for rs in cursor.stored_results():
        result.extend(rs.fetchall())

    cursor.close()
    conn.close()
    return result


# =====================================================================
#                SAVE FINAL CLEANED DATA TO DATABASE
# =====================================================================
def save_processed_cleaned_data(
    session_id, session_name, created_by, global_operations, final_result
):
    upload_status = "Done"
    data_insights_status = final_result[0].get("insights_status", "Failed") if final_result else "Failed"

    safe_global = safe_mysql_json(global_operations)
    safe_tables = safe_mysql_json(final_result)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.callproc("sp_store_processed_cleaned_data", [
            session_id,
            session_name,
            safe_global,
            safe_tables,
            upload_status,
            data_insights_status,
            created_by
        ])

        conn.commit()
        cursor.close()
        conn.close()
        return True, None

    except Exception as e:
        print("SAVE ERROR:", e)
        return False, str(e)


# =====================================================================
#            MAIN PROCESS CONTROLLER
# =====================================================================
def process_session_data_controller():
    try:
        body = request.get_json() or {}

        session_id = body.get("session_id")
        session_name = body.get("session_name")
        created_by = body.get("created_by")

        if not (session_id and session_name and created_by):
            return build_response(False, "session_id, session_name, and created_by required", 400)

        raw_data = fetch_raw_data(session_id, session_name, created_by)
        if not raw_data:
            return build_response(False, "No data found", 404)

        tables = clean_data(raw_data)

        global_ops = build_global_operations(tables, call_llm)

        insights_data, insights_error = generate_insights_and_relationships(tables, call_llm)
        insights_status = "Failed" if insights_error else "Done"

        final_result = []

        for table in tables:
            table_name = table["table_name"]
            rows = table["clean_data"]

            df = pd.DataFrame(rows)

            meta = build_column_store(df, call_llm)
            clean_cols = list(df.columns)

            insights_block = insights_data.get("table_insights", {}).get(table_name, {})
            raw_insights = insights_block.get("insights", [])

            insights = [clean_insight_text(i) for i in raw_insights if i]

            final_result.append({
                "table_name": table_name,
                "column_metadata": meta,
                "row_data": rows,
                "unused_row_data": {
                    "clean_total_rows": len(rows),
                    "clean_total_columns": len(clean_cols)
                },
                "clean_columns": clean_cols,
                "insights": insights,
                "insights_status": insights_status,
                "insights_error": insights_error
            })

        ok, err = save_processed_cleaned_data(
            session_id, session_name, created_by, global_ops, final_result
        )

        if not ok:
            print("DB Save Error:", err)

        return build_response(True, "Raw data processed successfully", 200, {
            "global_operations": global_ops,
            "tables": final_result
        })

    except Exception as e:
        return build_response(False, str(e), 500)



