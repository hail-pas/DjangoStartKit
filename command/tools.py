import os
import re
import pathlib

import typer

tool_typer = typer.Typer(short_help="工具")

src = pathlib.Path(__file__).parent.parent

DIRS = ["apps", "command", "common", "core", "conf", "deploy", "tasks", "storages", "third_apis"]
FILES = [".dockerignore", ".gitignore", "manage.py", "command.py", "pyproject.toml", "main.py", "README.md", "Makefile"]


@tool_typer.command("copy-project", short_help="复制脚手架项目并指明项目名称目标文件夹路径")
def copy_project(
    name: str = typer.Option(default=None, help="项目名称"), dest: str = typer.Option(default=None, help="目标路径")
):
    if not (name and dest):
        print("必须指定项目名称name和目标路径dest")
        return

    dest = pathlib.Path(dest)
    if not dest.exists():
        print("路径不存在")
        return

    if not dest.is_dir():
        print("目标路径不是文件夹")
        return

    dest = dest.joinpath(name)

    if dest.exists():
        print("目标路径下已存在和项目名同名的文件夹")
        return

    dest.mkdir()

    def copy_file_in_dir(src_path: pathlib.Path, is_sub: bool = False):
        if "__pycache__" in str(src_path) or ".DS_Store" in str(src_path):
            return
        all_need = os.listdir(src_path)
        for need in all_need:
            if not is_sub and need not in FILES + DIRS:
                continue
            current_src_path = src_path.joinpath(need)
            src_path_finds = re.findall(".*?DjangoStartKit/(?P<appendix>.*)", str(current_src_path))
            src_appendix = src_path_finds[0] if src_path_finds else ""
            dest_path = dest.joinpath(src_appendix)

            if current_src_path.is_file():
                if is_sub or need in FILES:
                    dest_file = dest_path.open(mode="w", encoding="utf-8")
                    with open(current_src_path, mode="r") as src_file:
                        for line in src_file:
                            dest_file.write(line)

                    dest_file.close()
                    print("copied to ", dest_path, end="\n")

            elif current_src_path.is_dir():
                if is_sub or need in DIRS:
                    dest_path.mkdir(exist_ok=True)
                    copy_file_in_dir(current_src_path, True)

    copy_file_in_dir(src)

    print("Successful")
