import pathlib
import subprocess
from functools import partial

import typer

from conf.enums import Environment
from conf.config import local_configs as settings

db_typer = typer.Typer(short_help="MySQL相关")

shell = partial(subprocess.run, shell=True)

default_sql_base_path = pathlib.Path(__file__).parent.parent.joinpath(pathlib.Path("initials/sql")).as_posix()


@db_typer.command("createdb", short_help="创建数据库")  # noqa
def create_db():
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


@db_typer.command("dropdb", short_help="删除数据库")  # noqa
def drop_db():
    if settings.PROJECT.ENVIRONMENT == Environment.production.value:
        print("Forbidden operation in Production Environment")
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


@db_typer.command("shell", short_help="Mysql命令行")
def _shell():
    cmd = "mysql -h {host} --port={port} -u {user} -p{password}".format(
        host=settings.RELATIONAL_DB.HOST,
        port=settings.RELATIONAL_DB.PORT,
        user=settings.RELATIONAL_DB.USER,
        password=settings.RELATIONAL_DB.PASSWORD,
    )
    shell(cmd)


@db_typer.command("execute-file", short_help="Mysql脚本执行")
def execute_file(file_path: str = typer.Option(default="", help="文件路径, 以/开头则为绝对路径否则以initials的sql为起始目录")):
    if not file_path.startswith("/"):
        file_path = default_sql_base_path + "/" + file_path

    cmd = "mysql -h {host} --port={port} -u {user} -D {db_name} -p{password} <{file_path}".format(
        host=settings.RELATIONAL_DB.HOST,
        port=settings.RELATIONAL_DB.PORT,
        user=settings.RELATIONAL_DB.USER,
        password=settings.RELATIONAL_DB.PASSWORD,
        db_name=settings.RELATIONAL_DB.DB,
        file_path=file_path,
    )
    shell(cmd)
