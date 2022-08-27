from crypt import methods
from ctypes import util
from flask import Flask, jsonify, request
import utils
import random

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello world"

@app.route("/create-app", methods=["POST"])
def create_app():
    payload = request.get_json()
    app_name = payload.get("app_name")
    utils.create_project.delay(app_name)
    return jsonify({"app_name": app_name, "status": "OK"}), 200

@app.route("/upload-app", methods=["POST"])
def upload_app():
    file = request.files["file"]
    app_name = request.form["app_name"]
    language = request.form["language"]
    print("=====>", file.name, app_name, language)
    file.save(f"../shonku-projects/{app_name}/{file.filename}")
    utils.upload_project.delay(app_name, file.filename)
    return jsonify({"file name": file.name, "app_name": app_name, "language": language, "status": "OK"}), 200

@app.route("/initialize-build/<app_name>", methods=["GET"])
def initialize_build(app_name):
    port = random.randint(4000, 6000)
    utils.initialize_build.delay(f"../shonku-projects/{app_name}/Shonkufile", f"../shonku-projects/{app_name}", port)
    return jsonify({"app_name": app_name, "status": "OK"}), 200

@app.route("/build", methods=["POST"])
def build():
    payload = request.get_json()
    app_name = payload.get("app_name")
    utils.build.delay(app_name)
    return jsonify({"app_name": app_name, "status": "OK"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6010, debug=True)