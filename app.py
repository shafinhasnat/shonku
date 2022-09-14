from crypt import methods
from ctypes import util
from flask import Flask, jsonify, request
import utils
import random
import requests
import json
app = Flask(__name__)
@app.route("/")
def home():
    return "Hello world"

@app.route("/projects", methods=["GET"])
def projects():
    resp = []
    projects = utils.mongo.projects.find({})
    for i in projects:
        i["_id"]=str(i["_id"])
        resp.append(i)
    return jsonify({"projects": resp, "status": "OK"}), 200

@app.route("/projects/<app_name>", methods=["GET"])
def project(app_name):
    find = utils.mongo.projects.find_one({"app_name": app_name})
    if find:
        find["_id"] = str(find["_id"])
    return jsonify({"project": find, "status": "OK"}), 200


@app.route("/create-app", methods=["POST"])
def create_app():
    payload = request.get_json()
    app_name = payload.get("app_name")
    find = utils.mongo.projects.find_one({"app_name": app_name})
    if not find:
        utils.create_project.delay(app_name)
        return jsonify({"app_name": app_name, "status": "OK"}), 200
    return jsonify({"app_name": app_name, "status": "ERROR", "msg": "Project already exist"}), 400

@app.route("/upload-app", methods=["POST"])
def upload_app():
    file = request.files["file"]
    app_name = request.form["app_name"].lower()
    language = request.form["language"]
    file.save(f"/home/ubuntu/shonku-projects/{app_name}/{file.filename}")
    utils.upload_project.delay(app_name, file.filename)
    return jsonify({"file name": file.name, "app_name": app_name, "language": language, "status": "OK"}), 200

@app.route("/initialize-build/<app_name>", methods=["GET"])
def initialize_build(app_name):
    utils.initialize_build.delay(app_name)
    return jsonify({"app_name": app_name, "status": "OK"}), 200

@app.route("/build", methods=["POST"])
def build():
    payload = request.get_json()
    app_name = payload.get("app_name")
    utils.build.delay(app_name)
    return jsonify({"app_name": app_name, "status": "OK"}), 200

@app.route("/up/<app_name>", methods=["GET"])
def up(app_name):
    port = random.randint(4000, 6000)
    utils.up.delay(app_name, port)
    public_ip = requests.get('https://api.ipify.org').content.decode('utf8')
    return jsonify({"app_name": app_name, "url": f"http://{public_ip}:{port}", "message":"Try the url after few seconds later", "status": "UP"}), 200

@app.route("/down/<app_name>", methods=["GET"])
def down(app_name):
    utils.down.delay(app_name)
    return jsonify({"app_name": app_name, "status": "DOWN"}), 200

@app.route("/launch-mongo", methods=["POST"])
def launch_mongo():
    payload = request.get_json()
    app_name = payload.get("app_name")
    utils.launch_mongo(app_name)
    return jsonify({"app_name": app_name, "status": "SUCCESS", "message": "Mongo launch successful"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)