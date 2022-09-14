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
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0',
)
api = APIClient("tcp://36.255.70.209:2375")
# client = DockerClient()

@celery.task
def create_project(app_name):
    pathlib.Path(f"/home/ubuntu/shonku-projects/{app_name}").mkdir(exist_ok=True)
    network = api.create_network(app_name, check_duplicate=True)
    mongo.projects.insert_one({"app_name": app_name, "codebase": False, "dockerfile": False, "build": False, "up": False, "mongo": False, "network": network["Id"]})

@celery.task
def upload_project(app_name, file):
    print("file", file)
    with zipfile.ZipFile(f"/home/ubuntu/shonku-projects/{app_name}/{file}", 'r') as zip_ref:
        files = zip_ref.namelist()
        if "Shonkufile" not in files:
            return
        zip_ref.extractall(f"/home/ubuntu/shonku-projects/{app_name}/")
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"codebase": True}})

@celery.task
def initialize_build(app_name):
    bp = Buildpack(app_name)
    bp.generateDockerfile(file=f"/home/ubuntu/shonku-projects/{app_name}/Shonkufile", save_location=f"/home/ubuntu/shonku-projects/{app_name}")
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"dockerfile": True}})
    for line in api.build(path=f"/home/ubuntu/shonku-projects/{app_name}", dockerfile="Dockerfile", tag=app_name, network_mode="host"):
        print(line)
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"build": True}})

@celery.task
def build(app_name):
    for line in api.build(path=f"/home/ubuntu/shonku-projects/{app_name}", dockerfile="Dockerfile", tag=app_name, network_mode="host"):
        print(line)
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"build": True}})

@celery.task
def launch_mongo(app_name):
    find = mongo.projects.find_one({"app_name": app_name})
    if not find:
        return
    api.create_container("mongo", name=f"mongo-{app_name}", hostname=f"mongo-{app_name}", environment=[f"MONGO_INITDB_ROOT_USERNAME=mongo-{app_name}", f"MONGO_INITDB_ROOT_PASSWORD={app_name}"])
    api.connect_container_to_network(f"mongo-{app_name}", net_id=find["network"])
    api.start(container=f"mongo-{app_name}")
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"mongo": f"mongo-{app_name}"}})

@celery.task
def up(app_name, port):
    find = mongo.projects.find_one({"app_name": app_name})
    if not find:
        return
    try:
        api.stop(app_name)
        api.remove_container(app_name)
        container = api.create_container(app_name, ports=[port], name=app_name, host_config=api.create_host_config(port_bindings={8000:port}))
        api.connect_container_to_network(app_name, net_id=find["network"])
        api.start(container)
        public_ip = requests.get('https://api.ipify.org').content.decode('utf8')
        mongo.projects.update_one({"app_name": app_name}, {"$set": {"up": True, "url": f"http://{public_ip}:{port}"}})
    except:
        container = api.create_container(app_name, ports=[port], name=app_name, host_config=api.create_host_config(port_bindings={8000:port}))
        api.connect_container_to_network(app_name, net_id=find["network"])
        api.start(container)
        public_ip = requests.get('https://api.ipify.org').content.decode('utf8')
        mongo.projects.update_one({"app_name": app_name}, {"$set": {"up": True, "url": f"http://{public_ip}:{port}"}})

@celery.task
def down(app_name):
    api.stop(app_name)
    api.remove_container(app_name)
    mongo.projects.update_one({"app_name": app_name}, {"$set": {"up": False, "build": False, "url": False}})