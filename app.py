from flask import Flask, request
from flask_cors import CORS
from database.dbConnection import get_db_connection
from controller.register import register_controller
from controller.login import login_controller

from controller.upload_file import upload_and_insights_controller
from controller.get_file_status import get_file_status_controller
from controller.get_full_table_info import get_full_table_info_controller

app = Flask(__name__)

CORS(app)


@app.route("/")
def hello_world():
    return 'Hello, World!'

@app.route("/register", methods=["POST"])
def register_route():
    return register_controller()

@app.route("/login", methods=["POST"])
def login_route():
    return login_controller()

@app.route("/get_file_status", methods=["POST"])
def get_file_status_route():
    return get_file_status_controller()

@app.route("/upload_files", methods=["POST"])
def upload_and_insights_route():
    return upload_and_insights_controller()


@app.route("/get_full_table_info", methods=["POST"])
def get_full_table_info_route():
    return get_full_table_info_controller()


# Run the Flask Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3008, debug=True)