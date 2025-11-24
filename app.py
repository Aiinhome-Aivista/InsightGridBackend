from flask import Flask
from flask_cors import CORS
from controller.login import login_controller
from controller.uploadFile import upload_files_controller 
from controller.register import register_controller
from controller.uploadFile import upload_files_controller
from controller.getFileData import get_file_data_controller

app = Flask(__name__)

CORS(app)


@app.route("/")
def hello_world():
    return 'Hello, World!'


@app.route("/upload_files", methods=["POST"])
def upload_files():
    """
    POST API: Upload CSV/Excel files
    Saves file and stores raw + cleaned data
    """
    return upload_files_controller()

@app.route("/register", methods=["POST"])
def register():
    return register_controller()

@app.route("/login", methods=["POST"])
def login():
    return login_controller()

@app.route("/get_file_data", methods=["GET"])
def get_file_data():
    """
    GET API: Fetch file metadata and analyze structure
    Extracts: Tables -> Columns -> Data Mapping
    
    Query Parameters:
    - file_name (required): Name of the uploaded file
    - session_id (optional): Session ID, default is '123456'
    
    Example: /get_file_data?file_name=SalesData&session_id=123456
    """
    return get_file_data_controller()


# Run the Flask Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3008, debug=True)