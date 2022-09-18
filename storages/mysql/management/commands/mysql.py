import logging
import pathlib
import subprocess
from functools import partial

from django.core.management.base import BaseCommand, CommandError

from conf.enums import Environment
from conf.config import local_configs as settings

logger = logging.getLogger("manage.mysql")

shell = partial(subprocess.run, shell=True)


class Command(BaseCommand):
    help = """
    MySQL相关操作
        createdb: 创建数据库; 
        dropdb: 删除数据;
        shell: 交互shell;
        execute-file --file-path [] : 执行sql文件
    """

    available_actions = ["createdb", "dropdb", "shell", "execute-file"]  # noqa

    def add_arguments(self, parser):
        parser.add_argument("action", nargs=1, type=str, choices=self.available_actions)
        parser.add_argument(
            "--file-path", action="store", help="execute file path",
        )

    def handle(self, *args, **options):
        action = options["action"][0]
        if action == "createdb":  # noqa
            shell(
                "mysql -h {host} --port={port} -u{user} -p{password} -e "
                '"CREATE DATABASE IF NOT EXISTS \\`{name}\\` '
                'default character set utf8mb4 collate utf8mb4_general_ci;"'.format(
                    host=settings.RELATIONAL_DB.HOST,
                    port=settings.RELATIONAL_DB.PORT,
                    user=settings.RELATIONAL_DB.USER,
                    password=settings.RELATIONAL_DB.PASSWORD,
                    name=settings.RELATIONAL_DB.DB,
                )
            )
        elif action == "dropdb":  # noqa
            if settings.PROJECT.ENVIRONMENT == Environment.production.value:
                logger.error("Forbidden operation in Production Environment")
                return
            shell(
                "mysql -h {host} --port={port} -u{user} -p{password} -e "
                '"DROP DATABASE \\`{name}\\`;"'.format(
                    host=settings.RELATIONAL_DB.HOST,
                    port=settings.RELATIONAL_DB.PORT,
                    user=settings.RELATIONAL_DB.USER,
                    password=settings.RELATIONAL_DB.PASSWORD,
                    name=settings.RELATIONAL_DB.DB,
                )
            )
        elif action == "shell":
            cmd = "mysql -h {host} --port={port} -u {user} -p{password}".format(
                host=settings.RELATIONAL_DB.HOST,
                port=settings.RELATIONAL_DB.PORT,
                user=settings.RELATIONAL_DB.USER,
                password=settings.RELATIONAL_DB.PASSWORD,
            )
            shell(cmd)
        elif action == "execute-file":
            file_path = options["file-path"]
            if not file_path.startswith("/"):  # noqa
                raise CommandError("absolute path required")

            cmd = "mysql -h {host} --port={port} -u {user} -D {db_name} -p{password} <{file_path}".format(
                host=settings.RELATIONAL_DB.HOST,
                port=settings.RELATIONAL_DB.PORT,
                user=settings.RELATIONAL_DB.USER,
                password=settings.RELATIONAL_DB.PASSWORD,
                db_name=settings.RELATIONAL_DB.DB,
                file_path=file_path,
            )
            shell(cmd)
