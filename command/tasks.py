import importlib
import os
import pathlib
import typer
from typing import Dict
from tasks import Task, TaskType
from common.k8s_api import KubernetesAPI, KubeSetting
from conf.config import local_configs

tasks_create_typer = typer.Typer(short_help="任务创建")
task = tasks_create_typer.command

task_map: Dict[str, Task] = {}
timed_task_folder = pathlib.Path(__file__).parent.parent.joinpath(pathlib.Path("tasks/timed"))
files = os.listdir(timed_task_folder)
for file in files:
    try:
        module = importlib.import_module(f".{file.split('.')[0]}", "tasks.timed")
        manager = getattr(module, "task_manager", None)
        if manager:
            task_map.update(manager.task_map)
    except ModuleNotFoundError:
        continue
async_task_folder = pathlib.Path(__file__).parent.parent.joinpath(pathlib.Path("tasks/asynchronous"))
files = os.listdir(async_task_folder)
for file in files:
    try:
        module = importlib.import_module(f".{file.split('.')[0]}", "tasks.asynchronous")
        manager = getattr(module, "task_manager", None)
        if manager:
            task_map.update(manager.task_map)
    except ModuleNotFoundError:
        continue


@task()
def show_all_jobs():
    """
    显示所有已注册的任务
    """
    print("Asynchronous:\n")
    for k, v in task_map.items():
        if v.type_ is TaskType.asynchronous:
            print(k, ":", v)
    print("\n\nTimed:\n")
    for k, v in task_map.items():
        if v.type_ is TaskType.timed:
            print(k, ":", v)


@task()
def create_job(
        job_name: str = typer.Option(default="", help="任务名字")
):
    """
    创建任务
    """
    if not job_name:
        print("必须指定任务名字!")
        return
    job = task_map.get(job_name)  # type: Task

    if job.type_ is TaskType.asynchronous:
        print(f"非异步定时任务，无须创建。 {job}")
        return

    name = f'timed-{job.function.__name__.replace("_", "-")}'  # noqa
    command = f'["python", {job.file_name}]'
    kube_setting = KubeSetting(name, command, schedule=job.cron)
    KubernetesAPI(config_file=local_configs.KUBE_CONFIG_FILE).create_cron_job(kube_setting, **job.k8s_kwargs)
    print(f"创建任务-{job_name}成功")


@task()
def create_all_job():
    for job_name, _ in task_map.items():
        create_job(job_name)
    print("Success")
