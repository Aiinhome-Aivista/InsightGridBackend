import os
from flask import jsonify
from dotenv import load_dotenv

# ---------- Load Environment Variables ----------
load_dotenv()


ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS")

def get_allowed_extensions():
    exts = os.getenv("ALLOWED_EXTENSIONS", "")
    return set(ext.strip().lower() for ext in exts.split(",") if ext.strip())

def get_upload_folder():
    return os.getenv("UPLOAD_FOLDER", "uploads")

# Check if file extension is allowed
def allowed_file(filename):
    allowed = get_allowed_extensions()
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

def build_response(is_success, message, status_code, data=None):
    payload = {
        "isSuccess": is_success,
        "message": message,
        "statusCode": status_code,
    }
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code