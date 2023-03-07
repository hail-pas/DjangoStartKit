"""
异步、定时 任务
"""
from typing import Dict, Callable, Optional

from common.types import StrEnumMore


class UsageError(Exception):
    """
    Usage Error
    """


class TaskType(StrEnumMore):
    timed = ("timed", "定时任务")
    asynchronous = ("asynchronous", "异步任务")


class Task:
    def __init__(
        self,
        type_: TaskType,
        function: Callable,
        cron: Optional[str] = "",
        description: Optional[str] = "",
        file_name: Optional[str] = "",
        **k8s_kwargs,
    ):
        self.type_ = type_
        self.function = function
        self.cron = cron
        self.description = description
        self.file_name = file_name
        self.k8s_kwargs = k8s_kwargs

    def __str__(self):
        return f"""
            "type": {self.type_.value},
            "function": {self.function.__name__},
            "cron": {self.cron},
            "description": {self.description},
            "file_name": {self.file_name},
            "k8s_kwargs": {self.k8s_kwargs}
            """


_task_map: Dict[str, Task] = {}


class TaskManager:
    @property
    def task_map(self) -> Dict:
        return _task_map

    def task(  # noqa
        self,
        name: Optional[str] = "",
        description: Optional[str] = "",
        type_: TaskType = TaskType.asynchronous,
        cron: str = None,
        **k8s_kwargs,
    ):
        def _1(func):
            # TODO 使用数据库保存
            global _task_map
            nonlocal name
            if not name:
                name = func.__doc__.strip()
            if not callable(func):
                raise UsageError("Task must be Callable!")

            if type_ is TaskType.timed and not cron:
                raise UsageError("Cron Task must specify cron rule!")

            # if name in _task_map:
            #     raise UsageError("Task name must be unique!")

            nonlocal description
            if not description:
                description = func.__doc__.strip()
            _task_map[name] = Task(type_, func, cron, description, func.__code__.co_filename, **k8s_kwargs)  # noqa

            def _2(*args, **kwargs):
                return func(*args, **kwargs)

            return _2

        return _1


task_manager = TaskManager()
