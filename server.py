import uvicorn

from conf.config import local_configs
from core.asgi import application
from django.core.management import call_command

app = application

if __name__ == "__main__":
    call_command('migrate')
    uvicorn.run(
        app="server:app",
        host=local_configs.SERVER.HOST,
        port=local_configs.SERVER.PORT,
        debug=local_configs.PROJECT.DEBUG,
        workers=local_configs.SERVER.WORKERS_NUM,
        log_level="debug" if local_configs.PROJECT.DEBUG else "info",
        use_colors=True if local_configs.PROJECT.DEBUG else False,
    )

