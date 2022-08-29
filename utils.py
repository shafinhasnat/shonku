from operator import imod
from celery import Celery
import pathlib, subprocess
import zipfile
from buildpack import Buildpack
import docker

celery = Celery(
    __name__,
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
)
api = docker.APIClient()
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
    # process = subprocess.Popen([f'app_name={app_name} ../shonku-projects/build.sh'], stdout=subprocess.PIPE, shell=True)
    # process.wait()
    api.build(path=f"../shonku_projects/{app_name}/")

@celery.task
def up(app_name, port):
    container = api.create_container(app_name, ports=[port], host_config=api.create_host_config(port_bindings={port:8000}))
    api.start(container)
    # process = subprocess.Popen([f'app_name={app_name} port={port} ./up.sh'], stdout=subprocess.PIPE, shell=True)
    # process.wait()
    # cat = subprocess.run(["cat", f"../shonku-projects/{app_name}/docker-compose.yml"], check=True, capture_output=True)
    # sed = subprocess.run(["sed", f"s/[PORT]/{port}/g"], input=cat.stdout, capture_output=True)
    # up = subprocess.run(["docker-compose", "-f", "-", "up", "-d"], input=sed.stdout, capture_output=True)
    # print(up, "*******")
    # subprocess.Popen(f"cat ../shonku-projects/{app_name}/docker-compose.yml", shell=True, stdout=subprocess.PIPE)

@celery.task
def down(app_name):
    api.stop(app_name)
    # subprocess.run(["docker-compose", "-f", f"../shonku-projects/{app_name}/docker-compose.yml", "down"])
# cat docker-compose.yml | sed "s/PORT/4040/g" | docker-compose -f - up -d
# subprocess.run(["cat", f"../shonku-projects/{app_name}/docker-compose.yml", "|", "sed", f"s/[PORT]/{port}/g", "|", "docker-compose", "-f", "-", "up", "-d"])