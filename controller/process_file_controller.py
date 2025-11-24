import json
import hashlib
from flask import request, jsonify, Blueprint
from database.dbConnection import get_db_connection
from utils.cleaner import clean_dataframe_from_rows, build_cleaned_json_for_sheets

bp = Blueprint("process_file", __name__, url_prefix="/api")


def _compute_clean_unique_id(base_unique_id, sheet_name, session_id):
    raw = f"{base_unique_id}__{sheet_name}__{session_id}__clean"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


@bp.route("/process_file", methods=["POST"])
def process_file_controller():
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        session_id = payload.get("session_id")
        file_name = payload.get("file_name")
        unique_id = payload.get("unique_id", None)
        sheet_name_filter = payload.get("sheet_name", None)

        if not session_id or not file_name:
            return jsonify({"status": "failed", "message": "session_id and file_name are required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if unique_id:
            cursor.execute("""
                SELECT id, session_id, file_name, unique_id, row_data 
                FROM file_data
                WHERE session_id=%s AND file_name=%s AND unique_id=%s
            """, (session_id, file_name, unique_id))
        else:
            cursor.execute("""
                SELECT id, session_id, file_name, unique_id, row_data 
                FROM file_data
                WHERE session_id=%s AND file_name=%s
            """, (session_id, file_name))

        rows = cursor.fetchall()
        if not rows:
            cursor.close()
            conn.close()
            return jsonify({"status": "failed", "message": "No matching file_data rows found"}), 404

        results = []
        for rec in rows:
            rec_unique_id = rec.get("unique_id")
            raw_row_data = rec.get("row_data")
            try:
                parsed = json.loads(raw_row_data) if isinstance(raw_row_data, (str, bytes)) else raw_row_data
            except Exception as e:
                results.append({"unique_id": rec_unique_id, "status": "error", "message": f"invalid JSON: {e}"})
                continue

            sheets = parsed.get("data") if isinstance(parsed, dict) else None
            if not sheets or not isinstance(sheets, dict):
                results.append({"unique_id": rec_unique_id, "status": "skipped", "message": "no sheets found"})
                continue

            cleaned_sheets = {}
            for sheet_name, rows_list in sheets.items():
                if sheet_name_filter and sheet_name_filter != sheet_name:
                    continue
                cleaned_df, meta = clean_dataframe_from_rows(rows_list)
                cleaned_sheets[sheet_name] = cleaned_df

            if not cleaned_sheets:
                results.append({"unique_id": rec_unique_id, "status": "skipped", "message": "no sheets after cleaning"})
                continue

            cleaned_json = build_cleaned_json_for_sheets(cleaned_sheets)

            try:
                for sheet_name, df in cleaned_sheets.items():
                    clean_unique_id = _compute_clean_unique_id(rec_unique_id, sheet_name, session_id)
                    upsert_sql = """
                    INSERT INTO file_data_cleaned
                        (session_id, file_name, sheet_name, unique_id, cleaned_rows, cleaned_columns, raw_row_count, remarks, row_data)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        cleaned_rows=VALUES(cleaned_rows),
                        cleaned_columns=VALUES(cleaned_columns),
                        raw_row_count=VALUES(raw_row_count),
                        remarks=VALUES(remarks),
                        row_data=VALUES(row_data),
                        updated_at=CURRENT_TIMESTAMP
                    """
                    params = (
                        session_id, file_name, sheet_name, clean_unique_id,
                        df.shape[0], df.shape[1], df.shape[0], "processed", cleaned_json
                    )
                    cur2 = conn.cursor()
                    cur2.execute(upsert_sql, params)
                    conn.commit()
                    cur2.close()
                    results.append({"unique_id": rec_unique_id, "sheet": sheet_name, "status": "inserted",
                                    "rows": df.shape[0]})
            except Exception as e:
                results.append({"unique_id": rec_unique_id, "status": "db_error", "message": str(e)})

        cursor.close()
        conn.close()
        return jsonify({"status": "success", "results": results}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
