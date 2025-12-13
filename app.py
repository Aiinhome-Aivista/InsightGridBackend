from flask import Flask, request
from flask_cors import CORS
from database.dbConnection import get_db_connection
from controller.register import register_controller
from controller.login import login_controller
from controller.upload_file_old import upload_and_insights_old_controller
from controller.get_file_status import get_file_status_controller
from controller.get_full_table_info import get_full_table_info_controller
from controller.get_dashboard_data import get_dashboard_data_controller
from controller.sql_ai_executor import chat_endpoint_controller,execute_sql_endpoint_controller
from controller.query_save import query_save_controller
from controller.get_saved_query_response import get_saved_query_response_controller
from controller.delete_upload_file import delete_uploaded_file_controller
from controller.upload_file_new import upload_and_insights_new_controller
from controller.get_uploaded_table_with_tabledata import get_uploaded_table_with_tabledata_controller
from controller.report_controller import save_report_controller, report_list_controller
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
def upload_and_insights_old_route():
    return upload_and_insights_old_controller()

@app.route("/upload_files_new", methods=["POST"])
def upload_and_insights_new_route():
    return upload_and_insights_new_controller()

@app.route("/get_full_table_info", methods=["POST"])
def get_full_table_info_route():
    return get_full_table_info_controller()

@app.route("/get_dashboard_data", methods=["POST"])
def get_dashboard_data_route():
    return get_dashboard_data_controller()

@app.route("/chat_ai", methods=["POST"])
def chat_endpoint_route():
    return chat_endpoint_controller()

@app.route("/execute_sql", methods=["POST"])
def execute_sql_endpoint_route():
    return execute_sql_endpoint_controller()

@app.route("/query_save", methods=["POST"])
def query_save_route():
    return query_save_controller()

@app.route("/get_saved_query_response", methods=["POST"])
def get_saved_query_response_route():
    return get_saved_query_response_controller()  

@app.route("/delete_uploaded_file", methods=["POST"])
def delete_uploaded_file_route():
    return delete_uploaded_file_controller() 

@app.route("/get_uploaded_table_with_tabledata", methods=["POST"])
def get_uploaded_table_with_tabledata_route():     
    return get_uploaded_table_with_tabledata_controller() 


@app.route("/report_save", methods=["POST"])
def report_save_route():
    return save_report_controller()

@app.route("/report_list", methods=["POST"])
def report_list_route():
    return report_list_controller()

# @app.route("/report_update", methods=["POST"])
# def report_updated_route():
#     return update_report_controller()

# Run the Flask Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3008, debug=True)