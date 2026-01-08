import os

from flask import jsonify,g
from dotenv import load_dotenv
import uuid
import hashlib
import base64
from datetime import date, datetime

# ---------- Load Environment Variables ----------
load_dotenv()


ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS")
ALLOWED_LOGO_EXT = os.getenv("ALLOWED_LOGO_EXT")

def get_allowed_extensions():
    exts = os.getenv("ALLOWED_EXTENSIONS", "")
    return set(ext.strip().lower() for ext in exts.split(",") if ext.strip())

def get_upload_folder():
    return os.getenv("UPLOAD_FOLDER", "uploads")

# Check if file extension is allowed
def allowed_file(filename):
    allowed = get_allowed_extensions()
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

def build_response(is_success, message, status_code, data=None, status=None, extra=None):
    payload = {
        "isSuccess": is_success,
        "message": message,
        "statusCode": status_code,
    }
    if status is not None:
        payload["status"] = status
    if data is not None:
        payload["data"] = data
    if extra:
        payload.update(extra)
    return jsonify(payload), status_code


# Generate a unique user ID
def generate_user_id(firstname):
    short_id = uuid.uuid4().hex[:6]   # first 6 chars
    return f"{firstname.lower()}_{short_id}"

def format_file_size(num_bytes):
    for unit in ["Bytes", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024:
            # Round to nearest integer
            return f"{round(num_bytes)} {unit}"
        num_bytes /= 1024



def generate_unique_id():
    return uuid.uuid4().hex


def chunk_list(data, chunk_size=1000):
    """Yield chunks of list."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]
        
def get_company_upload_path(file_name):
    company_folder = os.path.join(
        get_upload_folder(),
        g.company_db.database
    )
    os.makedirs(company_folder, exist_ok=True)
    return os.path.join(company_folder, file_name) 

def allowed_logo(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_LOGO_EXT
    )
    
def make_file_hash(session_id, file_name):
    return hashlib.md5(f"{session_id}|{file_name}".encode()).hexdigest()
  
  

def save_base64_image(base64_str, path):
    header, data = base64_str.split(",", 1)
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))   
        

def format_dates_in_rows(rows):
    for row in rows:
        for key, value in row.items():

            # ✅ DATETIME → "5 Jan 2026, 2:30 PM"
            if isinstance(value, datetime):
                row[key] = value.strftime("%-d %b %Y, %-I:%M %p")

            # ✅ DATE → "05-01-2026"
            elif isinstance(value, date):
                row[key] = value.strftime("%d-%m-%Y")

    return rows
         
       




