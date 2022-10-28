import logging
import subprocess
from functools import partial

from django.core.management import BaseCommand

from conf.config import local_configs as settings

logger = logging.getLogger("manage.redis")

shell = partial(subprocess.run, shell=True)


class Command(BaseCommand):
    help = """
    Redis   
        shell: 交互shell;
    """
    available_actions = [
        "shell",
    ]  # noqa

    def add_arguments(self, parser):
        parser.add_argument("action", nargs=1, type=str, choices=self.available_actions)
        parser.add_argument(
            "--db", action="store", help="redis-db to access",
        )

    def handle(self, *args, **options):
        action = options["action"][0]
        if action == "shell":  # noqa
            db = options["db"]
            if settings.REDIS.PASSWORD:
                cmd = "redis-cli -h {host} -p {port} -a {password} -n {db}".format(
                    host=settings.REDIS.HOST, port=settings.REDIS.PORT, password=settings.REDIS.PASSWORD, db=db,
                )
            else:
                cmd = "redis-cli -h {host} -p {port} -n {db}".format(
                    host=settings.REDIS.HOST, port=settings.REDIS.PORT, db=db,
                )
            shell(cmd)
