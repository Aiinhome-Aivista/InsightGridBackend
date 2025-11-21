from flask import Flask
from flask_cors import CORS
from controller.uploadFile import upload_files_controller 

app = Flask(__name__)

CORS(app)


@app.route("/")
def hello_world():
    return 'Hello, World!'

@app.route("/upload_files",methods=["POST"])
def upload_files():
    return upload_files_controller()

# Run the Flask Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3008, debug=True)