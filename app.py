from flask import Flask, request
from flask_cors import CORS
from database.dbConnection import get_db_connection
from controller.register import register_controller
from controller.login import login_controller
from controller.get_tracker import get_tracker_controller
from controller.upload_files_count import upload_files_count_controller

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

@app.route("/tracker", methods=["GET"])
def tracker_route():
    return get_tracker_controller()

@app.route("/upload_files_count", methods=["POST"])
def upload_files_count_route():
    return upload_files_count_controller()

# Run the Flask Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3008, debug=True)
   
