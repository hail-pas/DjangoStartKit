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
        'mysql -h {host} --port={port} -u{user} -p{password} -e '
        '"CREATE DATABASE IF NOT EXISTS \\`{name}\\` '
        'default character set utf8mb4 collate utf8mb4_general_ci;"'.format(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            name=settings.DB_NAME
        )
    )


@db_typer.command("dropdb", short_help="删除数据库")
def drop_db():
    if settings.ENVIRONMENT == Environment.production.value:
        return "Forbidden operation in Production Environment"
    shell(
        'mysql -h {host} --port={port} -u{user} -p{password} -e '
        '"DROP DATABASE \\`{name}\\`;"'.format(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            name=settings.DB_NAME
        )
    )


@db_typer.command("shell", short_help="Mysql命令行")
def _shell():
    cmd = "mysql -u {user} -p{password}".format(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    shell(cmd)
