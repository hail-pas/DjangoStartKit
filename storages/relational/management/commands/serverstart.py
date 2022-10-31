import subprocess
from functools import partial

from django.core.management import BaseCommand

from conf.config import local_configs

shell = partial(subprocess.run, shell=True)


class Command(BaseCommand):
    help = """shell 启动 core.main 服务器"""

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        shell(str(local_configs.PROJECT.BASE_DIR.absolute()) + "/start.sh")
