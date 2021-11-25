import subprocess

import typer

from functools import partial
from conf.config import local_configs as settings
from conf.enums import Environment

redis_typer = typer.Typer(short_help="Redis相关")

shell = partial(subprocess.run, shell=True)


@redis_typer.command("shell", short_help="Redis命令行")
def _shell(db: int = typer.Option(default=0, help="指定数据库")):
    if settings.REDIS_PASSWORD:
        cmd = "redis-cli -h {host} -p {port} -a {password} -n {db}".format(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=db,
        )
    else:
        cmd = "redis-cli -h {host} -p {port} -n {db}".format(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=db,
        )
    shell(cmd)
