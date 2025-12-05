from flask import Flask, request
from flask_cors import CORS
from database.dbConnection import get_db_connection
from controller.register import register_controller
from controller.login import login_controller
from controller.get_tracker import get_tracker_controller
from controller.upload_files_count import upload_files_count_controller
from controller.process_session_data import process_session_data_controller
from controller.get_ui_data import get_ui_data_controller
from controller.chat_query import chat_query_controller
from controller.save_chat import save_chat_controller
from controller.sql_ai_executor import chat_endpoint, execute_sql_endpoint
from controller.get_dashboard_data import get_dashboard_data_controller
from controller.get_saved_chat_response import get_chat_history_by_user_controller
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

@app.route("/process_session_data", methods=["POST"])
def process_session_data_route():
    return process_session_data_controller()

@app.route("/get_ui_data", methods=["POST"])
def get_ui_data_route():
    return get_ui_data_controller()

@app.route("/chat_query", methods=["POST"])
def chat_query_route():
    return chat_query_controller()

@app.route("/save_chat", methods=["POST"])
def save_chat_route():
    return save_chat_controller()

@app.route("/get_chat_history", methods=["POST"])
def get_chat_history_route():
    return get_chat_history_by_user_controller()  

@app.route("/chat_ai", methods=["POST"])
def chat_ai_route():
    return chat_endpoint()

@app.route("/execute_sql", methods=["POST"])
def execute_sql_route():
    return execute_sql_endpoint()

@app.route("/get_dashboard_data", methods=["POST"])
def get_dashboard_data_route():
    return get_dashboard_data_controller()

# Run the Flask Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3008, debug=True)
   
