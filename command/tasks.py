import typer

tasks_create_typer = typer.Typer(short_help="任务创建")
task = tasks_create_typer.command


@task()
def create_sync_status_job():
    """
    状态同步
    """
    print("Success")
