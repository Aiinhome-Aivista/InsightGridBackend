# import os
# import hashlib
# import pandas as pd
# from flask import request, jsonify
# from werkzeug.utils import secure_filename
# from utils.helper import get_upload_folder, allowed_file
# from database.dbConnection import get_db_connection

# UPLOAD_FOLDER = get_upload_folder()

# def upload_files_controller():
#     try:
#         # Step 0: Validate request
#         errors = {}
#         file_name = request.form.get("file_name")
#         files = request.files.getlist("files")
#         session_id = request.form.get("session_id", "123456")
#         created_by = request.form.get("created_by", "admin")

#         if not file_name:
#             errors["file_name"] = "file_name is required"
#         if not files or len(files) == 0:
#             errors["files"] = "No files uploaded"
#         if errors:
#             return jsonify({
#                 "status": "failed",
#                 "statusCode": 400,
#                 "message": "Validation failed",
#                 "data": errors
#             }), 400

#         # Step 1: Setup
#         saved_files = []
#         response_data = []
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         if not os.path.exists(UPLOAD_FOLDER):
#             os.makedirs(UPLOAD_FOLDER)

#         # Step 2: Process each file
#         for file in files:
#             file_status = {"file_name": file.filename}
#             safe_full_name = secure_filename(file.filename)
#             file_name_only = safe_full_name.rsplit(".", 1)[0]
#             ext = safe_full_name.rsplit(".", 1)[1].lower()
#             file_path = os.path.join(UPLOAD_FOLDER, safe_full_name)

#             # Validate file type
#             if not allowed_file(file.filename):
#                 file_status.update({
#                     "upload_status": "failed",
#                     "errors": {"file_type": f"File type not allowed: {file.filename}"}
#                 })
#                 response_data.append(file_status)
#                 continue

#             # Save file
#             try:
#                 file.save(file_path)
#                 upload_status = "done"
#                 saved_files.append(file_path)
#             except Exception as e:
#                 file_status.update({
#                     "upload_status": "failed",
#                     "errors": {"upload_error": str(e)}
#                 })
#                 response_data.append(file_status)
#                 continue

#            # Extract data and metadata
#             try:
#                 file_json = {}
#                 if ext == "csv":
#                     df = pd.read_csv(file_path)
#                     total_rows, total_columns = df.shape
#                     total_sheets = 1
#                     table_names = "sheet1"
#                     file_json["sheet1"] = df.to_dict(orient="records")

#                 elif ext in ["xlsx", "xls"]:
#                     engine = "openpyxl" if ext == "xlsx" else "xlrd"
#                     all_sheets = pd.read_excel(file_path, sheet_name=None, engine=engine)
#                     total_sheets = len(all_sheets)
#                     table_names = ",".join(all_sheets.keys())
#                     total_rows = 0
#                     total_columns = 0

#                     # Combine all sheets
#                     for sheet_name, sheet_df in all_sheets.items():
#                         total_rows += sheet_df.shape[0]       # sum rows
#                         total_columns += sheet_df.shape[1]    # sum columns across sheets
#                         file_json[sheet_name] = sheet_df.to_dict(orient="records")

#                 # Convert combined JSON
#                 row_json = pd.Series({"data": file_json}).to_json()
#                 # Mark all status as done
#                 table_extract_status = column_extract_status = data_mapping_status = upload_status = "done"

#             except Exception as e:
#                 file_status.update({
#                     "upload_status": "failed",
#                     "table_extract_status": "failed",
#                     "errors": {"read_error": str(e)}
#                 })
#                 response_data.append(file_status)
#                 continue



#             # Insert metadata
#             cursor.execute("""
#                 INSERT INTO file_master
#                     (file_name, file_type, upload_status, table_extract_status,
#                      column_extract_status, data_mapping_status, total_rows, total_columns,
#                      table_names, total_sheets, created_by, session_id)
#                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#                 ON DUPLICATE KEY UPDATE
#                     file_type=VALUES(file_type),
#                     upload_status=VALUES(upload_status),
#                     table_extract_status=VALUES(table_extract_status),
#                     column_extract_status=VALUES(column_extract_status),
#                     data_mapping_status=VALUES(data_mapping_status),
#                     total_rows=VALUES(total_rows),
#                     total_columns=VALUES(total_columns),
#                     table_names=VALUES(table_names),
#                     total_sheets=VALUES(total_sheets),
#                     updated_at=CURRENT_TIMESTAMP,
#                     created_by=VALUES(created_by)
#             """, (file_name_only, ext, upload_status, table_extract_status,
#                   column_extract_status, data_mapping_status, total_rows, total_columns,
#                   table_names, total_sheets, created_by, session_id))
#             conn.commit()

#             # Insert row-level data as JSON
#             unique_hash = hashlib.md5((file_name_only + session_id).encode('utf-8')).hexdigest()
#             cursor.execute("""
#                 INSERT INTO file_data (session_id, file_name, unique_id, row_data)
#                 VALUES (%s,%s,%s,%s)
#                 ON DUPLICATE KEY UPDATE
#                     row_data = VALUES(row_data),
#                     updated_at = CURRENT_TIMESTAMP
#             """, (session_id, file_name_only, unique_hash, row_json))
#             conn.commit()

#             file_status.update({
#                 "upload_status": upload_status,
#                 "table_extract_status": table_extract_status,
#                 "column_extract_status": column_extract_status,
#                 "data_mapping_status": data_mapping_status
#             })
#             response_data.append(file_status)

#         cursor.close()
#         conn.close()

#         # Final response
#         if all("errors" not in f for f in response_data):
#             return jsonify({
#                 "status": "success",
#                 "statusCode": 200,
#                 "message": "Files uploaded successfully",
#                 "data": {"file_name": file_name, "uploaded_files": saved_files}
#             }), 200

#         return jsonify({
#             "status": "failed",
#             "statusCode": 400,
#             "message": "Some files failed",
#             "data": response_data
#         }), 400

#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "statusCode": 500,
#             "message": "File upload failed",
#             "error": str(e),
#             "data": []
#         }), 500



import os
import hashlib
import pandas as pd
from flask import request, jsonify
from werkzeug.utils import secure_filename
from utils.helper import get_upload_folder, allowed_file
from database.dbConnection import get_db_connection

UPLOAD_FOLDER = get_upload_folder()

def upload_files_controller():
    try:
        # Step 0: Validate request
        errors = {}
        file_name = request.form.get("file_name")
        files = request.files.getlist("files")
        session_id = request.form.get("session_id", "123456")
        created_by = request.form.get("created_by", "admin")

        if not file_name:
            errors["file_name"] = "file_name is required"
        if not files or len(files) == 0:
            errors["files"] = "No files uploaded"
        if errors:
            return jsonify({
                "status": "failed",
                "statusCode": 400,
                "message": "Validation failed",
                "data": errors
            }), 400

        # Step 1: Setup
        saved_files = []
        response_data = []
        conn = get_db_connection()
        cursor = conn.cursor()
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # Step 2: Process each file
        for file in files:
            file_status = {"file_name": file.filename}
            safe_full_name = secure_filename(file.filename)
            file_name_only = safe_full_name.rsplit(".", 1)[0]
            ext = safe_full_name.rsplit(".", 1)[1].lower()
            file_path = os.path.join(UPLOAD_FOLDER, safe_full_name)

            # Validate file type
            if not allowed_file(file.filename):
                file_status.update({
                    "upload_status": "failed",
                    "errors": {"file_type": f"File type not allowed: {file.filename}"}
                })
                response_data.append(file_status)
                continue

            # Save file
            try:
                file.save(file_path)
                upload_status = "done"
                saved_files.append(file_path)
            except Exception as e:
                file_status.update({
                    "upload_status": "failed",
                    "errors": {"upload_error": str(e)}
                })
                response_data.append(file_status)
                continue

            # Extract data and metadata
            try:
                total_rows = 0
                total_columns = 0
                file_json = {}

                if ext == "csv":
                    df = pd.read_csv(file_path)
                    total_rows, total_columns = df.shape
                    total_sheets = 1
                    table_names = "sheet1"
                    sheet_json = pd.Series({"data": {"sheet1": df.to_dict(orient="records")}}).to_json()
                    
                    # Insert single CSV sheet into file_data
                    unique_hash = hashlib.md5((file_name_only + session_id).encode('utf-8')).hexdigest()
                    cursor.execute("""
                        INSERT INTO file_data (session_id, file_name, unique_id, row_data)
                        VALUES (%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                            row_data = VALUES(row_data),
                            updated_at = CURRENT_TIMESTAMP
                    """, (session_id, file_name_only, unique_hash, sheet_json))
                    conn.commit()

                elif ext in ["xlsx", "xls"]:
                    engine = "openpyxl" if ext == "xlsx" else "xlrd"
                    all_sheets = pd.read_excel(file_path, sheet_name=None, engine=engine)
                    total_sheets = len(all_sheets)
                    table_names = ",".join(all_sheets.keys())

                    for sheet_name, sheet_df in all_sheets.items():
                        sheet_rows, sheet_cols = sheet_df.shape
                        total_rows += sheet_rows
                        total_columns += sheet_cols

                        sheet_json = pd.Series({"data": {sheet_name: sheet_df.to_dict(orient="records")}}).to_json()
                        unique_hash = hashlib.md5((file_name_only + sheet_name + session_id).encode('utf-8')).hexdigest()

                        # Insert sheet-wise JSON
                        cursor.execute("""
                            INSERT INTO file_data (session_id, file_name, unique_id, row_data)
                            VALUES (%s,%s,%s,%s)
                            ON DUPLICATE KEY UPDATE
                                row_data = VALUES(row_data),
                                updated_at = CURRENT_TIMESTAMP
                        """, (session_id, file_name_only, unique_hash, sheet_json))
                        conn.commit()

                # Mark all status as done
                table_extract_status = column_extract_status = data_mapping_status = upload_status = "done"

            except Exception as e:
                file_status.update({
                    "upload_status": "failed",
                    "table_extract_status": "failed",
                    "errors": {"read_error": str(e)}
                })
                response_data.append(file_status)
                continue



            # ---- CLEANED DATA INSERT AFTER RAW INSERT ----
            try:
                # For CSV
                if ext == "csv":
                    cleaned_df = df.copy()
                    cleaned_df.dropna(how="all", inplace=True)
                    cleaned_df.drop_duplicates(inplace=True)
                    cleaned_df = cleaned_df.apply(pd.to_numeric, errors='ignore')

                    clean_rows, clean_cols = cleaned_df.shape
                    sheet_name = "sheet1"
                    cleaned_json = pd.Series({"data": {sheet_name: cleaned_df.to_dict(orient="records")}}).to_json()
                    clean_unique_hash = hashlib.md5((file_name_only + sheet_name + session_id + "_clean").encode('utf-8')).hexdigest()

                    cursor.execute("""
                        INSERT INTO file_data_cleaned
                            (session_id, file_name, sheet_name, unique_id, cleaned_rows, cleaned_columns, row_data)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (session_id, file_name_only, sheet_name, clean_unique_hash, clean_rows, clean_cols, cleaned_json))
                    conn.commit()

                # For Excel
                elif ext in ["xlsx", "xls"]:
                    for sheet_name, sheet_df in all_sheets.items():
                        cleaned_df = sheet_df.copy()
                        cleaned_df.dropna(how="all", inplace=True)
                        cleaned_df.drop_duplicates(inplace=True)
                        cleaned_df = cleaned_df.apply(pd.to_numeric, errors='ignore')

                        clean_rows, clean_cols = cleaned_df.shape
                        cleaned_json = pd.Series({"data": {sheet_name: cleaned_df.to_dict(orient="records")}}).to_json()
                        clean_unique_hash = hashlib.md5((file_name_only + sheet_name + session_id + "_clean").encode('utf-8')).hexdigest()

                        cursor.execute("""
                            INSERT INTO file_data_cleaned
                                (session_id, file_name, sheet_name, unique_id, cleaned_rows, cleaned_columns, row_data)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (session_id, file_name_only, sheet_name, clean_unique_hash, clean_rows, clean_cols, cleaned_json))
                        conn.commit()

            except Exception as e:
                print("Cleaned data insert error:", str(e))



            # Insert metadata into file_master
            cursor.execute("""
                INSERT INTO file_master
                    (file_name, file_type, upload_status, table_extract_status,
                     column_extract_status, data_mapping_status, total_rows, total_columns,
                     table_names, total_sheets, created_by, session_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    file_type=VALUES(file_type),
                    upload_status=VALUES(upload_status),
                    table_extract_status=VALUES(table_extract_status),
                    column_extract_status=VALUES(column_extract_status),
                    data_mapping_status=VALUES(data_mapping_status),
                    total_rows=VALUES(total_rows),
                    total_columns=VALUES(total_columns),
                    table_names=VALUES(table_names),
                    total_sheets=VALUES(total_sheets),
                    updated_at=CURRENT_TIMESTAMP,
                    created_by=VALUES(created_by)
            """, (file_name_only, ext, upload_status, table_extract_status,
                  column_extract_status, data_mapping_status, total_rows, total_columns,
                  table_names, total_sheets, created_by, session_id))
            conn.commit()

            file_status.update({
                "upload_status": upload_status,
                "table_extract_status": table_extract_status,
                "column_extract_status": column_extract_status,
                "data_mapping_status": data_mapping_status
            })
            response_data.append(file_status)

        cursor.close()
        conn.close()

        # Final response
        if all("errors" not in f for f in response_data):
            return jsonify({
                "status": "success",
                "statusCode": 200,
                "message": "Files uploaded successfully",
                "data": {"file_name": file_name, "uploaded_files": saved_files}
            }), 200

        return jsonify({
            "status": "failed",
            "statusCode": 400,
            "message": "Some files failed",
            "data": response_data
        }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "statusCode": 500,
            "message": "File upload failed",
            "error": str(e),
            "data": []
        }), 500

