import uvicorn
from django.core.management import call_command

from core.asgi import application
from conf.config import local_configs

app = application


def run():
    call_command("collectstatic", "--noinput")  # noqa
    call_command("migrate")
    print("=" * 50)
    print(local_configs.dict())
    print("=" * 50)
    uvicorn.run(
        app="core.main:app",
        host=local_configs.SERVER.HOST,
        port=local_configs.SERVER.PORT,
        debug=local_configs.PROJECT.DEBUG,
        reload=local_configs.PROJECT.DEBUG,
        workers=local_configs.SERVER.WORKERS_NUM,
        log_level="debug" if local_configs.PROJECT.DEBUG else "info",
        use_colors=True if local_configs.PROJECT.DEBUG else False,
    )


if __name__ == "__main__":
    run()
