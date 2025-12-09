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
        created_by = request.form.get("created_by")

        if not session_id or not created_by:
            return build_response(False, "session_id & created_by required", 400)

        files = request.files.getlist("files")
        if not files:
            return build_response(False, "No files uploaded", 400)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        #  VALIDATE SESSION ID & created_by
        # -----------------------------------
        cursor.execute(
            "SELECT user_id, session_id FROM users WHERE session_id = %s AND user_id = %s LIMIT 1",
            (session_id, created_by)
        )
        session_row = cursor.fetchone()

        if not session_row:
            cursor.close()
            db.close()
            return build_response(
                False,
                "Invalid session_id or created_by",
                400
                # {"status": "failed"}
            )

        result_info = []
       
        for file in files:

            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)

            # --------------------------------------------------------
            # READ CSV
            # --------------------------------------------------------
            df = pd.read_csv(filepath, dtype=str)
            df = df.drop_duplicates().dropna(how="all")
            df.columns = clean_column_names(df.columns)
            df = df.where(pd.notnull(df), None)

            total_rows = len(df)
            total_columns = len(df.columns)

            table_name = filename.replace(".csv", "").replace("-", "_").replace(" ", "_").replace(".", "_").lower()

            # --------------------------------------------------------
            # STORED PROCEDURE INSERT METADATA
            # --------------------------------------------------------
            cursor.callproc(
                "sp_insert_uploaded_file",
                [session_id, filename, table_name, file_size_mb, "csv", total_rows, total_columns, created_by],
            )
            # file_id = list(cursor.stored_results())[0].fetchone()["file_id"]
            
            # fetch SP result safely (file_id + status_flag)
            sp_result = list(cursor.stored_results())[0].fetchone()

            file_id = sp_result["file_id"]
            status_flag = sp_result["status_flag"] 
            
            # --------------------------------------------------------
            # CREATE TABLE IF NOT EXISTS
            # --------------------------------------------------------
            col_defs = ", ".join([f"`{col}` TEXT" for col in df.columns])
            try:
                cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS `{table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, {col_defs}, row_hash VARCHAR(64))"
                )
                cursor.execute("UPDATE uploaded_files SET table_extraction_status='done' WHERE id=%s", (file_id,))
            except Exception as e:
                cursor.execute("UPDATE uploaded_files SET table_extraction_status='failed' WHERE id=%s", (file_id,))
                db.commit()
                return build_response(False, f"Table creation failed: {str(e)}", 500)

            # --------------------------------------------------------
            # ENSURE UNIQUE INDEX FOR row_hash
            # --------------------------------------------------------
            try:
                cursor.execute(f"CREATE UNIQUE INDEX idx_{table_name}_rowhash ON `{table_name}` (row_hash)")
            except:
                pass  # already exists → ignore

            # --------------------------------------------------------
            # GENERATE row_hash FOR EACH ROW
            # --------------------------------------------------------
            df["row_hash"] = df.apply(lambda r: _make_row_hash(r.values), axis=1)

            # --------------------------------------------------------
            # FETCH EXISTING ROW HASHES FROM DB
            # --------------------------------------------------------
            cursor.execute(f"SELECT * FROM `{table_name}`")
            db_existing_rows = cursor.fetchall()
            existing_map = {row["row_hash"]: row for row in db_existing_rows}

            new_rows = 0
            updated_rows = 0

            # --------------------------------------------------------
            # DETECT NEW / UPDATED ROWS
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
            # UPSERT DATA (INSERT + UPDATE)
            # --------------------------------------------------------
            columns = df.columns.tolist()
            col_sql = ",".join([f"`{c}`" for c in columns])
            placeholders = ",".join(["%s"] * len(columns))
            update_sql = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in columns if c != "row_hash"])

            upsert_sql = f"""
                INSERT INTO `{table_name}` ({col_sql})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_sql};
            """

            cursor.executemany(upsert_sql, df.values.tolist())
            cursor.execute("UPDATE uploaded_files SET column_extraction_status='done' WHERE id=%s", (file_id,))

            # --------------------------------------------------------
            # DECIDE FINAL MESSAGE
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
            # GENERATE INSIGHTS
            # --------------------------------------------------------
            try:
                insights = generate_insights_from_llm(df, filename)
                cursor.execute(
                    "UPDATE uploaded_files SET insights=%s, data_insights_status='done' WHERE id=%s",
                    (json.dumps(insights), file_id),
                )
            except:
                cursor.execute("UPDATE uploaded_files SET data_insights_status='failed' WHERE id=%s", (file_id,))

            # cursor.callproc("sp_insert_file_steps", [file_id])
            db.commit()

            result_info.append(
                {
                    "file_id": file_id,
                    "file_name": filename,
                    "table_name": table_name,
                    "total_rows": total_rows,
                    "total_columns": total_columns,
                    "file_size_mb": file_size_mb,
                    "message": custom_message,
                    "status_flag": status_flag,
                }
            )

        return build_response(True, "File processed", 200, result_info)

    except Exception as e:
        return build_response(False, "Server Error", 500, {"error": str(e)})