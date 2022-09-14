import os
import pathlib
import importlib
from typing import Dict

import typer
from django.core.management import BaseCommand

from tasks import Task, TaskType
from conf.config import local_configs
from common.k8s_api import KubeSetting, KubernetesAPI

task_map: Dict[str, Task] = {}  # noqa
timed_task_folder = local_configs.PROJECT.BASE_DIR.joinpath(pathlib.Path("tasks/timed"))
file_names = os.listdir(timed_task_folder)  # noqa
for file_name in file_names:
    try:
        module = importlib.import_module(f".{file_name.split('.')[0]}", "tasks.timed")  # noqa
        manager = getattr(module, "task_manager", None)
        if manager:
            task_map.update(manager.task_map)
    except ModuleNotFoundError:
        continue
async_task_folder = local_configs.PROJECT.BASE_DIR.joinpath(pathlib.Path("tasks/asynchronous"))
file_names = os.listdir(async_task_folder)  # noqa
for file_name in file_names:
    try:
        module = importlib.import_module(f".{file_name.split('.')[0]}", "tasks.asynchronous")  # noqa
        manager = getattr(module, "task_manager", None)
        if manager:
            task_map.update(manager.task_map)
    except ModuleNotFoundError:
        continue


class Command(BaseCommand):
    help = """
    K8s任务管理
        show-all-jobs: 展示全部任务;  
        create-job: 创建定时任务;  
        create-all-job: 创建全部定时任务
    """
    available_actions = ["show-all-jobs", "create-job", "create-all-job"]  # noqa

    def add_arguments(self, parser):
        parser.add_argument("action", nargs=1, type=str, choices=self.available_actions)
        parser.add_argument(
            "--job-name", action="store", help="job name to create",
        )

    def handle(self, *args, **options):
        action = options["action"][0]
        if action == "show-all-jobs":  # noqa
            self.show_all_jobs()
        elif action == "create-job":  # noqa
            self.create_job()
        elif action == "create-all-job":
            for job_name, _ in task_map.items():
                try:
                    self.create_job(job_name)
                    print(f"任务: {job_name} 创建成功")
                except Exception as e:
                    print(f"任务: {job_name} 创建失败 >> {e}")

    @staticmethod
    def create_job(job_name: str):
        if not job_name:  # noqa
            print("必须指定任务名字!")
            return
        job = task_map.get(job_name)  # type: Task

        if job.type_ is TaskType.asynchronous:
            print(f"非异步定时任务，无须创建。 {job}")
            return

        name = f'timed-{job.function.__name__.replace("_", "-")}'  # noqa
        command = f'["python", {job.file_name}]'
        kube_setting = KubeSetting(name, command, schedule=job.cron)
        KubernetesAPI(config_file=local_configs.K8S.CONFIG_FILE).create_cron_job(kube_setting, **job.k8s_kwargs)
        print(f"创建任务-{job_name}成功")

    @staticmethod
    def show_all_jobs():
        print("Asynchronous:\n")  # noqa
        for k, v in task_map.items():
            if v.type_ is TaskType.asynchronous:
                print(k, ":", v)
        print("\n\nTimed:\n")
        for k, v in task_map.items():
            if v.type_ is TaskType.timed:
                print(k, ":", v)
