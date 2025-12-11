# """
# Fixed and enhanced single-endpoint CSV pipeline for Flask.
# - Single action-based endpoint: upload, generate_schema, create_table,
#   compare_schema, insert_data, preview, summary
# - Adds schema comparison for existing tables
# - Robust stored-procedure handling (avoids tuple.get errors)
# - Safer DDL creation and upsert
# - JSON-safe outputs

# Place into your project and wire `upload_and_insights_controller` as a route.
# """

# import os
# import json
# import hashlib
# import re
# import pandas as pd
# from flask import request
# from werkzeug.utils import secure_filename
# import numpy as np

# # Helpers (must exist in your project)
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import (
#     build_response,
#     format_file_size,
#     allowed_file,
#     get_upload_folder
# )
# from model.llm_client import call_llm

# # ---------- CONFIG ----------
# UPLOAD_FOLDER = get_upload_folder()
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# # ---------------------------------------------------
# # Utility Functions
# # ---------------------------------------------------
# def to_python(v):
#     if isinstance(v, (np.int64, np.int32, np.uint64, np.uint32)):
#         return int(v)
#     if isinstance(v, (np.float64, np.float32)):
#         return float(v)
#     if isinstance(v, (np.bool_, bool)):
#         return bool(v)
#     if isinstance(v, (int, float)):
#         return v
#     if v is None:
#         return None
#     return str(v)


# def sanitize_table_name(fname):
#     base = os.path.splitext(fname)[0]
#     return re.sub(r"[^a-z0-9_]", "_", base.lower())


# def clean_column_names(columns):
#     s = pd.Series(columns).fillna("col")
#     cleaned = []
#     for i, col in enumerate(s):
#         col = str(col).strip()
#         if col == "" or col.lower() == "nan" or col == "col":
#             col = f"col_{i}"
#         col = re.sub(r"[^\w]", "_", col)
#         if col in cleaned:
#             col = f"{col}_{i}"
#         cleaned.append(col)
#     return cleaned


# def _make_row_hash(values):
#     s = "|".join("" if v is None else str(v) for v in values)
#     return hashlib.md5(s.encode()).hexdigest()


# # ----------------------------
# # Robust JSON parsing helper
# # ----------------------------
# def safe_parse_json(text):
#     if not isinstance(text, str):
#         raise ValueError("safe_parse_json expects string")

#     s = text.strip()
#     s = re.sub(r"```(?:json)?", "", s, flags=re.IGNORECASE).strip()
#     start_candidates = [idx for idx in (s.find("["), s.find("{")) if idx != -1]
#     if start_candidates:
#         start = min(start_candidates)
#         if start > 0:
#             s = s[start:]

#     attempts = [s]
#     attempts.append(s.replace("True", "true").replace("False", "false"))

#     tmp = attempts[-1]
#     tmp2 = re.sub(r"(?<![A-Za-z0-9_])'([^']*?)'(?![A-Za-z0-9_])", r'"\1"', tmp)
#     attempts.append(tmp2)

#     tmp3 = re.sub(r",\s*(\}|\])", r"\1", tmp2)
#     attempts.append(tmp3)

#     last_err = None
#     for a in attempts:
#         try:
#             return json.loads(a)
#         except Exception as e:
#             last_err = e
#             continue

#     raise ValueError(f"safe_parse_json failed: {last_err}")


# # ---------------------------------------------------
# # LLM — Schema Inference (unchanged)
# # ---------------------------------------------------
# def infer_schema_with_llm(df, file_name):
#     try:
#         sample = df.head(10).fillna("").to_dict(orient="records")
#         stats = {}

#         for col in df.columns:
#             ser = df[col].dropna().astype(str)

#             max_len = int(ser.str.len().max()) if not ser.empty else 0
#             distinct = int(ser.nunique()) if not ser.empty else 0

#             integer = bool(not ser.empty and ser.str.match(r"^-?\d+$").all())
#             decimal = bool(not ser.empty and ser.str.match(r"^-?\d+\.\d+$").all())
#             boolean_like = bool(
#                 not ser.empty and ser.str.lower().isin(
#                     ["true", "false", "yes", "no", "0", "1"]
#                 ).all()
#             )

#             # ✅ FIXED — correct usage of .all()
#             json_like = bool(
#                 not ser.empty and ser.str.strip().str.startswith(("{", "[")).all()
#             )

#             date_like = bool(
#                 not ser.empty
#                 and pd.to_datetime(ser.head(10), errors="coerce")
#                 .notna()
#                 .all()
#             )

#             unique = bool(not ser.empty and ser.nunique() == len(ser))

#             stats[col] = {
#                 "max_len": max_len,
#                 "distinct": distinct,
#                 "integer": integer,
#                 "decimal": decimal,
#                 "boolean_like": boolean_like,
#                 "json_like": json_like,
#                 "date_like": date_like,
#                 "unique": unique
#             }

#         # ---------- LLM Prompt ----------
#         prompt = f"""
# You are a Senior MySQL Data Architect.

# Based on column statistics and sample data, generate a BEST-FIT MySQL schema.
# Return ONLY a JSON array.

# Allowed types: INT, BIGINT, SMALLINT, TINYINT, BOOLEAN, FLOAT, DOUBLE, DECIMAL(p,s),
# CHAR(n), VARCHAR(n), TEXT, MEDIUMTEXT, LONGTEXT, JSON, DATE, DATETIME, TIME, YEAR

# Rules:
# - Choose primary key if column unique AND column name contains id/code/uuid/number.
# - VARCHAR length = max_len + 10 (cap 500). Use TEXT if max_len > 1000.
# - DECIMAL for decimals.
# - BOOLEAN for yes/no/true/false/0/1.

# Input Stats:
# {json.dumps(stats, indent=2)}

# Sample Rows:
# {json.dumps(sample, indent=2)}

# Return JSON array only.
# """

#         raw = call_llm(prompt).strip()
#         raw = raw.replace("```", "").strip()

#         parsed = safe_parse_json(raw)

#         if not isinstance(parsed, list):
#             raise ValueError("LLM did not return a JSON array")

#         final_schema = []
#         for item in parsed:
#             if not isinstance(item, dict):
#                 continue

#             name = item.get("column") or item.get("name") or item.get("col")
#             typ = (item.get("type") or "VARCHAR").upper()
#             length = item.get("length")
#             primary = bool(item.get("primary", False))

#             if isinstance(length, str) and length.isdigit():
#                 length = int(length)
#             elif isinstance(length, (np.integer, int)):
#                 length = int(length)
#             else:
#                 length = None

#             final_schema.append({
#                 "column": name,
#                 "datatype": typ,
#                 "length": length,
#                 "primary": primary
#             })

#         return final_schema

#     except Exception as ex:
#         return [{
#             "error": "LLM Schema Error",
#             "message": str(ex)
#         }]


# # ---------------------------------------------------
# # Fetch existing tables created by user
# # ---------------------------------------------------
# def fetch_existing_user_tables_with_schema(cursor, session_id, created_by):
#     cursor.execute("""
#         SELECT DISTINCT table_name
#         FROM uploaded_files
#         WHERE session_id = %s AND created_by = %s
#     """, (session_id, created_by))

#     tables = [row["table_name"] for row in cursor.fetchall()]

#     existing_list = []
#     dropdown_list = []

#     for t in tables:
#         cursor.execute(f"SHOW COLUMNS FROM `{t}`")
#         cols = cursor.fetchall()

#         schema = []
#         for c in cols:
#             dtype = c["Type"] if isinstance(c, dict) and "Type" in c else c.get("Type") if isinstance(c, dict) else c["Type"] if isinstance(c, dict) else c[1]
#             # simple parsing
#             match = re.match(r"(\w+)(?:\((\d+)\))?", c["Type"] if isinstance(c, dict) else c[1])
#             datatype = match.group(1).lower() if match else c["Type"]
#             length = int(match.group(2)) if match and match.group(2) else None

#             schema.append({
#                 "column": c["Field"],
#                 "datatype": datatype,
#                 "length": length,
#                 "primary": c["Key"] == "PRI"
#             })

#         existing_list.append({
#             "table_name": t,
#             "schema": schema
#         })
#         dropdown_list.append({"label": t, "value": t})

#     return {
#         "existing_tables": existing_list,
#         "table_dropdown": dropdown_list
#     }


# # ---------------------------------------------------
# # Schema comparison helper
# # ---------------------------------------------------
# def normalize_type_for_compare(typ):
#     if not typ:
#         return "varchar"
#     t = str(typ).lower()
#     if t.startswith("varchar") or t.startswith("char") or t in ("text", "mediumtext", "longtext"):
#         return "string"
#     if t in ("int", "integer", "bigint", "smallint", "tinyint"):
#         return "int"
#     if t in ("float", "double", "decimal"):
#         return "float"
#     if t in ("date", "datetime", "time", "year"):
#         return "date"
#     if t == "json":
#         return "json"
#     return "string"


# def compare_schemas(file_schema, db_schema):
#     """file_schema and db_schema are lists of dicts with keys: column, datatype (or type), length"""
#     # map by column name (case-insensitive)
#     f_map = {c["column"].lower(): c for c in file_schema}
#     d_map = {c["column"].lower(): c for c in db_schema}

#     missing_in_db = []
#     extra_in_db = []
#     type_mismatches = []

#     for col in f_map:
#         if col not in d_map:
#             missing_in_db.append(f_map[col]["column"])
#         else:
#             f_t = normalize_type_for_compare(f_map[col].get("datatype") or f_map[col].get("type"))
#             d_t = normalize_type_for_compare(d_map[col].get("datatype") or d_map[col].get("type"))
#             if f_t != d_t:
#                 type_mismatches.append({
#                     "column": f_map[col]["column"],
#                     "file_type": f_map[col].get("datatype") or f_map[col].get("type"),
#                     "db_type": d_map[col].get("datatype") or d_map[col].get("type")
#                 })

#     for col in d_map:
#         if col not in f_map:
#             extra_in_db.append(d_map[col]["column"])

#     ok = not (missing_in_db or type_mismatches)
#     return {
#         "ok": ok,
#         "missing_in_db": missing_in_db,
#         "extra_in_db": extra_in_db,
#         "type_mismatches": type_mismatches
#     }


# # ---------------------------------------------------
# # CREATE TABLE DDL
# # ---------------------------------------------------
# def create_table_ddl(cursor, table_name, schema):
#     col_defs = []
#     pk = []
#     for col in schema:
#         name = col["column"]
#         typ = (col.get("datatype") or col.get("type") or "VARCHAR").upper()

#         if typ in ("INT", "INTEGER"):
#             dt = "INT"
#         elif typ == "BIGINT":
#             dt = "BIGINT"
#         elif typ.startswith("DECIMAL"):
#             dt = typ
#         elif typ == "DATETIME":
#             dt = "DATETIME"
#         elif typ == "DATE":
#             dt = "DATE"
#         elif typ == "TEXT":
#             dt = "TEXT"
#         elif typ == "JSON":
#             dt = "JSON"
#         elif typ == "BOOLEAN" or typ == "BOOL":
#             dt = "TINYINT(1)"
#         else:
#             length = col.get("length") or 255
#             try:
#                 length = max(1, min(65535, int(length))) if length is not None else 255
#             except Exception:
#                 length = 255
#             dt = f"VARCHAR({length})"

#         col_defs.append(f"`{name}` {dt}")
#         if col.get("primary"):
#             pk.append(name)

#     pk_sql = f", PRIMARY KEY({','.join(f'`{c}`' for c in pk)})" if pk else ""

#     ddl = f"""
# CREATE TABLE IF NOT EXISTS `{table_name}` (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     {', '.join(col_defs)},
#     row_hash VARCHAR(64)
#     {pk_sql}
# ) ENGINE=InnoDB;
# """
#     cursor.execute(ddl)


# # ---------------------------------------------------
# # UPSERT
# # ---------------------------------------------------
# def upsert_df_to_table(cursor, table_name, df):
#     cols = df.columns.tolist()
#     col_sql = ",".join([f"`{c}`" for c in cols])
#     ph = ",".join(["%s"] * len(cols))
#     update_sql = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in cols if c != "row_hash"])

#     sql = f"""
# INSERT INTO `{table_name}` ({col_sql})
# VALUES ({ph})
# ON DUPLICATE KEY UPDATE {update_sql};
# """
#     cursor.executemany(sql, df.values.tolist())
#     return cursor.rowcount




# # ---------------------------------------------------
# # LLM — Generate Insights
# # ---------------------------------------------------
# def generate_insights_from_llm(df, file_name):
#     """
#     Returns list of short insights (strings). If parsing fails, returns
#     a one-item list with an error message.
#     """
#     try:
#         sample = df.head(10).fillna("").to_dict(orient="records")
#         prompt = f"""
# You are a senior data analyst.
# Generate short actionable insights (JSON array of strings) for file '{file_name}'.
# Return ONLY a JSON array (no commentary).

# Sample rows:
# {json.dumps(sample, indent=2)}
# """
#         raw = call_llm(prompt).strip()
#         # remove markdown fences
#         raw = raw.replace("```json", "").replace("```", "").strip()

#         # extract JSON array portion & parse safely
#         parsed = safe_parse_json(raw)
#         # expect array of strings
#         if isinstance(parsed, list):
#             # normalize to strings
#             out = [str(x) for x in parsed]
#             return out
#         else:
#             return [f"[Insight Error] Unexpected LLM response type: {type(parsed)}"]
#     except Exception as ex:
#         return [f"[Insight Error] {str(ex)}"]



# # ---------------------------------------------------
# # SINGLE ENDPOINT ROUTE HANDLER
# # ---------------------------------------------------
# def upload_and_insights_controller():
#     try:
#         # Determine payload type
#         if request.content_type and request.content_type.startswith("multipart"):
#             action = request.form.get("action")
#             session_id = request.form.get("session_id")
#             created_by = request.form.get("created_by")
#             body = dict(request.form)
#         else:
#             body = request.get_json(force=True)
#             action = body.get("action")
#             session_id = body.get("session_id")
#             created_by = body.get("created_by")
#             file_name = body.get("file_name")

#         if not session_id or not created_by:
#             return build_response(False, "session_id & created_by required", 400)

#         db = get_db_connection()
#         cur = db.cursor(dictionary=True)
#         cur.execute(
#             "SELECT user_id FROM users WHERE session_id=%s AND user_id=%s",
#             (session_id, created_by)
#         )
#         if not cur.fetchone():
#             cur.close(); db.close()
#             return build_response(False, "Invalid session", 400)

#         # ---------------------------
#         # ACTION: UPLOAD
#         # ---------------------------
#         if action == "upload":
#             files = request.files.getlist("files")
#             if not files:
#                 cur.close(); db.close()
#                 return build_response(False, "No file uploaded", 400)

#             f = files[0]
#             fname = secure_filename(f.filename)

#             if not allowed_file(fname):
#                 cur.close(); db.close()
#                 return build_response(False, "Invalid file format", 400)

#             # Save file
#             path = os.path.join(UPLOAD_FOLDER, fname)
#             f.save(path)

#             # Basic info
#             file_size = format_file_size(os.path.getsize(path))
#             suggested_table = sanitize_table_name(fname)

#             # ------------------------------
#             # 👉 NEW: Generate schema for NEW table
#             # ------------------------------
#             try:
#                 df = pd.read_csv(path, dtype=str)
#                 df.columns = clean_column_names(df.columns)
#                 df = df.where(pd.notnull(df), None)

#                 new_table_schema = infer_schema_with_llm(df, fname)

#                 clean_schema = []
#                 for col in new_table_schema:
#                     fixed = {k: to_python(v) for k, v in col.items()}
#                     clean_schema.append(fixed)

#             except Exception as e:
#                 clean_schema = []
            
#             # Fetch existing tables created by THIS USER
#             existing = fetch_existing_user_tables_with_schema(cur, session_id, created_by)

#             cur.close(); db.close()

#             return build_response(True, "File uploaded", 200, {
#                 "file_name": fname,
#                 "file_size": file_size,
#                 "suggested_table_name": suggested_table,
#                 # NEW FIELD FOR UI
#                 "new_table_schema": clean_schema,
#                 "existing_tables": existing["existing_tables"],
#                 "table_dropdown": existing["table_dropdown"],
#             })

#         # ---------------------------
#         # ACTION: PREVIEW
#         # ---------------------------
#         if action == "preview":
#             file_name = body.get("file_name")
#             table_name = body.get("table_name")
#             is_existing = body.get("is_existing", False)  # boolean from UI

#             if not file_name or not table_name:
#                 cur.close(); db.close()
#                 return build_response(False, "file_name and table_name required", 400)

#             # Load CSV file
#             file_path = os.path.join(UPLOAD_FOLDER, file_name)
#             if not os.path.exists(file_path):
#                 cur.close(); db.close()
#                 return build_response(False, "CSV file missing", 400)

#             df = pd.read_csv(file_path, dtype=str)
#             df.columns = clean_column_names(df.columns)
#             df = df.where(pd.notnull(df), None)

#             # ---------- 1️⃣ If EXISTING TABLE → compare schema ----------
#             if is_existing:
#                 # infer schema for uploaded file
#                 file_schema = infer_schema_with_llm(df, file_name)

#                 # normalize schema structure
#                 file_schema_std = [{
#                     "column": c.get("column") or c.get("name"),
#                     "datatype": c.get("datatype") or c.get("type"),
#                     "length": c.get("length")
#                 } for c in file_schema]

#                 # fetch db table schema
#                 cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
#                 cols = cur.fetchall()

#                 db_schema = []
#                 for c in cols:
#                     match = re.match(r"(\w+)(?:\((\d+)\))?", c["Type"])
#                     datatype = match.group(1).lower() if match else c["Type"]
#                     length = int(match.group(2)) if match and match.group(2) else None
#                     db_schema.append({
#                         "column": c["Field"],
#                         "datatype": datatype,
#                         "length": length
#                     })

#                 # compare
#                 compare = compare_schemas(file_schema_std, db_schema)

#                 if not compare["ok"]:
#                     cur.close(); db.close()
#                     return build_response(False, "Schema mismatch", 400, compare)

#             # ---------- 2️⃣ SCHEMA OK → return preview data ----------
#             # Clean dataframe before preview
#             df_clean = (
#                 df
#                 .drop_duplicates()
#                 .dropna(how="all")
#             )

#             preview_rows = (
#                 df_clean
#                 .head(5)
#                 .fillna("")
#                 .to_dict(orient="records")
#             )

#             total_rows = df_clean.shape[0]


#             cur.close(); db.close()

#             return build_response(True, "Preview", 200, {
#                 "table_name": table_name,
#                 "total_rows": total_rows,
#                 "preview_rows": preview_rows
#             })
  
#             # ---------------------------
#             # ACTION: INSERT_DATA
#             # ---------------------------
#         if action == "insert_data":
#                 file_name = body.get("file_name")
#                 table_name = body.get("table_name")
#                 is_existing = body.get("is_existing", False)
#                 schema = body.get("schema")  # new table schema

#                 if not file_name or not table_name:
#                     cur.close(); db.close()
#                     return build_response(False, "file_name and table_name required", 400)

#                 # Load CSV
#                 file_path = os.path.join(UPLOAD_FOLDER, file_name)
#                 if not os.path.exists(file_path):
#                     cur.close(); db.close()
#                     return build_response(False, "CSV file missing", 400)

#                 df = pd.read_csv(file_path, dtype=str)
#                 df.columns = clean_column_names(df.columns)
#                 df = df.where(pd.notnull(df), None)

#                 # Clean data for insert
#                 df_clean = (
#                     df
#                     .drop_duplicates()
#                     .dropna(how="all")
#                 )

#                 total_rows = df_clean.shape[0]
#                 total_columns = df_clean.shape[1]

#                 # Generate row_hash
#                 df_clean["row_hash"] = df_clean.apply(lambda row: _make_row_hash(row.values), axis=1)

#                 # ---------------------------
#                 # If NEW TABLE → create table
#                 # ---------------------------
#                 if not is_existing:
#                     if not schema:
#                         cur.close(); db.close()
#                         return build_response(False, "Schema required for new table creation", 400)

#                     db2 = get_db_connection()
#                     cur2 = db2.cursor()

#                     try:
#                         create_table_ddl(cur2, table_name, schema)
#                         db2.commit()
#                     except Exception as e:
#                         db2.rollback()
#                         cur2.close(); db2.close()
#                         cur.close(); db.close()
#                         return build_response(False, f"Create table failed: {str(e)}", 500)

#                     cur2.close(); db2.close()

#                 # ---------------------------
#                 # Insert into table
#                 # ---------------------------
#                 db3 = get_db_connection()
#                 cur3 = db3.cursor(dictionary=True)

#                 try:
#                     upsert_df_to_table(cur3, table_name, df_clean)
#                     db3.commit()
#                 except Exception as e:
#                     db3.rollback()
#                     cur3.close(); db3.close()
#                     cur.close(); db.close()
#                     return build_response(False, f"Insert failed: {str(e)}", 500)

#                 # ---------------------------
#                 # Generate insights for metadata
#                 # ---------------------------
#                 try:
#                     insights_list = generate_insights_from_llm(df_clean, file_name)
#                     insights_json = json.dumps(insights_list)
#                     insights_status = "done"
#                 except:
#                     insights_json = "[]"
#                     insights_status = "failed"

#                 # ---------------------------
#                 # CALL STORED PROCEDURE (metadata)
#                 # ---------------------------
#                 try:
#                     cur3.callproc("sp_insert_uploaded_file", [
#                         session_id,
#                         file_name,
#                         table_name,
#                         format_file_size(os.path.getsize(file_path)),
#                         "csv",
#                         total_rows,
#                         total_columns,
#                         created_by,
#                         "done",
#                         "done",
#                         insights_json,
#                         insights_status
#                     ])

#                     sp_result = None
#                     for r in cur3.stored_results():
#                         row = r.fetchone()
#                         if row:
#                             sp_result = row
#                             break

#                     if sp_result and isinstance(sp_result, dict):
#                         file_id = sp_result.get("file_id")
#                         status_flag = sp_result.get("status_flag")
#                     else:
#                         file_id = None
#                         status_flag = "UNKNOWN"

#                     db3.commit()

#                 except Exception as e:
#                     db3.rollback()
#                     cur3.close(); db3.close()
#                     cur.close(); db.close()
#                     return build_response(False, f"Procedure failed: {str(e)}", 500)

#                 cur3.close(); db3.close()
#                 cur.close(); db.close()

#                 # ---------------------------
#                 # FINAL MESSAGE
#                 # ---------------------------
#                 msg = f"Table `{table_name}` successfully created with {total_columns} columns and {total_rows} rows."

#                 return build_response(True, "Data inserted", 200, {
#                     "file_id": file_id,
#                     "file_status": status_flag,
#                     "table_name": table_name,
#                     "summary_message": msg
#                 })

       
#         return build_response(False, "Unknown action", 400)

#     except Exception as ex:
#         try:
#             db.close()
#         except Exception:
#             pass
#         return build_response(False, "Server error", 500, {"error": str(ex)})


# app_csv_pipeline.py
"""
Clean, single-endpoint CSV pipeline for Flask (Option A - clean & readable)
Supports actions: upload, preview, insert_data
Features:
- Robust CSV loading with encoding and delimiter sniffing
- Header cleaning (never return null/empty header names)
- LLM schema inference with strict primary-key rules + fail-safes
- Preview (deduped + cleaned)
- Insert with CREATE TABLE (if new) + upsert + metadata SP call
- JSON-safe responses via build_response
"""

import os
import re
import json
import csv
import hashlib
import pandas as pd
import numpy as np
from flask import request
from werkzeug.utils import secure_filename

# Project helpers (must exist)
from database.dbConnection import get_db_connection
from helper.helperFunctions import (
    build_response,
    format_file_size,
    allowed_file,
    get_upload_folder
)
from model.llm_client import call_llm

UPLOAD_FOLDER = get_upload_folder()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -------------------------
# Utilities
# -------------------------
def to_python(v):
    if isinstance(v, (np.integer, np.int64, np.int32)):
        return int(v)
    if isinstance(v, (np.floating, np.float64, np.float32)):
        return float(v)
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if v is None:
        return None
    return str(v)


def sanitize_table_name(fname):
    base = os.path.splitext(fname)[0]
    return re.sub(r"[^a-z0-9_]", "_", base.lower())


def clean_column_names(columns):
    """
    Ensure no null/empty headers. Normalize to word chars and ensure uniqueness.
    """
    s = list(columns)
    clean = []
    seen = {}
    for i, c in enumerate(s):
        name = c
        if name is None:
            name = ""
        name = str(name).strip()
        if name == "" or name.lower() in ["nan", "none"]:
            name = f"col_{i}"
        else:
            name = re.sub(r"[^\w]", "_", name)
            if name == "":
                name = f"col_{i}"
        # uniqueness
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        clean.append(name)
    return clean


def _make_row_hash(values):
    s = "|".join("" if v is None else str(v) for v in values)
    return hashlib.md5(s.encode()).hexdigest()


def safe_parse_json(text):
    """
    Try robust parsing for LLM outputs.
    """
    if not isinstance(text, str):
        raise ValueError("safe_parse_json expects a string")
    s = text.strip()
    s = re.sub(r"```(?:json)?", "", s, flags=re.IGNORECASE).strip()
    # find first { or [
    starts = [idx for idx in (s.find("["), s.find("{")) if idx != -1]
    if starts:
        s = s[min(starts):]
    # try several fixes
    attempts = [s, s.replace("True", "true").replace("False", "false")]
    tmp = attempts[-1]
    tmp2 = re.sub(r"(?<![A-Za-z0-9_])'([^']*?)'(?![A-Za-z0-9_])", r'"\1"', tmp)
    attempts.append(tmp2)
    attempts.append(re.sub(r",\s*(\}|\])", r"\1", tmp2))
    last_err = None
    for a in attempts:
        try:
            return json.loads(a)
        except Exception as e:
            last_err = e
    raise ValueError(f"safe_parse_json failed: {last_err}")


# -------------------------
# LLM Schema inference (Primary-aware)
# -------------------------
# def infer_schema_with_llm(df: pd.DataFrame, file_name: str):
#     """
#     Produce list of dicts: {column, datatype, length, primary}
#     Uses cleaned headers (never null).
#     """
#     try:
#         # ensure df has cleaned headers
#         cleaned_cols = clean_column_names(df.columns)
#         df = df.copy()
#         df.columns = cleaned_cols

#         sample = df.head(10).fillna("").to_dict(orient="records")
#         stats = {}
#         for col in df.columns:
#             ser = df[col].dropna().astype(str)
#             max_len = int(ser.str.len().max()) if not ser.empty else 0
#             distinct = int(ser.nunique()) if not ser.empty else 0
#             integer = bool(not ser.empty and ser.str.match(r"^-?\d+$").all())
#             decimal = bool(not ser.empty and ser.str.match(r"^-?\d+\.\d+$").all())
#             boolean_like = bool(not ser.empty and ser.str.lower().isin(["true", "false", "yes", "no", "0", "1"]).all())
#             json_like = bool(not ser.empty and ser.str.strip().str.startswith(("{", "[")).all())
#             date_like = bool(not ser.empty and pd.to_datetime(ser.head(10), errors="coerce").notna().all())
#             unique = bool(not ser.empty and ser.nunique() == len(ser))
#             stats[col] = {
#                 "max_len": max_len,
#                 "distinct": distinct,
#                 "integer": integer,
#                 "decimal": decimal,
#                 "boolean_like": boolean_like,
#                 "json_like": json_like,
#                 "date_like": date_like,
#                 "unique": unique
#             }

#         # Prompt with strict primary rules
#         prompt = f"""
# You are a Senior MySQL Data Architect.

# Return ONLY a JSON array. Each item is an object with keys:
#   column, type, length (optional), primary (boolean)

# PRIMARY RULES:
# - Mark primary true if column name contains id/_id/uuid/code/num/no/key OR column is UNIQUE
# - If multiple, priority: uuid > id > code > number > no > unique
# - NEVER invent column names, NEVER return null/empty names

# DATA RULES:
# - VARCHAR length = max_len + 10 (cap 500). Use TEXT if >1000.
# - DECIMAL for decimals.
# - BOOLEAN for yes/no/true/false/0/1.
# - DATE/DATETIME when matched.
# - JSON if values start with {{ or [.

# Input Stats:
# {json.dumps(stats, indent=2)}

# Sample Rows:
# {json.dumps(sample, indent=2)}

# Return JSON array only.
# """
#         raw = call_llm(prompt).strip()
#         raw = raw.replace("```", "").strip()
#         parsed = safe_parse_json(raw)

#         if not isinstance(parsed, list):
#             raise ValueError("LLM did not return a JSON array")

#         final = []
#         for idx, item in enumerate(parsed):
#             if not isinstance(item, dict):
#                 continue
#             name = item.get("column") or item.get("name") or item.get("col")
#             # fail-safe: never null name -> use header by index
#             if not name:
#                 if idx < len(cleaned_cols):
#                     name = cleaned_cols[idx]
#                 else:
#                     name = f"col_{idx}"
#             typ = (item.get("type") or item.get("datatype") or "VARCHAR").upper()
#             length = item.get("length")
#             primary = bool(item.get("primary", False))
#             if isinstance(length, str) and length.isdigit():
#                 length = int(length)
#             elif isinstance(length, (np.integer, int)):
#                 length = int(length)
#             else:
#                 length = None
#             final.append({
#                 "column": name,
#                 "datatype": typ,
#                 "length": length,
#                 "primary": primary
#             })
            
#         return final

#     except Exception as ex:
#         # return transparent error structure for frontend
#         return [{"error": "LLM Schema Error", "message": str(ex)}]

# def infer_schema_with_llm(df: pd.DataFrame, file_name: str):
#     try:
#         cleaned_cols = clean_column_names(df.columns)
#         df = df.copy()
#         df.columns = cleaned_cols

#         sample = df.head(10).fillna("").to_dict(orient="records")

#         stats = {}
#         for col in df.columns:
#             ser = df[col].dropna().astype(str)
#             max_len = int(ser.str.len().max()) if not ser.empty else 0
#             distinct = int(ser.nunique()) if not ser.empty else 0
#             integer = bool(not ser.empty and ser.str.match(r"^-?\d+$").all())
#             decimal = bool(not ser.empty and ser.str.match(r"^-?\d+\.\d+$").all())
#             boolean_like = bool(not ser.empty and ser.str.lower().isin(["true", "false", "yes", "no", "0", "1"]).all())
#             json_like = bool(not ser.empty and ser.str.strip().str.startswith(("{", "[")).all())
#             # date_like = bool(not ser.empty and pd.to_datetime(ser.head(10), errors="coerce").notna().all())
#             # ---- FIXED DATE DETECTION (NO WARNINGS) ----
#             DATE_REGEX = (
#                 r"^\d{4}-\d{2}-\d{2}$|"      # yyyy-mm-dd
#                 r"^\d{2}/\d{2}/\d{4}$|"      # dd/mm/yyyy
#                 r"^\d{2}-\d{2}-\d{4}$|"      # dd-mm-yyyy
#                 r"^\d{4}/\d{2}/\d{2}$"       # yyyy/mm/dd
#             )

#             date_like = bool(
#                 not ser.empty
#                 and ser.head(10).str.match(DATE_REGEX).all()
#             )

#             unique = bool(not ser.empty and ser.nunique() == len(ser))

#             stats[col] = {
#                 "max_len": max_len,
#                 "distinct": distinct,
#                 "integer": integer,
#                 "decimal": decimal,
#                 "boolean_like": boolean_like,
#                 "json_like": json_like,
#                 "date_like": date_like,
#                 "unique": unique
#             }

#         prompt = f"""
# You are a Senior MySQL Data Architect.
# Return ONLY a JSON array...
# """

#         raw = call_llm(prompt).strip().replace("```", "")
#         parsed = safe_parse_json(raw)

#         if not isinstance(parsed, list):
#             raise ValueError("LLM did not return a JSON array")

#         final = []

#         # ---------------------
#         # BUILD FINAL SCHEMA
#         # ---------------------
#         for idx, item in enumerate(parsed):
#             if not isinstance(item, dict):
#                 continue

#             name = item.get("column") or item.get("name") or item.get("col")
#             if not name:
#                 name = cleaned_cols[idx] if idx < len(cleaned_cols) else f"col_{idx}"

#             typ = (item.get("type") or item.get("datatype") or "VARCHAR").upper()
#             length = item.get("length")
#             primary = bool(item.get("primary", False))

#             if isinstance(length, str) and length.isdigit():
#                 length = int(length)
#             elif isinstance(length, (np.integer, int)):
#                 length = int(length)
#             else:
#                 length = None

#             final.append({
#                 "column": name,
#                 "datatype": typ,
#                 "length": length,
#                 "primary": primary
#             })

#         # -----------------------------------------------
#         # ** FIX: ENFORCE ONLY ONE PRIMARY KEY **
#         # -----------------------------------------------
#         pk_candidates = [c for c in final if c.get("primary")]

#         if len(pk_candidates) > 1:

#             def pk_priority(col):
#                 name = col["column"].lower()
#                 if "uuid" in name:
#                     return 1
#                 if name == "id" or name.endswith("_id"):
#                     return 2
#                 if "code" in name:
#                     return 3
#                 if "number" in name or name.endswith("no"):
#                     return 4
#                 return 5

#             best = sorted(pk_candidates, key=pk_priority)[0]

#             for col in final:
#                 col["primary"] = (col["column"] == best["column"])

#         return final

#     except Exception as ex:
#         return [{"error": "LLM Schema Error", "message": str(ex)}]

def infer_schema_with_llm(df: pd.DataFrame, file_name: str):
    try:
        # -----------------------------------
        # CLEAN HEADERS
        # -----------------------------------
        cleaned_cols = clean_column_names(df.columns)
        df = df.copy()
        df.columns = cleaned_cols

        sample = df.head(10).fillna("").to_dict(orient="records")

        stats = {}

        # -----------------------------------
        # COLUMN TYPE DETECTION
        # -----------------------------------
        DATE_REGEX = (
            r"^\d{4}-\d{2}-\d{2}$|"      # yyyy-mm-dd
            r"^\d{2}/\d{2}/\d{4}$|"      # dd/mm/yyyy
            r"^\d{2}-\d{2}-\d{4}$|"      # dd-mm-yyyy
            r"^\d{4}/\d{2}/\d{2}$"       # yyyy/mm/dd
        )

        for col in df.columns:
            ser = df[col].dropna().astype(str)

            max_len = int(ser.str.len().max()) if not ser.empty else 0
            distinct = int(ser.nunique()) if not ser.empty else 0

            integer = bool(not ser.empty and ser.str.match(r"^-?\d+$").all())
            decimal = bool(not ser.empty and ser.str.match(r"^-?\d+\.\d+$").all())

            boolean_like = bool(
                not ser.empty and ser.str.lower().isin(
                    ["true", "false", "yes", "no", "0", "1"]
                ).all()
            )

            json_like = bool(
                not ser.empty and ser.str.strip().str.startswith(("{", "[")).all()
            )

            # ---------- FIXED DATE DETECTION ----------
            date_like = bool(
                not ser.empty
                and ser.head(10).str.match(DATE_REGEX).all()
            )

            unique = bool(not ser.empty and ser.nunique() == len(ser))

            stats[col] = {
                "max_len": max_len,
                "distinct": distinct,
                "integer": integer,
                "decimal": decimal,
                "boolean_like": boolean_like,
                "json_like": json_like,
                "date_like": date_like,
                "unique": unique
            }

        # -----------------------------------
        # LLM PROMPT
        # -----------------------------------
        prompt = f"""
You are a Senior MySQL Data Architect.
Based on column statistics and sample data, generate a BEST-FIT MySQL schema.

Return ONLY a JSON array of objects with:
  column, type, length(optional), primary(boolean)

Column stats:
{json.dumps(stats, indent=2)}

Sample rows:
{json.dumps(sample, indent=2)}
"""

        raw = call_llm(prompt).strip().replace("```", "")
        parsed = safe_parse_json(raw)

        if not isinstance(parsed, list):
            raise ValueError("LLM did not return JSON array")

        # -----------------------------------
        # FORMAT FINAL SCHEMA
        # -----------------------------------
        final = []

        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue

            name = item.get("column") or item.get("name") or item.get("col")

            if not name:
                name = cleaned_cols[idx] if idx < len(cleaned_cols) else f"col_{idx}"

            typ = (item.get("type") or item.get("datatype") or "VARCHAR").upper()
            length = item.get("length")

            if isinstance(length, str) and length.isdigit():
                length = int(length)
            elif isinstance(length, (np.integer, int)):
                length = int(length)
            else:
                length = None

            primary = bool(item.get("primary", False))

            final.append({
                "column": name,
                "datatype": typ,
                "length": length,
                "primary": primary
            })

        # -----------------------------------------------
        # ** PRIMARY KEY RULE: ONLY ONE PK ALLOWED **
        # -----------------------------------------------
        pk_candidates = [c for c in final if c.get("primary")]

        if len(pk_candidates) > 1:

            def pk_priority(col):
                name = col["column"].lower()
                if "uuid" in name: return 1
                if name == "id" or name.endswith("_id"): return 2
                if "code" in name: return 3
                if "number" in name or name.endswith("no"): return 4
                return 5

            best = sorted(pk_candidates, key=pk_priority)[0]

            for col in final:
                col["primary"] = (col["column"] == best["column"])

        return final

    except Exception as ex:
        return [{"error": "LLM Schema Error", "message": str(ex)}]

# -------------------------
# Schema compare helpers
# -------------------------
def normalize_type_for_compare(typ):
    if not typ:
        return "string"
    t = str(typ).lower()
    if t.startswith("varchar") or t.startswith("char") or t in ("text", "mediumtext", "longtext"):
        return "string"
    if t in ("int", "integer", "bigint", "smallint", "tinyint"):
        return "int"
    if t in ("float", "double", "decimal"):
        return "float"
    if t in ("date", "datetime", "time", "year"):
        return "date"
    if "json" in t:
        return "json"
    return "string"


def compare_schemas(file_schema, db_schema):
    """
    Both are lists of {column, datatype, length}
    """
    f_map = {c["column"].lower(): c for c in file_schema}
    d_map = {c["column"].lower(): c for c in db_schema}
    missing, extra, mismatch = [], [], []
    for col in f_map:
        if col not in d_map:
            missing.append(f_map[col]["column"])
        else:
            ft = normalize_type_for_compare(f_map[col].get("datatype") or f_map[col].get("type"))
            dt = normalize_type_for_compare(d_map[col].get("datatype") or d_map[col].get("type"))
            if ft != dt:
                mismatch.append({
                    "column": f_map[col]["column"],
                    "file_type": f_map[col].get("datatype") or f_map[col].get("type"),
                    "db_type": d_map[col].get("datatype") or d_map[col].get("type")
                })
    for col in d_map:
        if col not in f_map:
            extra.append(d_map[col]["column"])
    ok = not (missing or mismatch)
    return {"ok": ok, "missing_in_db": missing, "extra_in_db": extra, "type_mismatches": mismatch}


# -------------------------
# DDL & Upsert
# -------------------------
# def create_table_ddl(cursor, table_name, schema):
#     """
#     Create table based on user-provided schema:
#     - If user provides primary key → NO id column created.
#     - If primary column is INT/BIGINT → apply AUTO_INCREMENT.
#     - If user provides no PK → create id INT AUTO_INCREMENT PRIMARY KEY.
#     """
#     col_defs = []
#     pk_cols = []
#     auto_inc_col = None

#     for col in schema:
#         name = col.get("column")
#         if not name:
#             continue

#         datatype = (col.get("datatype") or col.get("type") or "VARCHAR").upper()

#         # determine base datatype
#         if datatype in ("INT", "INTEGER"):
#             dt = "INT"
#         elif datatype == "BIGINT":
#             dt = "BIGINT"
#         elif datatype.startswith("DECIMAL"):
#             dt = datatype
#         elif datatype == "DATE":
#             dt = "DATE"
#         elif datatype == "DATETIME":
#             dt = "DATETIME"
#         elif datatype == "TEXT":
#             dt = "TEXT"
#         elif "JSON" in datatype:
#             dt = "JSON"
#         elif datatype in ("BOOLEAN", "BOOL"):
#             dt = "TINYINT(1) DEFAULT 0"
#         else:
#             length = col.get("length") or 255
#             try:
#                 length = max(1, min(500, int(length)))
#             except:
#                 length = 255
#             dt = f"VARCHAR({length})"

#         # --- PRIMARY KEY LOGIC ---
#         if col.get("primary"):
#             pk_cols.append(name)

#             # If PK is numeric → set auto_increment later
#             if dt in ("INT", "BIGINT"):
#                 auto_inc_col = name

#         col_defs.append(f"`{name}` {dt}")

#     # --- CASE A: User has given PK ---
#     if pk_cols:
#         final_defs = []

#         for cd in col_defs:
#             col_name = cd.split()[0].strip("`")

#             # Add AUTO_INCREMENT if this is PK & numeric
#             if col_name == auto_inc_col:
#                 cd = cd + " AUTO_INCREMENT"

#             final_defs.append(cd)

#         ddl = f"""
# CREATE TABLE IF NOT EXISTS `{table_name}` (
#     {", ".join(final_defs)},
#     row_hash VARCHAR(64),
#     PRIMARY KEY({",".join(f"`{c}`" for c in pk_cols)})
# ) ENGINE=InnoDB;
# """

#     # --- CASE B: No PK provided by user ---
#     else:
#         ddl = f"""
# CREATE TABLE IF NOT EXISTS `{table_name}` (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     {", ".join(col_defs)},
#     row_hash VARCHAR(64)
# ) ENGINE=InnoDB;
# """

#     cursor.execute(ddl)


def create_table_ddl(cursor, table_name, schema):
    col_defs = []
    pk_cols = []
    numeric_pk_cols = []

    # collect PK columns and numeric PKs
    for col in schema:
        name = col["column"]
        datatype = (col.get("datatype") or col.get("type") or "VARCHAR").upper()

        # base dt
        if datatype in ("INT", "INTEGER"):
            dt = "INT"
        elif datatype == "BIGINT":
            dt = "BIGINT"
        elif datatype.startswith("DECIMAL"):
            dt = datatype
        elif datatype == "DATE":
            dt = "DATE"
        elif datatype == "DATETIME":
            dt = "DATETIME"
        elif datatype == "TEXT":
            dt = "TEXT"
        elif "JSON" in datatype:
            dt = "JSON"
        elif datatype in ("BOOLEAN", "BOOL"):
            dt = "TINYINT(1) DEFAULT 0"
        else:
            length = col.get("length") or 255
            try:
                length = max(1, min(500, int(length)))
            except:
                length = 255
            dt = f"VARCHAR({length})"

        # primary handling
        if col.get("primary"):
            pk_cols.append(name)
            if dt in ("INT", "BIGINT"):
                numeric_pk_cols.append(name)

        col_defs.append(f"`{name}` {dt}")

    # -----------------------------
    # AUTO_INCREMENT RULE
    # -----------------------------
    auto_inc_col = None

    if len(pk_cols) == 1:          # only one PK allowed to use AUTO_INCREMENT
        if len(numeric_pk_cols) == 1:
            auto_inc_col = numeric_pk_cols[0]

    # build column definitions
    final_defs = []
    for cd in col_defs:
        col_name = cd.split()[0].strip("`")
        if col_name == auto_inc_col:
            cd += " AUTO_INCREMENT"
        final_defs.append(cd)

    # build ddl
    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        {", ".join(final_defs)},
        row_hash VARCHAR(64),
        PRIMARY KEY({",".join(f"`{c}`" for c in pk_cols)})
    ) ENGINE=InnoDB;
    """

    cursor.execute(ddl)


def normalize_boolean_columns(df):
    bool_map = {
        "true": 1, "false": 0,
        "yes": 1, "no": 0,
        "1": 1, "0": 0,
        True: 1, False: 0
    }

    for col in df.columns:
        # Column has boolean-like values?
        if df[col].astype(str).str.lower().isin(["true", "false", "yes", "no", "1", "0"]).any():
            df[col] = df[col].astype(str).str.lower().map(bool_map).fillna(0)

    return df



def upsert_df_to_table(cursor, table_name, df: pd.DataFrame):
    cols = df.columns.tolist()
    col_sql = ",".join([f"`{c}`" for c in cols])
    ph = ",".join(["%s"] * len(cols))
    update_sql = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in cols if c != "row_hash"])
    sql = f"""
INSERT INTO `{table_name}` ({col_sql})
VALUES ({ph})
ON DUPLICATE KEY UPDATE {update_sql};
"""
    cursor.executemany(sql, df.values.tolist())
    return cursor.rowcount


# -------------------------
# Insights (LLM) - optional
# -------------------------
def generate_insights_from_llm(df: pd.DataFrame, file_name: str):
    try:
        sample = df.head(10).fillna("").to_dict(orient="records")
        prompt = f"""
You are a senior data analyst.
Return ONLY a JSON array of short insights (strings) for file '{file_name}'.

Sample rows:
{json.dumps(sample, indent=2)}
"""
        raw = call_llm(prompt).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = safe_parse_json(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        return [f"[Insight Error] Unexpected LLM response type: {type(parsed)}"]
    except Exception as ex:
        return [f"[Insight Error] {str(ex)}"]


# -------------------------
# Fetch user's existing tables (simple)
# -------------------------
def fetch_existing_user_tables_with_schema(cursor, session_id, created_by):
    cursor.execute("""
        SELECT DISTINCT table_name FROM uploaded_files
        WHERE session_id = %s AND created_by = %s
    """, (session_id, created_by))
    tables = [r["table_name"] for r in cursor.fetchall()]
    existing_list = []
    dropdown = []
    for t in tables:
        try:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = cursor.fetchall()
            schema = []
            for c in cols:
                # c expected to be dict-like with keys Field, Type, Key
                type_str = c.get("Type") if isinstance(c, dict) else c[1]
                match = re.match(r"(\w+)(?:\((\d+)\))?", type_str)
                datatype = match.group(1).lower() if match else type_str
                length = int(match.group(2)) if match and match.group(2) else None
                schema.append({"column": c["Field"], "datatype": datatype, "length": length, "primary": c.get("Key") == "PRI"})
            existing_list.append({"table_name": t, "schema": schema})
            dropdown.append({"label": t, "value": t})
        except Exception:
            # skip problematic table
            continue
    return {"existing_tables": existing_list, "table_dropdown": dropdown}


# -------------------------
# Main single-endpoint handler
# -------------------------
def upload_and_insights_controller():
    try:
        # parse payload
        if request.content_type and request.content_type.startswith("multipart"):
            action = request.form.get("action")
            session_id = request.form.get("session_id")
            created_by = request.form.get("created_by")
            body = dict(request.form)
        else:
            body = request.get_json(force=True)
            action = body.get("action")
            session_id = body.get("session_id")
            created_by = body.get("created_by")
            # file_name may be sent for preview/insert
            file_name = body.get("file_name")

        if not session_id or not created_by:
            return build_response(False, "session_id & created_by required", 400)

        db = get_db_connection()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT user_id FROM users WHERE session_id=%s AND user_id=%s", (session_id, created_by))
        if not cur.fetchone():
            cur.close(); db.close()
            return build_response(False, "Invalid session", 400)

        # --------------------------
        # ACTION: upload
        # --------------------------
        if action == "upload":
            files = request.files.getlist("files")
            if not files:
                cur.close(); db.close()
                return build_response(False, "No file uploaded", 400)
            f = files[0]
            fname = secure_filename(f.filename)
            if not allowed_file(fname):
                cur.close(); db.close()
                return build_response(False, "Invalid file format", 400)
            # save
            path = os.path.join(UPLOAD_FOLDER, fname)
            f.save(path)
            file_size = format_file_size(os.path.getsize(path))
            suggested_table = sanitize_table_name(fname)

            # robust CSV load (encoding + delimiter sniff)
            try:
                df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
            except Exception:
                # try sniff delimiter
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as fh:
                    sample = fh.read(4096)
                    try:
                        dialect = csv.Sniffer().sniff(sample)
                        delimiter = dialect.delimiter
                    except Exception:
                        delimiter = ','
                df = pd.read_csv(path, dtype=str, delimiter=delimiter, encoding="utf-8-sig", error_bad_lines=False)

            # header cleaning: never-null names & uniqueness
            raw_cols = list(df.columns)
            cleaned_headers = clean_column_names(raw_cols)
            df.columns = cleaned_headers

            # data cleaning (keep NaN -> None)
            df = df.where(pd.notnull(df), None)

            # generate schema via LLM (safe)
            try:
                new_table_schema = infer_schema_with_llm(df, fname)
            except Exception as e:
                new_table_schema = [{"error": "schema_infer_failed", "message": str(e)}]

            # ensure no null column names
            clean_schema = []
            for i, col in enumerate(new_table_schema):
                # ensure dict
                if not isinstance(col, dict):
                    continue
                fixed = {k: to_python(v) for k, v in col.items()}
                if fixed.get("column") in [None, "", "null", "None"]:
                    # fallback to header index
                    if i < len(cleaned_headers):
                        fixed["column"] = cleaned_headers[i]
                    else:
                        fixed["column"] = f"col_{i}"
                clean_schema.append(fixed)

            # fetch existing tables for UI
            existing = fetch_existing_user_tables_with_schema(cur, session_id, created_by)

            cur.close(); db.close()
            return build_response(True, "File uploaded", 200, {
                "file_name": fname,
                "file_size": file_size,
                "suggested_table_name": suggested_table,
                "new_table_schema": clean_schema,
                "existing_tables": existing["existing_tables"],
                "table_dropdown": existing["table_dropdown"],
            })

        # --------------------------
        # ACTION: preview
        # --------------------------
                # --------------------------
        # ACTION: preview
        # --------------------------
        if action == "preview":
            file_name = body.get("file_name")
            table_name = body.get("table_name")
            is_existing = bool(body.get("is_existing", False))
            schema = body.get("schema")  # only for new table preview

            if not file_name or not table_name:
                cur.close(); db.close()
                return build_response(False, "file_name and table_name required", 400)

            path = os.path.join(UPLOAD_FOLDER, file_name)
            if not os.path.exists(path):
                cur.close(); db.close()
                return build_response(False, "CSV file missing", 400)

            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
            df.columns = clean_column_names(df.columns)
            df = df.where(pd.notnull(df), None)

            # ------------------------------------
            # CASE 1: NEW TABLE PREVIEW (is_existing = false)
            # ------------------------------------
            if not is_existing:
                if not schema:
                    cur.close(); db.close()
                    return build_response(False, "Schema required for new table preview", 400)

                expected_cols = [col["column"] for col in schema]

                # Add missing schema columns
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = None

                # Remove extra CSV columns
                df = df[expected_cols]

                # Convert boolean-like columns to 1/0
                df = normalize_boolean_columns(df)

                df_clean = df.drop_duplicates().dropna(how="all")

                preview_rows = df_clean.head(5).fillna("").to_dict(orient="records")
                total_rows = df_clean.shape[0]

                cur.close(); db.close()

                return build_response(True, "Preview", 200, {
                    "table_name": table_name,
                    "total_rows": total_rows,
                    "preview_rows": preview_rows
                })

            # ------------------------------------
            # CASE 2: EXISTING TABLE PREVIEW
            # ------------------------------------
            df_clean = df.drop_duplicates().dropna(how="all")

            csv_cols = [c.lower() for c in df_clean.columns]

            cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
            cols = cur.fetchall()

            db_cols = [
                c["Field"].lower()
                for c in cols
                if c["Field"].lower() not in ("id", "row_hash")
            ]

            missing_in_csv = [c for c in db_cols if c not in csv_cols]
            extra_in_csv = [c for c in csv_cols if c not in db_cols]

            if missing_in_csv or extra_in_csv:
                cur.close(); db.close()
                return build_response(False, "Schema mismatch", 400, {
                    "missing_in_csv": missing_in_csv,
                    "extra_in_csv": extra_in_csv
                })

            df_clean = normalize_boolean_columns(df_clean)

            preview_rows = df_clean.head(5).fillna("").to_dict(orient="records")
            total_rows = df_clean.shape[0]

            cur.close(); db.close()
            return build_response(True, "Preview", 200, {
                "table_name": table_name,
                "total_rows": total_rows,
                "preview_rows": preview_rows
            })

        
        
        
        
        # if action == "preview":
        #     file_name = body.get("file_name")
        #     table_name = body.get("table_name")
        #     is_existing = bool(body.get("is_existing", False))

        #     if not file_name or not table_name:
        #         cur.close(); db.close()
        #         return build_response(False, "file_name and table_name required", 400)

        #     path = os.path.join(UPLOAD_FOLDER, file_name)
        #     if not os.path.exists(path):
        #         cur.close(); db.close()
        #         return build_response(False, "CSV file missing", 400)

        #     df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        #     df.columns = clean_column_names(df.columns)
        #     df = df.where(pd.notnull(df), None)

        #     # if existing table -> compare schema
        #     # if is_existing:
        #     #     file_schema = infer_schema_with_llm(df, file_name)
        #     #     file_schema_std = [{"column": c.get("column") or c.get("name"), "datatype": c.get("datatype") or c.get("type"), "length": c.get("length")} for c in file_schema]

        #     #     # db schema
        #     #     cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        #     #     cols = cur.fetchall()
        #     #     db_schema = []
        #     #     for c in cols:
        #     #         match = re.match(r"(\w+)(?:\((\d+)\))?", c["Type"])
        #     #         datatype = match.group(1).lower() if match else c["Type"]
        #     #         length = int(match.group(2)) if match and match.group(2) else None
        #     #         db_schema.append({"column": c["Field"], "datatype": datatype, "length": length})
        #     #     compare = compare_schemas(file_schema_std, db_schema)
        #     #     if not compare["ok"]:
        #     #         cur.close(); db.close()
        #     #         return build_response(False, "Schema mismatch", 400, compare)

           
        #     # --------- NEW: SIMPLE EXISTING TABLE SCHEMA CHECK ---------
        #     if is_existing:
        #         df_clean = df.drop_duplicates().dropna(how="all")

        #         csv_cols = [c.lower() for c in df_clean.columns]

        #         # fetch DB table columns
        #         cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        #         cols = cur.fetchall()

        #         db_cols = [
        #             c["Field"].lower()
        #             for c in cols
        #             if c["Field"].lower() not in ("id", "row_hash")
        #         ]

        #         missing_in_csv = [c for c in db_cols if c not in csv_cols]
        #         extra_in_csv = [c for c in csv_cols if c not in db_cols]

        #         if missing_in_csv or extra_in_csv:
        #             cur.close(); db.close()
        #             return build_response(False, "Schema mismatch", 400, {
        #                 "missing_in_csv": missing_in_csv,
        #                 "extra_in_csv": extra_in_csv
        #             })

        #     # prepare preview: dedupe + drop all-empty rows
        #     df_clean = df.drop_duplicates().dropna(how="all")

        #     # Convert all boolean-like columns (TRUE/FALSE, Yes/No, etc.)
        #     df_clean = normalize_boolean_columns(df_clean)
        #     preview_rows = df_clean.head(5).fillna("").to_dict(orient="records")
        #     total_rows = int(df_clean.shape[0])
        #     cur.close(); db.close()
        #     return build_response(True, "Preview", 200, {"table_name": table_name, "total_rows": total_rows, "preview_rows": preview_rows})

        # --------------------------
        # ACTION: insert_data
        # --------------------------
        # if action == "insert_data":
        #     file_name = body.get("file_name")
        #     table_name = body.get("table_name")
        #     is_existing = bool(body.get("is_existing", False))
        #     schema = body.get("schema")  # schema list expected for new table (from frontend)

        #     if not file_name or not table_name:
        #         cur.close(); db.close()
        #         return build_response(False, "file_name and table_name required", 400)

        #     path = os.path.join(UPLOAD_FOLDER, file_name)
        #     if not os.path.exists(path):
        #         cur.close(); db.close()
        #         return build_response(False, "CSV file missing", 400)

        #     df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        #     df.columns = clean_column_names(df.columns)
        #     df = df.where(pd.notnull(df), None)

        #     df_clean = df.drop_duplicates().dropna(how="all")

        #    #  Convert all boolean-like columns (TRUE/FALSE, Yes/No, etc.)
        #     df_clean = normalize_boolean_columns(df_clean)
        #     total_rows = int(df_clean.shape[0])
        #     total_columns = int(df_clean.shape[1])

        #     # add row_hash
        #     df_clean["row_hash"] = df_clean.apply(lambda r: _make_row_hash(r.values), axis=1)

        #     # Create table if new
        #     if not is_existing:
        #         if not schema or not isinstance(schema, list):
        #             cur.close(); db.close()
        #             return build_response(False, "Schema required for new table creation", 400)
        #         db2 = get_db_connection()
        #         cur2 = db2.cursor()
        #         try:
        #             create_table_ddl(cur2, table_name, schema)
        #             db2.commit()
        #         except Exception as e:
        #             db2.rollback()
        #             cur2.close(); db2.close()
        #             cur.close(); db.close()
        #             return build_response(False, f"Create table failed: {str(e)}", 500)
        #         cur2.close(); db2.close()

        #     # Insert/upsert
        #     db3 = get_db_connection()
        #     cur3 = db3.cursor(dictionary=True)
        #     try:
        #         upsert_df_to_table(cur3, table_name, df_clean)
        #         db3.commit()
        #     except Exception as e:
        #         db3.rollback()
        #         cur3.close(); db3.close()
        #         cur.close(); db.close()
        #         return build_response(False, f"Insert failed: {str(e)}", 500)

        #     # Generate insights (best-effort)
        #     try:
        #         insights_list = generate_insights_from_llm(df_clean, file_name)
        #         insights_json = json.dumps(insights_list)
        #         insight_status = "done"
        #     except:
        #         insights_json = "[]"
        #         insight_status = "failed"

        #     # Call metadata stored procedure (sp_insert_uploaded_file) - adapt args as needed
        #     file_id = None
        #     status_flag = "UNKNOWN"
        #     try:
        #         cur3.callproc("sp_insert_uploaded_file", [
        #             session_id,
        #             file_name,
        #             table_name,
        #             format_file_size(os.path.getsize(path)),
        #             "csv",
        #             total_rows,
        #             total_columns,
        #             created_by,
        #             "done",       # file_status
        #             "done",       # insert_status
        #             insights_json,
        #             insight_status
        #         ])
        #         # read first stored_results() row if present
        #         sp_result = None
        #         for r in cur3.stored_results():
        #             row = r.fetchone()
        #             if row:
        #                 sp_result = row
        #                 break
        #         if sp_result and isinstance(sp_result, dict):
        #             file_id = sp_result.get("file_id")
        #             status_flag = sp_result.get("status_flag") or status_flag
        #         db3.commit()
        #     except Exception as e:
        #         db3.rollback()
        #         cur3.close(); db3.close()
        #         cur.close(); db.close()
        #         return build_response(False, f"Procedure failed: {str(e)}", 500)

        #     cur3.close(); db3.close()
        #     cur.close(); db.close()

        #     msg = f"Table `{table_name}` successfully created with {total_columns} columns and {total_rows} rows."
        #     return build_response(True, "Data inserted", 200, {"file_id": file_id, "file_status": status_flag, "table_name": table_name, "summary_message": msg})
        # --------------------------
        # ACTION: insert_data
        # --------------------------
        # if action == "insert_data":
        #     file_name = body.get("file_name")
        #     table_name = body.get("table_name")
        #     is_existing = bool(body.get("is_existing", False))
        #     schema = body.get("schema")  # Only required for new table creation

        #     if not file_name or not table_name:
        #         cur.close(); db.close()
        #         return build_response(False, "file_name and table_name required", 400)

        #     # --- Load CSV ---
        #     path = os.path.join(UPLOAD_FOLDER, file_name)
        #     if not os.path.exists(path):
        #         cur.close(); db.close()
        #         return build_response(False, "CSV file missing", 400)

        #     df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        #     df.columns = clean_column_names(df.columns)
        #     df = df.where(pd.notnull(df), None)

        #     # --- Clean & Normalize ---
        #     df_clean = df.drop_duplicates().dropna(how="all")
            
        #     # Normalize TRUE/FALSE → 1/0
        #     df_clean = normalize_boolean_columns(df_clean)

        #     # Add row_hash
        #     df_clean["row_hash"] = df_clean.apply(lambda r: _make_row_hash(r.values), axis=1)

        #     total_rows = int(df_clean.shape[0])
        #     total_cols = int(df_clean.shape[1])

        #     # --------------------------------------
        #     # NEW TABLE → CREATE TABLE USING UI SCHEMA
        #     # --------------------------------------
        #     if not is_existing:
        #         if not schema:
        #             cur.close(); db.close()
        #             return build_response(False, "Schema required for new table", 400)

        #         db2 = get_db_connection()
        #         cur2 = db2.cursor()

        #         try:
        #             create_table_ddl(cur2, table_name, schema)  # UI schema only
        #             db2.commit()
        #         except Exception as e:
        #             db2.rollback()
        #             cur2.close(); db2.close()
        #             cur.close(); db.close()
        #             return build_response(False, f"Create table failed: {str(e)}", 500)

        #         cur2.close(); db2.close()

        #     # --------------------------------------
        #     # INSERT / UPSERT → both cases
        #     # --------------------------------------
        #     db3 = get_db_connection()
        #     cur3 = db3.cursor(dictionary=True)

        #     try:
        #         upsert_df_to_table(cur3, table_name, df_clean)
        #         db3.commit()
        #     except Exception as e:
        #         db3.rollback()
        #         cur3.close(); db3.close()
        #         cur.close(); db.close()
        #         return build_response(False, f"Insert failed: {str(e)}", 500)

        #     # --------------------------------------
        #     # DONE
        #     # --------------------------------------
            
        #     cur3.close(); db3.close()
        #     cur.close(); db.close()
        #     msg = f"Table `{table_name}` successfully created with {total_cols} columns and {total_rows} rows."

        #     return build_response(True, "Data inserted", 200, {
        #         "table_name": table_name,
        #         "total_rows": total_rows,
        #         "total_columns": total_cols,
        #         "summary_message": msg
        #     })

        # --------------------------
        # ACTION: insert_data
        # --------------------------
        if action == "insert_data":
            file_name = body.get("file_name")
            table_name = body.get("table_name")
            is_existing = bool(body.get("is_existing", False))
            schema = body.get("schema")  # Only required for new table creation

            if not file_name or not table_name:
                cur.close(); db.close()
                return build_response(False, "file_name and table_name required", 400)

            # --- Load CSV ---
            path = os.path.join(UPLOAD_FOLDER, file_name)
            if not os.path.exists(path):
                cur.close(); db.close()
                return build_response(False, "CSV file missing", 400)

            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
            df.columns = clean_column_names(df.columns)
            df = df.where(pd.notnull(df), None)

            # --- Clean & Normalize ---
            df_clean = df.drop_duplicates().dropna(how="all")
            df_clean = normalize_boolean_columns(df_clean)

            # Add row_hash
            df_clean["row_hash"] = df_clean.apply(lambda r: _make_row_hash(r.values), axis=1)

            total_rows = df_clean.shape[0]
            total_cols = df_clean.shape[1]

            # --------------------------------------
            # NEW TABLE → CREATE TABLE USING UI SCHEMA
            # --------------------------------------
            if not is_existing:
                if not schema:
                    cur.close(); db.close()
                    return build_response(False, "Schema required for new table", 400)

                db2 = get_db_connection()
                cur2 = db2.cursor()

                try:
                    create_table_ddl(cur2, table_name, schema)
                    db2.commit()
                except Exception as e:
                    db2.rollback()
                    cur2.close(); db2.close()
                    cur.close(); db.close()
                    return build_response(False, f"Create table failed: {str(e)}", 500)

                cur2.close(); db2.close()

            # --------------------------------------
            # INSERT / UPSERT → both new and existing
            # --------------------------------------
            db3 = get_db_connection()
            cur3 = db3.cursor(dictionary=True)

            try:
                upsert_df_to_table(cur3, table_name, df_clean)
                db3.commit()
            except Exception as e:
                db3.rollback()
                cur3.close(); db3.close()
                cur.close(); db.close()
                return build_response(False, f"Insert failed: {str(e)}", 500)

            # --------------------------------------
            # Generate LLM insights
            # --------------------------------------
            try:
                insights_list = generate_insights_from_llm(df_clean, file_name)
                insights_json = json.dumps(insights_list)
                insight_status = "done"
            except:
                insights_json = "[]"
                insight_status = "failed"

            # --------------------------------------
            # CALL STORED PROCEDURE (metadata)
            # --------------------------------------
            try:
                cur3.callproc("sp_insert_uploaded_file_new", [
                    session_id,
                    file_name,
                    table_name,
                    format_file_size(os.path.getsize(path)),
                    "csv",
                    total_rows,
                    total_cols,
                    created_by,
                    "done",
                    "done",
                    insights_json,
                    insight_status
                ])

                sp_result = None
                for r in cur3.stored_results():
                    row = r.fetchone()
                    if row:
                        sp_result = row
                        break

                if sp_result and isinstance(sp_result, dict):
                    file_id = sp_result.get("file_id")
                    status_flag = sp_result.get("status_flag")
                else:
                    file_id = None
                    status_flag = "UNKNOWN"

                db3.commit()

            except Exception as e:
                db3.rollback()
                cur3.close(); db3.close()
                cur.close(); db.close()
                return build_response(False, f"Procedure failed: {str(e)}", 500)

            cur3.close(); db3.close()
            cur.close(); db.close()

            return build_response(True, "Data inserted", 200, {
                "file_id": file_id,
                "file_status": status_flag,
                "table_name": table_name,
                "total_rows": total_rows,
                "total_columns": total_cols,
                "summary_message": f"Table `{table_name}` successfully created with {total_cols} columns and {total_rows} rows."
            })


        # unknown action
        cur.close(); db.close()
        return build_response(False, "Unknown action", 400)

    except Exception as ex:
        try:
            db.close()
        except Exception:
            pass
        return build_response(False, "Server error", 500, {"error": str(ex)})
