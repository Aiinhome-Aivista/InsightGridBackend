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
        # ---------------------- MAIN INPUTS ---------------------- #
        session_id = request.form.get("session_id")
        session_name = request.form.get("session_name")
        files = request.files.getlist("files")
        created_by = "system"

        # Basic validation (session_id & session_name only)
        if not session_id or not session_name:
            return build_response(False, "Session ID & Session Name are required", 400)

        # Allowed extensions from .env
        allowed_ext = get_allowed_extensions()
        final_response = []

        # ---------------------- PROCESS EACH FILE ---------------------- #
        for file in files:

            # 🛑 Skip empty file object
            if file.filename == "" or file.filename is None:
                final_response.append({
                    "file name": "",
                    "file type": "",
                    "upload_status": "Pending",
                    "table_extract_status": "Pending",
                    "column_extract_status": "Pending",
                    "data_mapping_status": "Pending",
                    "relation_mapping_status": "Pending",
                    "total sheets": 0,
                    "total column": 0,
                    "table name": "",
                    "error": "Empty file received"
                })
                continue

            file_name = file.filename
            ext = file_name.rsplit(".", 1)[-1].lower()

            # File size calculation
            file_size_bytes = len(file.read())
            file.seek(0)
            file_size_str = format_file_size(file_size_bytes)

            # Default response object for this file
            result = {
                "file name": file_name,
                "file type": ext,
                "upload_status": "Pending",
                "table_extract_status": "Pending",
                "column_extract_status": "Pending",
                "data_mapping_status": "Pending",
                "relation_mapping_status": "Pending",
                "total files": len(files),
                "total sheets": 0,
                "total column": 0,
                "table name": "",
                "column_names": {}   # new field to store sheet-wise column names
            }

            # 🛑 Invalid extension → mark failed (but overall API OK)
            if ext not in allowed_ext:
                result["error"] = f"Extension .{ext} is not allowed"
                final_response.append(result)
                continue

            file_data_chunks = []
            total_rows = 0

            # ------------------- FILE TYPE PROCESSING ------------------- #
            try:
                # Excel
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
                         # Store column names for this sheet
                        result["column_names"][sheet] = list(df.columns)
                        result["column_extract_status"] = "Done"
                        result["table_extract_status"] = "Done"
                                       
                        for index, chunk in enumerate(chunk_list(rows, 1000)):
                            file_data_chunks.append({
                                "unique_id": f"{generate_unique_id()}_{sheet}_{index}",
                                "row_data": {"data": {sheet: chunk}}
                            })

                    result["total column"] = total_columns

                # CSV
                elif ext == "csv":
                    df = pd.read_csv(file)
                    rows = json.loads(df.to_json(orient="records"))
                    total_rows = len(df)

                    result["total sheets"] = 1
                    result["table name"] = "Sheet1"
                    result["total column"] = len(df.columns)
                    result["column_names"]["Sheet1"] = list(df.columns)  
                    result["column_extract_status"] = "Done"
                    result["table_extract_status"] = "Done"

                    for index, chunk in enumerate(chunk_list(rows, 1000)):
                        file_data_chunks.append({
                            "unique_id": f"{generate_unique_id()}_Sheet1_{index}",
                            "row_data": {"data": {"Sheet1": chunk}}
                        })

                # XML
                elif ext == "xml":
                    df = pd.read_xml(file)
                    rows = json.loads(df.to_json(orient="records"))
                    total_rows = len(df)

                    result["total sheets"] = 1
                    result["table name"] = "XMLData"
                    result["total column"] = len(df.columns)
                    result["column_names"]["XMLData"] = list(df.columns)   # store column names
                    result["column_extract_status"] = "Done"
                    result["table_extract_status"] = "Done"

                    for index, chunk in enumerate(chunk_list(rows, 1000)):
                        file_data_chunks.append({
                            "unique_id": f"{generate_unique_id()}_XMLData_{index}",
                            "row_data": {"data": {"XMLData": chunk}}
                        })

                # SQL Dump
                elif ext in ("sql", "dump"):
                    file_data_chunks.append({
                        "unique_id": generate_unique_id(),
                        "row_data": {"data": {}}
                    })

                    result["total sheets"] = 0
                    result["total column"] = 0
                    result["table name"] = "N/A"

            except Exception as e:
                # Mark only this file as failed
                result["error"] = f"Processing error: {str(e)}"
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
                            %s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                    """, (
                        session_id,
                        session_name,
                        file_name,
                        ext,
                        result["upload_status"],        # ALWAYS PENDING
                        result["table_extract_status"],
                        result["column_extract_status"],
                        result["data_mapping_status"],
                        total_rows,
                        result["total column"],
                        result["table name"],
                        result["total sheets"],
                        created_by,
                        file_size_str,
                        json.dumps(result["column_names"]),
                        json.dumps([chunk]),
                    ))

                conn.commit()
                cursor.close()
                conn.close()

            except Exception as db_error:
                result["error"] = f"Database error: {str(db_error)}"

            final_response.append(result)

        # ------------------ ALWAYS RETURN 200 ------------------ #
        return build_response(True, "Upload completed", 200, data=final_response)

    except Exception as e:
        return build_response(False, f"Unexpected Error: {str(e)}", 500)
