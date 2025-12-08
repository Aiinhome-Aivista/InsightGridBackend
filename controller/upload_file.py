# import os
# import pandas as pd
# import mysql.connector
# from flask import request
# from werkzeug.utils import secure_filename
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response


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

#             # ---------------------- READ CSV SAFELY ----------------------
#             df = pd.read_csv(filepath, encoding='utf-8', dtype=str)
#             df = df.drop_duplicates()
#             df = df.dropna(how="all")

# # ---------------------- CLEAN COLUMN NAMES ----------------------
#             df.columns = clean_column_names(df.columns)

# # ---------------------- CLEAN CELL VALUES (THIS FIXES YOUR ERROR) ----------------------
#             df = df.where(pd.notnull(df), None) 

#             total_rows = len(df)
#             total_columns = len(df.columns)

#             # ---------------------- FIX TABLE NAME ----------------------
#             table_name = (
#                 filename.replace(".csv", "")
#                         .replace("-", "_")
#                         .replace(" ", "_")
#                         .replace(".", "_")
#                         .lower()
#             )

#             # ---------------------- CREATE TABLE ----------------------
#             col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])

#             create_sql = f"""
#                 CREATE TABLE IF NOT EXISTS `{table_name}` (
#                     id INT AUTO_INCREMENT PRIMARY KEY,
#                     {col_defs}
#                 )
#             """
#             cursor.execute(create_sql)

#             # ---------------------- INSERT DATA ----------------------
#             if total_rows > 0:
#                 placeholders = ", ".join(["%s"] * len(df.columns))

#                 insert_sql = f"""
#                     INSERT INTO `{table_name}` ({','.join([f'`{c}`' for c in df.columns])})
#                     VALUES ({placeholders})
#                 """

#                 cursor.executemany(insert_sql, df.values.tolist())

#             # ---------------------- SAVE METADATA (Stored Procedure) ----------------------
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

#             file_id = None
#             for row in cursor.stored_results():
#                 file_id = row.fetchone()["file_id"]

#             # ---------------------- INSERT PROCESSING STEPS ----------------------
#             cursor.callproc("sp_insert_file_steps", [file_id])

#             db.commit()

#             # ---------------------- RESPONSE ----------------------
#             result_info.append(
#                 {
#                     "file_id": file_id,
#                     "file_name": filename,
#                     "table_name": table_name,
#                     "total_rows": total_rows,
#                     "total_columns": total_columns,
#                     "file_size_mb": file_size_mb,
#                 }
#             )

#         return build_response(True, "Files uploaded successfully", 200, result_info)

#     except Exception as e:
#         return build_response(
#             False,
#             "Server Error",
#             500,
#             {"error": str(e)},
#         )




import os
import pandas as pd
from flask import request
from werkzeug.utils import secure_filename
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response


UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def clean_column_names(columns):
    columns = columns.fillna("col")
    cleaned = []

    for i, col in enumerate(columns):
        col = str(col).strip()
        if col == "" or col.lower() == "nan" or col == "col":
            col = f"col_{i}"

        col = (
            col.replace(" ", "_")
               .replace("-", "_")
               .replace(".", "_")
               .replace("/", "_")
               .replace("\\", "_")
        )

        if col in cleaned:
            col = f"{col}_{i}"

        cleaned.append(col)

    return cleaned


def upload_and_insights_controller():
    try:
        session_id = request.form.get("session_id")
        created_by = request.form.get("created_by")

        if not session_id or not created_by:
            return build_response(False, "session_id & created_by required", 400)

        files = request.files.getlist("files")
        if not files:
            return build_response(False, "No files uploaded", 400)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        result_info = []

        for file in files:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)

            # ------------------- READ CSV -------------------
            df = pd.read_csv(filepath, encoding='utf-8', dtype=str)
            df = df.drop_duplicates().dropna(how="all")

            # ------------------- CLEAN COLUMNS -------------------
            df.columns = clean_column_names(df.columns)

            # Convert NaN values to NULL for MySQL
            df = df.where(pd.notnull(df), None)

            total_rows = len(df)
            total_columns = len(df.columns)

            # ------------------- TABLE NAME -------------------
            table_name = (
                filename.replace(".csv", "")
                        .replace("-", "_")
                        .replace(" ", "_")
                        .replace(".", "_")
                        .lower()
            )

            # ------------------- SAVE METADATA (SP CALL) -------------------
            cursor.callproc(
                "sp_insert_uploaded_file",
                [
                    session_id,
                    filename,
                    table_name,
                    file_size_mb,
                    "csv",
                    total_rows,
                    total_columns,
                    created_by,
                ],
            )

            # fetch file_id
            result = list(cursor.stored_results())[0].fetchone()
            file_id = result["file_id"]

            # ------------------- STEP 1: Table Extraction -------------------
            try:
                col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])
                create_sql = f"""
                    CREATE TABLE IF NOT EXISTS `{table_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        {col_defs}
                    )
                """
                cursor.execute(create_sql)

                # Mark table extraction = done
                cursor.execute(
                    "UPDATE uploaded_files SET table_extraction_status='done' WHERE id=%s",
                    (file_id,)
                )

            except Exception:
                cursor.execute(
                    "UPDATE uploaded_files SET table_extraction_status='failed' WHERE id=%s",
                    (file_id,)
                )
                db.commit()
                continue  # move to next file

            # ------------------- STEP 2: Column Data Insertion -------------------
            try:
                if total_rows > 0:
                    placeholders = ", ".join(["%s"] * len(df.columns))
                    insert_sql = f"""
                        INSERT INTO `{table_name}` ({','.join([f'`{c}`' for c in df.columns])})
                        VALUES ({placeholders})
                    """
                    cursor.executemany(insert_sql, df.values.tolist())

                # Mark column extraction = done
                cursor.execute(
                    "UPDATE uploaded_files SET column_extraction_status='done' WHERE id=%s",
                    (file_id,)
                )

            except Exception:
                cursor.execute(
                    "UPDATE uploaded_files SET column_extraction_status='failed' WHERE id=%s",
                    (file_id,)
                )

            # ------------------- INSERT PROCESSING STEPS -------------------
            cursor.callproc("sp_insert_file_steps", [file_id])

            db.commit()

            # Response object
            result_info.append({
                "file_id": file_id,
                "file_name": filename,
                "table_name": table_name,
                "total_rows": total_rows,
                "total_columns": total_columns,
                "file_size_mb": file_size_mb,
            })

        return build_response(True, "Files uploaded successfully", 200, result_info)

    except Exception as e:
        return build_response(False, "Server Error", 500, {"error": str(e)})