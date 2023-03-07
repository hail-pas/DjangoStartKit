import os
import re
import logging
import pathlib

from django.core.management import BaseCommand

from conf.config import local_configs

src = local_configs.PROJECT.BASE_DIR

DIRS = ["apis", "common", "core", "conf", "deploy", "tasks", "storages", "third_apis", "scripts"]
FILES = [".gitignore", "manage.py", "pyproject.toml", "README.md", "Makefile", "start.sh"]

logger = logging.getLogger("manage.tools")


class Command(BaseCommand):
    help = """
    工具类
        copy-project: 复制项目框架
    """
    available_actions = [
        "copy-project",
    ]  # noqa

    def add_arguments(self, parser):
        parser.add_argument("action", nargs=1, type=str, choices=self.available_actions)
        parser.add_argument(
            "--name", action="store", help="project name to create",
        )
        parser.add_argument(
            "--dest", action="store", help="destination path to create project",
        )

    def handle(self, *args, **options):
        action = options["action"][0]
        if action == "copy-project":  # noqa
            name = options["name"]
            dest = options["dest"]
            self.copy_project(name, dest)

    @staticmethod
    def copy_project(name: str, dest: str):
        dest = pathlib.Path(dest)  # noqa
        if not dest.exists():
            logger.warning("路径不存在")
            return

        if not dest.is_dir():
            logger.warning("目标路径不是文件夹")
            return

        dest = dest.joinpath(name)

        if dest.exists():
            logger.warning("目标路径下已存在和项目名同名的文件夹")
            return

        dest.mkdir()

        def copy_file_in_dir(src_path: pathlib.Path, is_sub: bool = False):
            if "__pycache__" in str(src_path) or ".DS_Store" in str(src_path):
                return
            all_need = os.listdir(src_path)
            for need in all_need:
                if "__pycache__" in str(need) or ".DS_Store" in str(need):
                    continue
                if not is_sub and need not in FILES + DIRS:
                    continue
                current_src_path = src_path.joinpath(need)  # noqa

                src_path_finds = re.findall(".*?DjangoStartKit/(?P<appendix>.*)", str(current_src_path))
                src_appendix = src_path_finds[0] if src_path_finds else ""
                if (
                    src_appendix.endswith("development.yaml")
                    or src_appendix.endswith("test.yaml")
                    or src_appendix.endswith("production.yaml")
                ):
                    continue
                dest_path = dest.joinpath(src_appendix)

                if current_src_path.is_file():
                    if is_sub or need in FILES:
                        dest_file = dest_path.open(mode="w", encoding="utf-8")
                        with open(current_src_path, mode="r") as src_file:
                            for line in src_file:
                                dest_file.write(line)

                        dest_file.close()
                        # print("copied to ", dest_path, end="\n")

                elif current_src_path.is_dir():
                    if is_sub or need in DIRS:
                        dest_path.mkdir(exist_ok=True)
                        copy_file_in_dir(current_src_path, True)

        copy_file_in_dir(src)

        logger.info("Successful")
