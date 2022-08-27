from celery import Celery
import pathlib, subprocess
import zipfile
from buildpack import Buildpack

celery = Celery(
    __name__,
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
)

@celery.task
def create_project(app_name):
    pathlib.Path(f"../shonku-projects/{app_name}").mkdir(exist_ok=True)

@celery.task
def upload_project(app_name, file):
    print("file", file)
    with zipfile.ZipFile(f"../shonku-projects/{app_name}/{file}", 'r') as zip_ref:
        zip_ref.extractall(f"../shonku-projects/{app_name}/")

@celery.task
def initialize_build(app_name, port):
    bp = Buildpack(app_name)
    bp.generateDockerfile(file=f"../shonku-projects/{app_name}/Shonkufile", save_location=f"../shonku-projects/{app_name}", port=port)

@celery.task
def build(app_name):
    process = subprocess.Popen([f'app_name={app_name} ../shonku-projects/build.sh'], stdout=subprocess.PIPE, shell=True)
    process.wait()