import typer

from command.mysql import db_typer
from command.redis import redis_typer
from command.tasks import tasks_create_typer
from command.tools import tool_typer

cli = typer.Typer()

cli.add_typer(tool_typer, name="tools")
cli.add_typer(db_typer, name="mysql")
cli.add_typer(redis_typer, name="redis")
cli.add_typer(tasks_create_typer, name="tasks")
