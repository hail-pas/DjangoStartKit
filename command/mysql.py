import subprocess
from functools import partial

import typer
from conf.config import local_configs as settings
from conf.enums import Environment

db_typer = typer.Typer(short_help="MySQL相关")

shell = partial(subprocess.run, shell=True)


@db_typer.command("createdb", short_help="创建数据库")
def create_db():
    shell(
        'mysql -h {HOST} --port={PORT} -u{USER} -p{PASSWORD} -e '
        '"CREATE DATABASE IF NOT EXISTS \\`{database}\\` '
        'default character set utf8mb4 collate utf8mb4_general_ci;"'.format(
            **settings.DATABASES.get("default")
        )
    )


@db_typer.command("dropdb", short_help="删除数据库")
def drop_db():
    if settings.ENVIRONMENT == Environment.production.value:
        return "Forbidden operation in Production Environment"
    shell(
        'mysql -h {HOST} --port={PORT} -u{USER} -p{PASSWORD} -e '
        '"DROP DATABASE \\`{database}\\`;"'.format(
            **settings.DATABASES.get("default")
        )
    )


@db_typer.command("shell", short_help="Mysql命令行")
def _shell(db: int = typer.Option(default=0, help="指定数据库")):
    cmd = "mysql -u {user} -p{password}".format(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    shell(cmd)
