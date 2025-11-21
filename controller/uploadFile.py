import os
import pandas as pd   
from flask import request, jsonify
from werkzeug.utils import secure_filename
from utils.helper import get_upload_folder, allowed_file

UPLOAD_FOLDER = get_upload_folder()


def upload_files_controller():
    try:
        # -----------------------------------------
        #   🔹 Combined Validation (Minimal Change)
        # -----------------------------------------
        errors = {}

        file_name = request.form.get("file_name")
        files = request.files.getlist("files")

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
        # -----------------------------------------

        saved_files = []

        # Create upload folder if not exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # ---- Save each file ----
        for file in files:

            if not file or not allowed_file(file.filename):
                return jsonify({
                    "status": "failed",
                    "statusCode": 400,
                    "message": f"File type not allowed: {file.filename}",
                    "data": []
                }), 400

            safe_name = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, safe_name)
            file.save(file_path)
            saved_files.append(file_path)

            # ---------------------------
            # DYNAMIC VALIDATION
            # ---------------------------
            ext = safe_name.rsplit(".", 1)[1].lower()

            # read file
            if ext == "csv":
                df = pd.read_csv(file_path)
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(file_path)
            elif ext == "xml":
                # skip validation
                continue
            else:
                return jsonify({
                    "status": "failed",
                    "statusCode": 400,
                    "message": f"Unsupported format: {ext}",
                    "data": []
                }), 400

          # ---- Validation Rules ----
        errors = {}

        # ---------------------
        # 1. NULL value check
        # ---------------------
        null_counts = df.isnull().sum()
        null_cols = {col: int(v) for col, v in null_counts.items() if v > 0}
        if null_cols:
            errors["null_values"] = null_cols

        # ---------------------
        # 2. Duplicate check
        # ---------------------
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            errors["duplicate_rows"] = int(dup_count)

        # ---------------------
        # 3. Data type detection
        # ---------------------
        dtype_map = {}
        for col in df.columns:
            try:
                pd.to_numeric(df[col].dropna())
                dtype_map[col] = "number"
            except:
                try:
                    pd.to_datetime(df[col].dropna())
                    dtype_map[col] = "date"
                except:
                    dtype_map[col] = "string"

        # ------------------------------
        # 4. Data Type Mismatch Check
        # ------------------------------
        type_errors = {}

        for col in df.columns:
            col_type = dtype_map[col]

            col_data = df[col].dropna().astype(str)

            # --- String column but numeric found ---
            if col_type == "string":
                only_numbers = col_data.str.replace('.', '').str.isnumeric().all()
                if only_numbers:
                    type_errors[col] = "Expected string but column contains numeric values."

            # --- Number column but alphabetic found ---
            if col_type == "number":
                if any(any(c.isalpha() for c in val) for val in col_data):
                    type_errors[col] = "Expected number but column contains alphabetic values."

            # --- Date column but invalid date values ---
            if col_type == "date":
                try:
                    pd.to_datetime(df[col], errors="raise")
                except:
                    type_errors[col] = "Expected date but found invalid date values."

        # add type mismatch errors
        if type_errors:
            errors["datatype_mismatch"] = type_errors

        # ---------------------------
        # If ANY validation failed
        # ---------------------------
        if errors:
            return jsonify({
                "status": "failed",
                "statusCode": 400,
                "message": "Validation Failed",
                "data": {
                    "file_name": safe_name,
                    "errors": errors,
                    "detected_datatypes": dtype_map
                }
            }), 400


        # ---- Success Response ----
        return jsonify({
            "status": "success",
            "statusCode": 200,
            "message": "Files uploaded successfully",
            "data": {
                "file_name": file_name,
                "uploaded_files": saved_files
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "statusCode": 500,
            "message": "File upload failed",
            "error": str(e),
            "data": []
        }), 500
