import os
from flask import Flask, request,g, send_from_directory
from flask_cors import CORS
from controller.company_user_register import company_user_register_controller
from controller.get_file_status import get_file_status_controller
from controller.get_full_table_info import get_full_table_info_controller
from controller.get_dashboard_data import get_dashboard_data_controller
from controller.sql_ai_executor import chat_endpoint_controller,execute_sql_endpoint_controller
from controller.query_save import query_save_controller
from controller.get_saved_query_response import get_saved_query_response_controller
from controller.delete_upload_file import delete_uploaded_file_controller
from controller.upload_file_new import upload_and_insights_new_controller
from controller.report_controller import save_report_controller, report_list_controller
from controller.admin_company_register import admin_company_register_controller
from controller.admin_company_admin_register import admin_company_admin_register_controller
from middleware.dbContext import attach_company_db
from controller.superadmin_login import superadmin_login_controller
from controller.company_login import company_login_controller

# app = Flask(__name__,
#     static_url_path="/uploads",
#     static_folder=os.getenv("UPLOAD_FOLDER"))

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
CORS(app)


@app.before_request
def before_request():
    return attach_company_db()


@app.route("/")
def hello_world():
    return 'Hello, World!'

@app.route("/company_user_register", methods=["POST"])
def company_user_register_route():
    return company_user_register_controller()


@app.route("/superadmin/login", methods=["POST"])
def superadmin_login():
    return superadmin_login_controller()

@app.route("/company/login", methods=["POST"])
def company_login():
    return company_login_controller()

@app.route("/get_file_status", methods=["POST"])
def get_file_status_route():
    return get_file_status_controller()

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

@app.route("/report_save", methods=["POST"])
def report_save_route():
    return save_report_controller()

@app.route("/report_list", methods=["POST"])
def report_list_route():
    return report_list_controller()



@app.route("/admin/company_register", methods=["POST"])
def admin_company_register_route():
    return admin_company_register_controller()

@app.route("/admin/company/admin_register", methods=["POST"])
def admin_company_admin_register_route():
    return admin_company_admin_register_controller()

@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOAD_ROOT, filename)


# Run the Flask Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3008, debug=True)