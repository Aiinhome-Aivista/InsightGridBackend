import pandas as pd
import json
import uuid
from flask import request
from database.dbConnection import get_db_connection
from helper.helperFunctions import build_response, get_allowed_extensions


def generate_unique_id():
    return uuid.uuid4().hex


def chunk_list(data, chunk_size=1000):
    """Yield chunks of list."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def upload_files_count_controller():
    try:
        session_id = request.form.get("session_id")
        session_name = request.form.get("session_name")
        files = request.files.getlist("files")

        created_by = "Admin"   # backend generated

        if not session_id:
            return build_response(False, "session_id is required", 400)

        if not files:
            return build_response(False, "No files uploaded", 400)

        allowed_ext = get_allowed_extensions()
        final_response = []

        for file in files:

            file_name = file.filename
            ext = file_name.rsplit(".", 1)[-1].lower()
             # ========= FILE SIZE (in bytes) =========
            file.seek(0, 2)              # move pointer to end
            file_size = file.tell()      # actual size in bytes
            file.seek(0)                 # reset pointer for pandas

            result = {
                "file name": file_name,
                "file type": ext,
                "total files": len(files),
                "file size": file_size,
                "upload_status": "Pending",
                "table_extract_status": "Pending",
                "column_extract_status": "Pending",
                "data_mapping_status": "Pending",
                "relation_mapping_status": "Pending",
                "total sheets": 0,
                "total column": 0,
                "table name": ""
            }

            if ext not in allowed_ext:
                result["upload_status"] = "Failed"
                final_response.append(result)
                continue

            file_data_chunks = []   # final chunk list
            total_rows = 0

            try:

                # ========== 1) EXCEL ==========
                if ext in ("xlsx", "xls"):

                    excel = pd.ExcelFile(file)
                    sheets = excel.sheet_names

                    result["total sheets"] = len(sheets)
                    result["table name"] = ",".join(sheets)

                    total_columns = 0

                    for sheet in sheets:
                        df = excel.parse(sheet)
                        rows = json.loads(df.to_json(orient="records"))

                        total_columns += len(df.columns)
                        total_rows += len(df)

                        # Split into chunks
                        for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):

                            chunk_json = {
                                "data": {
                                    sheet: chunk
                                }
                            }

                            file_data_chunks.append({
                                "unique_id": f"{generate_unique_id()}_{sheet}_{index}",
                                "row_data": chunk_json
                            })

                    result["total column"] = total_columns
                    result["upload_status"] = "Done"
                    result["table_extract_status"] = "Done"
                    result["column_extract_status"] = "Done"

                # ========== 2) CSV ==========
                elif ext == "csv":

                    df = pd.read_csv(file)
                    rows = json.loads(df.to_json(orient="records"))

                    total_rows = len(df)
                    result["total sheets"] = 1
                    result["table name"] = "Sheet1"
                    result["total column"] = len(df.columns)

                    for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):
                        chunk_json = {"data": {"Sheet1": chunk}}

                        file_data_chunks.append({
                            "unique_id": f"{generate_unique_id()}_Sheet1_{index}",
                            "row_data": chunk_json
                        })

                    result["upload_status"] = "Done"
                    result["table_extract_status"] = "Done"
                    result["column_extract_status"] = "Done"

                # ========== 3) XML ==========
                elif ext == "xml":

                    df = pd.read_xml(file)
                    rows = json.loads(df.to_json(orient="records"))

                    total_rows = len(df)
                    result["total sheets"] = 1
                    result["table name"] = "XMLData"
                    result["total column"] = len(df.columns)

                    for index, chunk in enumerate(chunk_list(rows, chunk_size=1000)):
                        chunk_json = {"data": {"XMLData": chunk}}

                        file_data_chunks.append({
                            "unique_id": f"{generate_unique_id()}_XMLData_{index}",
                            "row_data": chunk_json
                        })

                    result["upload_status"] = "Done"
                    result["table_extract_status"] = "Done"
                    result["column_extract_status"] = "Done"

                # ========== 4) SQL / DUMP ==========
                elif ext in ("sql", "dump"):

                    file_data_chunks.append({
                        "unique_id": generate_unique_id(),
                        "row_data": {"data": {}}
                    })

                    result["total sheets"] = 0
                    result["total column"] = 0
                    result["table name"] = "N/A"
                    total_rows = 0

                    result["upload_status"] = "Done"
                    result["table_extract_status"] = "Pending"
                    result["column_extract_status"] = "Pending"

            except Exception as e:
                result["upload_status"] = "Failed"
                result["error"] = str(e)
                final_response.append(result)
                continue

            # ========== CALL STORED PROCEDURE FOR EACH CHUNK ==========
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                for chunk in file_data_chunks:

                    cursor.execute("""
                        CALL sp_upload_file_count(
                            %s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s
                        )
                    """, (
                        session_id,
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
                        json.dumps([chunk]),  # single-chunk JSON array
                        file_size                  
                    ))

                conn.commit()
                cursor.close()
                conn.close()

            except Exception as db_error:
                result["upload_status"] = "Failed"
                result["error"] = str(db_error)

            final_response.append(result)

        return build_response(True, "Upload completed", 200, data=final_response)

    except Exception as e:
        return build_response(False, f"Error: {str(e)}", 500)

