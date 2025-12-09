# # # import os
# # # import pandas as pd
# # # import mysql.connector
# # # from flask import request
# # # from werkzeug.utils import secure_filename
# # # from database.dbConnection import get_db_connection
# # # from helper.helperFunctions import build_response


# # # UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
# # # os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# # # def clean_column_names(columns):
# # #     """
# # #     Fix NaN/blank headers, remove spaces, ensure valid SQL identifiers,
# # #     and remove duplicates.
# # #     """
# # #     # Replace NaN with placeholder
# # #     columns = columns.fillna("col")

# # #     cleaned = []
# # #     for i, col in enumerate(columns):
# # #         col = str(col).strip()

# # #         if col == "" or col.lower() == "nan" or col == "col":
# # #             col = f"col_{i}"

# # #         # Remove illegal characters
# # #         col = (
# # #             col.replace(" ", "_")
# # #                .replace("-", "_")
# # #                .replace(".", "_")
# # #                .replace("/", "_")
# # #                .replace("\\", "_")
# # #         )

# # #         # Prevent duplicates
# # #         if col in cleaned:
# # #             col = f"{col}_{i}"

# # #         cleaned.append(col)

# # #     return cleaned


# # # def upload_and_insights_controller():
# # #     try:
# # #         session_id = request.form.get("session_id")
# # #         created_by = request.form.get("created_by")

# # #         if not session_id or not created_by:
# # #             return build_response(False, "session_id & created_by required", 400)

# # #         files = request.files.getlist("files")
# # #         if not files:
# # #             return build_response(False, "No files uploaded", 400)

# # #         db = get_db_connection()
# # #         cursor = db.cursor(dictionary=True)

# # #         result_info = []

# # #         for file in files:
# # #             filename = secure_filename(file.filename)
# # #             filepath = os.path.join(UPLOAD_FOLDER, filename)
# # #             file.save(filepath)

# # #             file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)

# # #             # ---------------------- READ CSV SAFELY ----------------------
# # #             df = pd.read_csv(filepath, encoding='utf-8', dtype=str)
# # #             df = df.drop_duplicates()
# # #             df = df.dropna(how="all")

# # # # ---------------------- CLEAN COLUMN NAMES ----------------------
# # #             df.columns = clean_column_names(df.columns)

# # # # ---------------------- CLEAN CELL VALUES (THIS FIXES YOUR ERROR) ----------------------
# # #             df = df.where(pd.notnull(df), None) 

# # #             total_rows = len(df)
# # #             total_columns = len(df.columns)

# # #             # ---------------------- FIX TABLE NAME ----------------------
# # #             table_name = (
# # #                 filename.replace(".csv", "")
# # #                         .replace("-", "_")
# # #                         .replace(" ", "_")
# # #                         .replace(".", "_")
# # #                         .lower()
# # #             )

# # #             # ---------------------- CREATE TABLE ----------------------
# # #             col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])

# # #             create_sql = f"""
# # #                 CREATE TABLE IF NOT EXISTS `{table_name}` (
# # #                     id INT AUTO_INCREMENT PRIMARY KEY,
# # #                     {col_defs}
# # #                 )
# # #             """
# # #             cursor.execute(create_sql)

# # #             # ---------------------- INSERT DATA ----------------------
# # #             if total_rows > 0:
# # #                 placeholders = ", ".join(["%s"] * len(df.columns))

# # #                 insert_sql = f"""
# # #                     INSERT INTO `{table_name}` ({','.join([f'`{c}`' for c in df.columns])})
# # #                     VALUES ({placeholders})
# # #                 """

# # #                 cursor.executemany(insert_sql, df.values.tolist())

# # #             # ---------------------- SAVE METADATA (Stored Procedure) ----------------------
# # #             cursor.callproc(
# # #                 "sp_insert_uploaded_file",
# # #                 [
# # #                     session_id,
# # #                     filename,
# # #                     table_name,
# # #                     file_size_mb,
# # #                     "csv",
# # #                     total_rows,
# # #                     total_columns,
# # #                     created_by,
# # #                 ],
# # #             )

# # #             file_id = None
# # #             for row in cursor.stored_results():
# # #                 file_id = row.fetchone()["file_id"]

# # #             # ---------------------- INSERT PROCESSING STEPS ----------------------
# # #             cursor.callproc("sp_insert_file_steps", [file_id])

# # #             db.commit()

# # #             # ---------------------- RESPONSE ----------------------
# # #             result_info.append(
# # #                 {
# # #                     "file_id": file_id,
# # #                     "file_name": filename,
# # #                     "table_name": table_name,
# # #                     "total_rows": total_rows,
# # #                     "total_columns": total_columns,
# # #                     "file_size_mb": file_size_mb,
# # #                 }
# # #             )

# # #         return build_response(True, "Files uploaded successfully", 200, result_info)

# # #     except Exception as e:
# # #         return build_response(
# # #             False,
# # #             "Server Error",
# # #             500,
# # #             {"error": str(e)},
# # #         )




# # import os
# # import pandas as pd
# # from flask import request
# # from werkzeug.utils import secure_filename
# # from database.dbConnection import get_db_connection
# # from helper.helperFunctions import build_response


# # UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
# # os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# # def clean_column_names(columns):
# #     columns = columns.fillna("col")
# #     cleaned = []

# #     for i, col in enumerate(columns):
# #         col = str(col).strip()
# #         if col == "" or col.lower() == "nan" or col == "col":
# #             col = f"col_{i}"

# #         col = (
# #             col.replace(" ", "_")
# #                .replace("-", "_")
# #                .replace(".", "_")
# #                .replace("/", "_")
# #                .replace("\\", "_")
# #         )

# #         if col in cleaned:
# #             col = f"{col}_{i}"

# #         cleaned.append(col)

# #     return cleaned


# # def upload_and_insights_controller():
# #     try:
# #         session_id = request.form.get("session_id")
# #         created_by = request.form.get("created_by")

# #         if not session_id or not created_by:
# #             return build_response(False, "session_id & created_by required", 400)

# #         files = request.files.getlist("files")
# #         if not files:
# #             return build_response(False, "No files uploaded", 400)

# #         db = get_db_connection()
# #         cursor = db.cursor(dictionary=True)

# #         result_info = []

# #         for file in files:
# #             filename = secure_filename(file.filename)
# #             filepath = os.path.join(UPLOAD_FOLDER, filename)
# #             file.save(filepath)

# #             file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)

# #             # ------------------- READ CSV -------------------
# #             df = pd.read_csv(filepath, encoding='utf-8', dtype=str)
# #             df = df.drop_duplicates().dropna(how="all")

# #             # ------------------- CLEAN COLUMNS -------------------
# #             df.columns = clean_column_names(df.columns)

# #             # Convert NaN values to NULL for MySQL
# #             df = df.where(pd.notnull(df), None)

# #             total_rows = len(df)
# #             total_columns = len(df.columns)

# #             # ------------------- TABLE NAME -------------------
# #             table_name = (
# #                 filename.replace(".csv", "")
# #                         .replace("-", "_")
# #                         .replace(" ", "_")
# #                         .replace(".", "_")
# #                         .lower()
# #             )

# #             # ------------------- SAVE METADATA (SP CALL) -------------------
# #             cursor.callproc(
# #                 "sp_insert_uploaded_file",
# #                 [
# #                     session_id,
# #                     filename,
# #                     table_name,
# #                     file_size_mb,
# #                     "csv",
# #                     total_rows,
# #                     total_columns,
# #                     created_by,
# #                 ],
# #             )

# #             # fetch file_id
# #             result = list(cursor.stored_results())[0].fetchone()
# #             file_id = result["file_id"]

# #             # ------------------- STEP 1: Table Extraction -------------------
# #             try:
# #                 col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])
# #                 create_sql = f"""
# #                     CREATE TABLE IF NOT EXISTS `{table_name}` (
# #                         id INT AUTO_INCREMENT PRIMARY KEY,
# #                         {col_defs}
# #                     )
# #                 """
# #                 cursor.execute(create_sql)

# #                 # Mark table extraction = done
# #                 cursor.execute(
# #                     "UPDATE uploaded_files SET table_extraction_status='done' WHERE id=%s",
# #                     (file_id,)
# #                 )

# #             except Exception:
# #                 cursor.execute(
# #                     "UPDATE uploaded_files SET table_extraction_status='failed' WHERE id=%s",
# #                     (file_id,)
# #                 )
# #                 db.commit()
# #                 continue  # move to next file

# #             # ------------------- STEP 2: Column Data Insertion -------------------
# #             try:
# #                 if total_rows > 0:
# #                     placeholders = ", ".join(["%s"] * len(df.columns))
# #                     insert_sql = f"""
# #                         INSERT INTO `{table_name}` ({','.join([f'`{c}`' for c in df.columns])})
# #                         VALUES ({placeholders})
# #                     """
# #                     cursor.executemany(insert_sql, df.values.tolist())

# #                 # Mark column extraction = done
# #                 cursor.execute(
# #                     "UPDATE uploaded_files SET column_extraction_status='done' WHERE id=%s",
# #                     (file_id,)
# #                 )

# #             except Exception:
# #                 cursor.execute(
# #                     "UPDATE uploaded_files SET column_extraction_status='failed' WHERE id=%s",
# #                     (file_id,)
# #                 )

# #             # ------------------- INSERT PROCESSING STEPS -------------------
# #             cursor.callproc("sp_insert_file_steps", [file_id])

# #             db.commit()

# #             # Response object
# #             result_info.append({
# #                 "file_id": file_id,
# #                 "file_name": filename,
# #                 "table_name": table_name,
# #                 "total_rows": total_rows,
# #                 "total_columns": total_columns,
# #                 "file_size_mb": file_size_mb,
# #             })

# #         return build_response(True, "Files uploaded successfully", 200, result_info)

# #     except Exception as e:
# #         return build_response(False, "Server Error", 500, {"error": str(e)})

# import os
# import pandas as pd
# import mysql.connector
# from flask import request
# from werkzeug.utils import secure_filename
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response
# import json
# from model.llm_client import call_llm


# UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# def clean_column_names(columns):
#     """
#     Fix NaN/blank headers, remove spaces, ensure valid SQL identifiers,
#     and remove duplicates.
#     """
#     # Replace NaN with placeholder
#     columns = columns.fillna("col")

#     cleaned = []
#     for i, col in enumerate(columns):
#         col = str(col).strip()

#         if col == "" or col.lower() == "nan" or col == "col":
#             col = f"col_{i}"

#         # Remove illegal characters
#         col = (
#             col.replace(" ", "_")
#                .replace("-", "_")
#                .replace(".", "_")
#                .replace("/", "_")
#                .replace("\\", "_")
#         )

#         # Prevent duplicates
#         if col in cleaned:
#             col = f"{col}_{i}"

#         cleaned.append(col)

#     return cleaned


# def generate_insights_from_llm(df, file_name):
#     try:
#         sample_data = df.head(10).to_dict(orient="records")

#         prompt = f"""
#         You are a senior data analyst.

#         Generate insights for the dataset '{file_name}'.

#         Here are sample rows (JSON):
#         {json.dumps(sample_data, indent=2)}

#         IMPORTANT:
#         Respond with ONLY a valid JSON array of strings.
#         No markdown.
#         No backticks.
#         No explanation.
#         Just clean JSON array.
#         """

#         llm_output = call_llm(prompt).strip()

#         # Remove accidental markdown code blocks
#         llm_output = llm_output.replace("```json", "").replace("```", "").strip()

#         # Extract only the JSON array portion
#         start = llm_output.find("[")
#         end = llm_output.rfind("]") + 1
#         pure_json = llm_output[start:end]

#         insights_list = json.loads(pure_json)

#         return insights_list

#     except Exception as e:
#         return [f"[Insight Error] {str(e)}"]


# def upload_and_insights_controller():
#     try:
#         session_id = request.form.get("session_id")
#         created_by = request.form.get("created_by")

#         if not session_id or not created_by:
#             return build_response(False, "session_id & created_by required", 400)

#         files = request.files.getlist("files")
#         if not files:
#             return build_response(False, "No files uploaded", 400)

#         db = get_db_connection()
#         cursor = db.cursor(dictionary=True)

#         result_info = []

#         for file in files:
#             filename = secure_filename(file.filename)
#             filepath = os.path.join(UPLOAD_FOLDER, filename)
#             file.save(filepath)

#             file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)

#             # -------------- READ CSV ------------------
#             df = pd.read_csv(filepath, encoding='utf-8', dtype=str)
#             df = df.drop_duplicates().dropna(how="all")

#             df.columns = clean_column_names(df.columns)
#             df = df.where(pd.notnull(df), None)

#             total_rows = len(df)
#             total_columns = len(df.columns)

#             table_name = (
#                 filename.replace(".csv", "")
#                         .replace("-", "_")
#                         .replace(" ", "_")
#                         .replace(".", "_")
#                         .lower()
#             )

#             # ---------------------- SAVE METADATA (SP) ----------------------
#             cursor.callproc(
#                 "sp_insert_uploaded_file",
#                 [
#                     session_id,
#                     filename,
#                     table_name,
#                     file_size_mb,
#                     "csv",
#                     total_rows,
#                     total_columns,
#                     created_by,
#                 ],
#             )

#             # fetch file_id
#             file_id = list(cursor.stored_results())[0].fetchone()["file_id"]

#             # ---------------------- STEP 1: TABLE EXTRACTION -------------------
#             try:
#                 col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])
#                 cursor.execute(f"""
#                     CREATE TABLE IF NOT EXISTS `{table_name}` (
#                         id INT AUTO_INCREMENT PRIMARY KEY,
#                         {col_defs}
#                     )
#                 """)

#                 cursor.execute(
#                     "UPDATE uploaded_files SET table_extraction_status='done' WHERE id=%s",
#                     (file_id,)
#                 )

#             # except Exception:
#             #     cursor.execute(
#             #         "UPDATE uploaded_files SET table_extraction_status='failed' WHERE id=%s",
#             #         (file_id,)
#             #     )
#             except Exception as e:
#                 cursor.execute(
#                     "UPDATE uploaded_files SET table_extraction_status='failed' WHERE id=%s",
#                     (file_id,)
#                 )
#                 db.commit()
#                 return build_response(False, f"Table creation failed: {str(e)}", 500)

#                 # db.commit()
#                 # continue

#             # ---------------------- STEP 2: COLUMN INSERTION -------------------
#             try:
#                 if total_rows > 0:
#                     placeholders = ", ".join(["%s"] * len(df.columns))
#                     insert_sql = f"""
#                         INSERT INTO `{table_name}` ({','.join([f'`{c}`' for c in df.columns])})
#                         VALUES ({placeholders})
#                     """
#                     cursor.executemany(insert_sql, df.values.tolist())

#                 cursor.execute(
#                     "UPDATE uploaded_files SET column_extraction_status='done' WHERE id=%s",
#                     (file_id,)
#                 )

#             # except Exception:
#             #     cursor.execute(
#             #         "UPDATE uploaded_files SET column_extraction_status='failed' WHERE id=%s",
#             #         (file_id,)
#             #     )
#             except Exception as e:
#                 cursor.execute(
#                     "UPDATE uploaded_files SET column_extraction_status='failed' WHERE id=%s",
#                     (file_id,)
#                 )
#                 db.commit()
#                 return build_response(False, f"Column insertion failed: {str(e)}", 500)

#             # ---------------------- STEP 3: INSIGHTS GENERATION -------------------
#             try:
#                 insights = generate_insights_from_llm(df, filename)
#                 print("Generated Insights:", insights)
#                 cursor.execute(
#                     "UPDATE uploaded_files SET insights=%s, data_insights_status='done' WHERE id=%s",
#                     (json.dumps(insights), file_id) 
#                 )

#             # except Exception:
#             #     cursor.execute(
#             #         "UPDATE uploaded_files SET data_insights_status='failed' WHERE id=%s",
#             #         (file_id,)
#             #     )
#             except Exception as e:
#                 cursor.execute(
#                     "UPDATE uploaded_files SET data_insights_status='failed' WHERE id=%s",
#                     (file_id,)
#                 )
#                 db.commit()
#                 return build_response(False, f"Insights generation failed: {str(e)}", 500)

#             # ---------------------- SAVE PROCESSING STEP ROW -------------------
#             cursor.callproc("sp_insert_file_steps", [file_id])

#             db.commit()

#             result_info.append({
#                 "file_id": file_id,
#                 "file_name": filename,
#                 "table_name": table_name,
#                 "total_rows": total_rows,
#                 "total_columns": total_columns,
#                 "file_size_mb": file_size_mb,
#             })

#         return build_response(True, "Files uploaded successfully + insights generated", 200, result_info)

#     except Exception as e:
#         return build_response(False, "Server Error", 500, {"error": str(e)})

import os
import json
import hashlib
import pandas as pd
from flask import request
from werkzeug.utils import secure_filename
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response
from model.llm_client import call_llm

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def clean_column_names(columns):
    columns = columns.fillna("col")
    cleaned = []
    for i, col in enumerate(columns):
        col = str(col).strip()
        if col == "" or col.lower() == "nan" or col == "col":
            col = f"col_{i}"
        col = col.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_").replace("\\", "_")
        if col in cleaned:
            col = f"{col}_{i}"
        cleaned.append(col)
    return cleaned


def generate_insights_from_llm(df, file_name):
    try:
        sample_data = df.head(10).to_dict(orient="records")
        prompt = f"""
        You are a senior data analyst.
        Generate insights for '{file_name}'.

        Sample rows:
        {json.dumps(sample_data, indent=2)}

        Return ONLY a valid JSON array of strings.
        """

        llm_output = call_llm(prompt).strip()
        llm_output = llm_output.replace("```json", "").replace("```", "").strip()
        pure_json = llm_output[llm_output.find("[") : llm_output.rfind("]") + 1]

        return json.loads(pure_json)

    except Exception as e:
        return [f"[Insight Error] {str(e)}"]


def _make_row_hash(row_values):
    s = "|".join("" if v is None else str(v) for v in row_values)
    return hashlib.md5(s.encode()).hexdigest()


def upload_and_insights_controller():
    try:
        session_id = request.form.get("session_id")
        created_by = request.form.get("created_by")  # THIS IS user_id (NOT email)

        if not session_id or not created_by:
            return build_response(False, "session_id & created_by required", 400)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # --------------------------------------------------------
        # 1️⃣ VALIDATE SESSION (session_id must exist)
        # --------------------------------------------------------
        cursor.execute(
            "SELECT user_id FROM users WHERE session_id=%s LIMIT 1",
            (session_id,)
        )
        session_row = cursor.fetchone()

        if not session_row:
            return build_response(False, "Invalid session_id", 400)

        # --------------------------------------------------------
        # 2️⃣ CREATED_BY MUST MATCH THE session's user_id
        # --------------------------------------------------------
        if session_row["user_id"] != created_by:
            return build_response(False, "Unauthorized: session does not belong to this user", 401)

        # --------------------------------------------------------
        # 3️⃣ FILE VALIDATION
        # --------------------------------------------------------
        files = request.files.getlist("files")
        if not files:
            return build_response(False, "No files uploaded", 400)

        result_info = []

        # --------------------------------------------------------
        # PROCESS EACH FILE
        # --------------------------------------------------------
        for file in files:

            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)

            # -------------------- READ CSV --------------------
            df = pd.read_csv(filepath, dtype=str)
            df = df.drop_duplicates().dropna(how="all")
            df.columns = clean_column_names(df.columns)
            df = df.where(pd.notnull(df), None)

            total_rows = len(df)
            total_columns = len(df.columns)

            # -------------------- TABLE NAME --------------------
            table_name = (
                filename.replace(".csv", "")
                        .replace("-", "_")
                        .replace(" ", "_")
                        .replace(".", "_")
                        .lower()
            )

            # --------------------------------------------------------
            # 4️⃣ CALL SP TO INSERT FILE METADATA
            # --------------------------------------------------------
            cursor.callproc(
                "sp_insert_uploaded_file",
                [session_id, filename, table_name, file_size_mb, "csv",
                 total_rows, total_columns, created_by]
            )

            sp_result = list(cursor.stored_results())[0].fetchone()
            file_id = sp_result["file_id"]
            status_flag = sp_result["status_flag"]

            # --------------------------------------------------------
            # 5️⃣ CREATE TABLE IF NOT EXISTS
            # --------------------------------------------------------
            col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])

            try:
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS `{table_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        {col_defs},
                        row_hash VARCHAR(64),
                        UNIQUE KEY idx_{table_name}_rowhash (row_hash)
                    )
                    """
                )

                cursor.execute(
                    "UPDATE uploaded_files SET table_extraction_status='done' WHERE id=%s",
                    (file_id,)
                )

            except Exception as e:
                cursor.execute(
                    "UPDATE uploaded_files SET table_extraction_status='failed' WHERE id=%s",
                    (file_id,)
                )
                db.commit()
                return build_response(False, f"Table creation failed: {str(e)}", 500)

            # --------------------------------------------------------
            # 6️⃣ ADD row_hash column to df
            # --------------------------------------------------------
            df["row_hash"] = df.apply(lambda r: _make_row_hash(r.values), axis=1)

            # --------------------------------------------------------
            # 7️⃣ FETCH EXISTING ROWS
            # --------------------------------------------------------
            cursor.execute(f"SELECT * FROM `{table_name}`")
            db_existing_rows = cursor.fetchall()

            existing_map = {row["row_hash"]: row for row in db_existing_rows}

            new_rows = 0
            updated_rows = 0

            # --------------------------------------------------------
            # 8️⃣ CHECK NEW/UPDATED ROWS
            # --------------------------------------------------------
            for _, row in df.iterrows():
                rh = row["row_hash"]

                if rh not in existing_map:
                    new_rows += 1
                else:
                    db_row = existing_map[rh]
                    modified = False

                    for col in df.columns:
                        if col != "row_hash" and str(row[col]) != str(db_row.get(col)):
                            modified = True
                            break

                    if modified:
                        updated_rows += 1

            # --------------------------------------------------------
            # 9️⃣ UPSERT (INSERT + UPDATE)
            # --------------------------------------------------------
            columns = df.columns.tolist()
            col_sql = ",".join([f"`{c}`" for c in columns])
            placeholders = ",".join(["%s"] * len(columns))
            update_sql = ", ".join(
                [f"`{c}`=VALUES(`{c}`)" for c in columns if c != "row_hash"]
            )

            upsert_sql = f"""
                INSERT INTO `{table_name}` ({col_sql})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_sql};
            """

            cursor.executemany(upsert_sql, df.values.tolist())

            cursor.execute(
                "UPDATE uploaded_files SET column_extraction_status='done' WHERE id=%s",
                (file_id,)
            )

            # --------------------------------------------------------
            #  🔟 DECIDE MESSAGE FOR USER
            # --------------------------------------------------------
            if new_rows == 0 and updated_rows == 0:
                custom_message = "File already uploaded"
            elif new_rows > 0 and updated_rows == 0:
                custom_message = "New data inserted successfully"
            elif updated_rows > 0 and new_rows == 0:
                custom_message = "File updated successfully"
            else:
                custom_message = "File updated with new & modified rows"

            # --------------------------------------------------------
            # 1️⃣1️⃣ GENERATE INSIGHTS (simple text)
            # --------------------------------------------------------
            try:
                insights = generate_insights_from_llm(df, filename)

                cursor.execute(
                    "UPDATE uploaded_files SET insights=%s, data_insights_status='done' WHERE id=%s",
                    (json.dumps({"insights": insights}), file_id)
                )

            except Exception:
                cursor.execute(
                    "UPDATE uploaded_files SET data_insights_status='failed' WHERE id=%s",
                    (file_id,)
                )

            db.commit()

            # --------------------------------------------------------
            # 1️⃣2️⃣ ADD FINAL RESPONSE DATA
            # --------------------------------------------------------
            result_info.append({
                "file_id": file_id,
                "file_name": filename,
                "table_name": table_name,
                "total_rows": total_rows,
                "total_columns": total_columns,
                "file_size_mb": file_size_mb,
                "message": custom_message,
                "status_flag": status_flag,
            })

        return build_response(True, "File processed", 200, result_info)

    except Exception as e:
        return build_response(False, "Server Error", 500, {"error": str(e)})

