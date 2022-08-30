from celery import Celery
import pathlib, subprocess
import zipfile
from buildpack import Buildpack
from docker import APIClient, from_env, DockerClient
from pymongo import MongoClient
import requests

m = MongoClient("mongodb://poridhimongo:poridhi@36.255.70.114:27017/?authSource=admin", connect=False)
mongo = m["paas"]

celery = Celery(
    __name__,
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
)
api = APIClient()
client = DockerClient()

@celery.task
def create_project(app_name):
    pathlib.Path(f"../shonku-projects/{app_name}").mkdir(exist_ok=True)
    mongo.projects.insert_one({"app_name": app_name, "codebase": False, "dockerfile": False, "build": False, "up": False})

@celery.task
def upload_project(app_name, file):
    print("file", file)
    with zipfile.ZipFile(f"../shonku-projects/{app_name}/{file}", 'r') as zip_ref:
        files = zip_ref.namelist()
        if "Shonkufile" not in files:
            return
        zip_ref.extractall(f"../shonku-projects/{app_name}/")
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"codebase": True}})

@celery.task
def initialize_build(app_name):
    bp = Buildpack(app_name)
    bp.generateDockerfile(file=f"../shonku-projects/{app_name}/Shonkufile", save_location=f"../shonku-projects/{app_name}")
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"dockerfile": True}})
    for line in api.build(path=f"../shonku-projects/{app_name}", dockerfile="Dockerfile", tag=app_name):
        print(line)
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"build": True}})

@celery.task
def build(app_name):
    for line in api.build(path=f"../shonku-projects/{app_name}", dockerfile="Dockerfile", tag=app_name):
        print(line)
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"build": True}})

@celery.task
def up(app_name, port):
    try:
        api.stop(app_name)
        api.remove_container(app_name)
        container = api.create_container(app_name, ports=[port], name=app_name, host_config=api.create_host_config(port_bindings={8000:port}))
        api.start(container)
        public_ip = requests.get('https://api.ipify.org').content.decode('utf8')
        mongo.projects.update_one({"app_name": app_name}, {"$set": {"up": True, "url": f"http://{public_ip}:{port}"}})
    except:
        container = api.create_container(app_name, ports=[port], name=app_name, host_config=api.create_host_config(port_bindings={8000:port}))
        api.start(container)
        public_ip = requests.get('https://api.ipify.org').content.decode('utf8')
        mongo.projects.update_one({"app_name": app_name}, {"$set": {"up": True, "url": f"http://{public_ip}:{port}"}})

@celery.task
def down(app_name):
    api.stop(app_name)
    api.remove_container(app_name)
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"up": False, "build": False, "url": False}})