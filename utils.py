from operator import imod
from celery import Celery
import pathlib, subprocess
import zipfile
from buildpack import Buildpack
from docker import APIClient, from_env, DockerClient

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

@celery.task
def upload_project(app_name, file):
    print("file", file)
    with zipfile.ZipFile(f"../shonku-projects/{app_name}/{file}", 'r') as zip_ref:
        zip_ref.extractall(f"../shonku-projects/{app_name}/")

@celery.task
def initialize_build(app_name):
    bp = Buildpack(app_name)
    bp.generateDockerfile(file=f"../shonku-projects/{app_name}/Shonkufile", save_location=f"../shonku-projects/{app_name}")

@celery.task
def build(app_name):
    for line in api.build(path=f"../shonku-projects/{app_name}", dockerfile="Dockerfile", tag=app_name):
        print(line)

@celery.task
def up(app_name, port):
    try:
        api.stop(app_name)
        api.remove_container(app_name)
        container = api.create_container(app_name, ports=[port], name=app_name, host_config=api.create_host_config(port_bindings={8000:port}))
        api.start(container)
    except:
        container = api.create_container(app_name, ports=[port], name=app_name, host_config=api.create_host_config(port_bindings={8000:port}))
        api.start(container)

@celery.task
def down(app_name):
    api.stop(app_name)
    api.remove_container(app_name)