# import pandas as pd
# import json
# import uuid
# from flask import request
# from database.dbConnection import get_db_connection
# from helper.helperFunctions import build_response, get_allowed_extensions,format_file_size,generate_unique_id, chunk_list 


# def upload_files_count_controller():
#     try:
#         session_id = request.form.get("session_id")
#         session_name = request.form.get("session_name")
#         files = request.files.getlist("files")

#         created_by = "system"   # backend generated

#         if not session_id or session_id.strip() == "":
#            return build_response(False, "Session id is required", 400)
        
#         if not session_name or session_name.strip() == "":
#             return build_response(False, "Session name is required", 400)

#         if not files:
#             return build_response(False, "No files uploaded", 400)
        
#         allowed_ext = get_allowed_extensions()
#         final_response = []

#         for file in files:

#             file_name = file.filename
#             ext = file_name.rsplit(".", 1)[-1].lower()

#         # --------- ADD THIS ---------
#             file_size_bytes = len(file.read())   # get size in bytes
#             file.seek(0)                         # reset pointer for pandas to read
#             file_size_str = format_file_size(file_size_bytes)
#             # ----------------------------


#             result = {
#                 "file name": file_name,
#                 "file type": ext,
#                 "total files": len(files),
#                 "upload_status": "Pending",
#                 "table_extract_status": "Pending",
#                 "column_extract_status": "Pending",
#                 "data_mapping_status": "Pending",
#                 "relation_mapping_status": "Pending",
#                 "total sheets": 0,
#                 "total column": 0,
#                 "table name": ""
#             }

#             if ext not in allowed_ext:
#                 result["upload_status"] = "Failed"
#                 final_response.append(result)
#                 continue

#             file_data_chunks = []   # final chunk list
#             total_rows = 0

#             try:

#                 # ========== 1) EXCEL ==========
#                 if ext in ("xlsx", "xls"):

#                     excel = pd.ExcelFile(file)
#                     sheets = excel.sheet_names

#                     result["total sheets"] = len(sheets)
#                     result["table name"] = ",".join(sheets)

#                     total_columns = 0

#                     for sheet in sheets:
#                         df = excel.parse(sheet)
#                         rows = json.loads(df.to_json(orient="records"))

#                         total_columns += len(df.columns)
#                         total_rows += len(df)

#                         # Split into chunks
#                         for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):

#                             chunk_json = {
#                                 "data": {
#                                     sheet: chunk
#                                 }
#                             }

#                             file_data_chunks.append({
#                                 "unique_id": f"{generate_unique_id()}_{sheet}_{index}",
#                                 "row_data": chunk_json
#                             })

#                     result["total column"] = total_columns
#                     result["upload_status"] = "Done"
#                     result["table_extract_status"] = "Done"
#                     result["column_extract_status"] = "Done"

#                 # ========== 2) CSV ==========
#                 elif ext == "csv":

#                     df = pd.read_csv(file)
#                     rows = json.loads(df.to_json(orient="records"))

#                     total_rows = len(df)
#                     result["total sheets"] = 1
#                     result["table name"] = "Sheet1"
#                     result["total column"] = len(df.columns)

#                     for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):
#                         chunk_json = {"data": {"Sheet1": chunk}}

#                         file_data_chunks.append({
#                             "unique_id": f"{generate_unique_id()}_Sheet1_{index}",
#                             "row_data": chunk_json
#                         })

#                     result["upload_status"] = "Done"
#                     result["table_extract_status"] = "Done"
#                     result["column_extract_status"] = "Done"

#                 # ========== 3) XML ==========
#                 elif ext == "xml":

#                     df = pd.read_xml(file)
#                     rows = json.loads(df.to_json(orient="records"))

#                     total_rows = len(df)
#                     result["total sheets"] = 1
#                     result["table name"] = "XMLData"
#                     result["total column"] = len(df.columns)

#                     for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):
#                         chunk_json = {"data": {"XMLData": chunk}}

#                         file_data_chunks.append({
#                             "unique_id": f"{generate_unique_id()}_XMLData_{index}",
#                             "row_data": chunk_json
#                         })

#                     result["upload_status"] = "Done"
#                     result["table_extract_status"] = "Done"
#                     result["column_extract_status"] = "Done"

#                 # ========== 4) SQL / DUMP ==========
#                 elif ext in ("sql", "dump"):

#                     file_data_chunks.append({
#                         "unique_id": generate_unique_id(),
#                         "row_data": {"data": {}}
#                     })

#                     result["total sheets"] = 0
#                     result["total column"] = 0
#                     result["table name"] = "N/A"
#                     total_rows = 0

#                     result["upload_status"] = "Done"
#                     result["table_extract_status"] = "Pending"
#                     result["column_extract_status"] = "Pending"

#             except Exception as e:
#                 result["upload_status"] = "Failed"
#                 result["error"] = str(e)
#                 final_response.append(result)
#                 continue

#             # ========== CALL STORED PROCEDURE FOR EACH CHUNK ==========
#             try:
#                 conn = get_db_connection()
#                 cursor = conn.cursor()
#                 print(len((
#                         session_id, session_name, file_name, ext,
#                         result["upload_status"], result["table_extract_status"],
#                         result["column_extract_status"], result["data_mapping_status"],
#                         total_rows, result["total column"],
#                         result["table name"], result["total sheets"],
#                         created_by, json.dumps([chunk])
#                     )))


#                 for chunk in file_data_chunks:

#                     cursor.execute("""
#                         CALL sp_upload_file_count(
#                             %s,%s,%s,%s,%s,%s,%s,
#                             %s,%s,%s,%s,%s,%s,%s,%s
#                         )
#                     """, (
#                         session_id,
#                         session_name,
#                         file_name,
#                         ext,
#                         result["upload_status"],
#                         result["table_extract_status"],
#                         result["column_extract_status"],
#                         result["data_mapping_status"],
#                         total_rows,
#                         result["total column"],
#                         result["table name"],
#                         result["total sheets"],
#                         created_by,
#                         file_size_str,
#                         json.dumps([chunk])  # single-chunk JSON array
#                     ))
#                 conn.commit()
#                 cursor.close()
#                 conn.close()

#             except Exception as db_error:
#                 result["upload_status"] = "Failed"
#                 result["error"] = str(db_error)

#             final_response.append(result)

#         return build_response(True, "Upload completed", 200, data=final_response)

#     except Exception as e:
#         return build_response(False, f"Error: {str(e)}", 500)


import pandas as pd
import json
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import (
    build_response,
    get_allowed_extensions,
    format_file_size,
    generate_unique_id,
    chunk_list
)


def upload_files_count_controller():
    try:
        # ---------------------- VALIDATION BLOCK ---------------------- #
        session_id = request.form.get("session_id")
        session_name = request.form.get("session_name")
        files = request.files.getlist("files")
        created_by = "system"

        required_messages = {
            "session_id": "Session id is required",
            "session_name": "Session name is required",
            "files": "At least 1 file is required"
        }

        errors = []

        # CASE 1: All missing
        if (not session_id and not session_name and (not files or len(files) == 0)):
            all_errors = ", ".join(required_messages.values())
            return build_response(False, all_errors, 400)

        # CASE 2: Individual validation
        if not session_id or session_id.strip() == "":
            errors.append(required_messages["session_id"])

        if not session_name or session_name.strip() == "":
            errors.append(required_messages["session_name"])

        if not files or len(files) == 0:
            errors.append(required_messages["files"])

        # If any validation failed
        if errors:
            return build_response(False, ", ".join(errors), 400)

        # ------------------ END VALIDATION BLOCK ---------------------- #

        allowed_ext = get_allowed_extensions()
        final_response = []

        # ---------------------- PROCESS EACH FILE ---------------------- #
        for file in files:

            file_name = file.filename
            ext = file_name.rsplit(".", 1)[-1].lower()

            # Calculate file size
            file_size_bytes = len(file.read())
            file.seek(0)
            file_size_str = format_file_size(file_size_bytes)

            result = {
                "file name": file_name,
                "file type": ext,
                "total files": len(files),
                "upload_status": "Pending",
                "table_extract_status": "Pending",
                "column_extract_status": "Pending",
                "data_mapping_status": "Pending",
                "relation_mapping_status": "Pending",
                "total sheets": 0,
                "total column": 0,
                "table name": ""
            }

            # Extension validation
            if ext not in allowed_ext:
                result["upload_status"] = "Failed"
                final_response.append(result)
                continue

            file_data_chunks = []
            total_rows = 0

            # ------------------- FILE TYPE PROCESSING ------------------- #
            try:
                # 1) Excel
                if ext in ("xlsx", "xls"):
                    excel = pd.ExcelFile(file)
                    sheets = excel.sheet_names

                    result["total sheets"] = len(sheets)
                    result["table name"] = ",".join(sheets)

                    total_columns = 0

                    for sheet in sheets:
                        df = excel.parse(sheet)
                        rows = json.loads(df.to_json(orient="records"))

                        total_rows += len(df)
                        total_columns += len(df.columns)

                        for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):
                            file_data_chunks.append({
                                "unique_id": f"{generate_unique_id()}_{sheet}_{index}",
                                "row_data": {"data": {sheet: chunk}}
                            })

                    result["total column"] = total_columns
                    result["upload_status"] = "Done"
                    result["table_extract_status"] = "Done"
                    result["column_extract_status"] = "Done"

                # 2) CSV
                elif ext == "csv":
                    df = pd.read_csv(file)
                    rows = json.loads(df.to_json(orient="records"))

                    total_rows = len(df)
                    result["total sheets"] = 1
                    result["table name"] = "Sheet1"
                    result["total column"] = len(df.columns)

                    for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):
                        file_data_chunks.append({
                            "unique_id": f"{generate_unique_id()}_Sheet1_{index}",
                            "row_data": {"data": {"Sheet1": chunk}}
                        })

                    result["upload_status"] = "Done"
                    result["table_extract_status"] = "Done"
                    result["column_extract_status"] = "Done"

                # 3) XML
                elif ext == "xml":
                    df = pd.read_xml(file)
                    rows = json.loads(df.to_json(orient="records"))

                    total_rows = len(df)
                    result["total sheets"] = 1
                    result["table name"] = "XMLData"
                    result["total column"] = len(df.columns)

                    for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):
                        file_data_chunks.append({
                            "unique_id": f"{generate_unique_id()}_XMLData_{index}",
                            "row_data": {"data": {"XMLData": chunk}}
                        })

                    result["upload_status"] = "Done"
                    result["table_extract_status"] = "Done"
                    result["column_extract_status"] = "Done"

                # 4) SQL Dump
                elif ext in ("sql", "dump"):
                    file_data_chunks.append({
                        "unique_id": generate_unique_id(),
                        "row_data": {"data": {}}
                    })

                    result["table name"] = "N/A"
                    result["total sheets"] = 0
                    result["total column"] = 0
                    total_rows = 0

                    result["upload_status"] = "Done"

            except Exception as e:
                result["upload_status"] = "Failed"
                result["error"] = str(e)
                final_response.append(result)
                continue

            # ------------------- INSERT INTO DB (SP CALL) ------------------- #
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                for chunk in file_data_chunks:
                    cursor.execute("""
                        CALL sp_upload_file_count(
                            %s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,%s,%s
                        )
                    """, (
                        session_id,
                        session_name,
                        file_name,
                        ext,
                        result["upload_status"],
                        result["table_extract_status"],
                        result["column_extract_status"],
                        result["data_mapping_status"],
                        total_rows,
                        result["total column"],
                        result["table name"],
                        result["total sheets"],
                        created_by,
                        file_size_str,
                        json.dumps([chunk])
                    ))

                conn.commit()
                cursor.close()
                conn.close()

            except Exception as db_error:
                result["upload_status"] = "Failed"
                result["error"] = str(db_error)

            final_response.append(result)

        # ------------------ FINAL API STATUS HANDLING ------------------ #

        any_failed = any(item.get("upload_status") == "Failed" for item in final_response)

        if any_failed:
            return build_response(False, "One or more files failed to upload", 400, data=final_response)

        return build_response(True, "Upload completed", 200, data=final_response)

    except Exception as e:
        return build_response(False, f"Error: {str(e)}", 500)
