# DjangoStartKit

[![Code style: black](https://img.shields.io/badge/DjangoStartKit-v0.01-green)](https://github.com/hail-pas/DjangoStartKit)
[![Code style: black](https://img.shields.io/badge/Python-3.9-blue)](https://github.com/python/cpython)
[![Code style: black](https://img.shields.io/badge/Django-3.2.9-blue)](https://github.com/django/django)
[![Code style: black](https://img.shields.io/badge/djangorestframework-3.12.4-blue)](https://github.com/encode/django-rest-framework)
[![Code style: black](https://img.shields.io/badge/redisearch-2.1.1-blue)](https://github.com/RediSearch/RediSearch)
[![Code style: black](https://img.shields.io/badge/gunicorn-20.1.0-blue)](https://github.com/benoitc/gunicorn)

<br>Django Quick Start Kit<br>

# 目录结构

|-- apps<br>
|       |-- 子App API<br>
|-- command<br>
|       |-- 命令行工具（MySQL、Redis、Hbase、K8S任务创建）<br>
|-- common<br>
|       |-- 通用模块（自定义swagger装饰器、类型、加解密函数）<br>
|-- conf<br>
|       |-- 配置相关（Pydantic加载时校验配置生成 local_settings、配置项在根目录 .env）<br>
|-- core<br>
|       |-- 主App目录<br>
|-- deploy<br>
|       |-- 部署相关（Dockerfile、K8S yaml）<br>
|-- storages<br>
|       |-- 存储相关(Hbase、Redis、Oss、Mysql)<br>
|-- tasks<br>
|       |-- 异步、定时任务实现目录<br>
|-- third_apis<br>
|       |-- 对接三方http接口<br>
|- command.py 命令行工具<br>
|- Makefile<br>
|- manage.py<br>
|- poetry.toml 依赖定义文件<br>
|- project.lock 依赖管理文件<br>
|- README.md<br>

# 快速启动

```shell script
# 复制配置并填充
cp conf/envs/.env.template conf/envs/${environment}.env

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install poetry
poetry update

# 创建数据库
python command.py mysql createdb
python manage.py migrate
```

# 依赖管理 poetry

## 增加依赖

```shell
# 搜索
poetry search target-pack
# 增加
poetry add target-pack[==version]
```

## 安装依赖:

```shell
# python 3.9
pip install poetry   # 安装 poetry 依赖管理工具
poetry update  # 等价于 poetry lock && poetry install
```

# 代码管理 Makefile/git

```shell
# 更新依赖
make up
# 安装依赖
make deps
# 检查代码
make chcek
# 格式化, 需要忽略的不规范格式化使用注释 #noqa
make style
```

# Response 格式化

使用统一的 Response 类<br>
将分页响应信息单独提出来: apps.responses._Page_info<br>
分页参数统一化: <br>        常规 page 分页 - apps.common.schemas.PageParam, <br>       hbase分页 - apps.common.schemas.HbasePageParam

```python
from apps.responses import RestResponse


def view_func(self, *args, **kwargs):
    return RestResponse.ok(data={"foo": "bar"})
```

# CURD 接口

使用重写之后的viewMixin, 返回的统一响应体结构，list接口增加指定字段返回
所有 choices 候选集数据都定义在 apps.enums 文件下

```python
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny

from apps.account import models, serializers
from common.drf.mixins import RestModelViewSet


class ProfileViewSet(
    RestModelViewSet,
):
    """账号接口
    """
    serializer_class = serializers.ProfileSerializer
    queryset = models.Profile.objects.all()
    search_fields = ('phone', 'name')
    filter_fields = ('roles',)
    parser_classes = (JSONParser,)
    permission_classes = (AllowAny,)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.ProfileListSerializer
        return self.serializer_class

```

# 接口文档

使用 custom_swagger_auto_schema 对接口装饰, <br>该装饰器装饰@action 或 @api_view的接口时会调用自定义中间件对GET query_params 和 json 传输的 body 进行指定的
serializer 自动校验, 并存入 request.param_data 和 request.body_data;<br>
增加额外参数 page_info, 指明接口响应体会包含 PageInfo 信息

```python
from drf_yasg import openapi
from rest_framework import status
from rest_framework.decorators import api_view

from apps.enums import get_enum_content
from apps.info import schemas
from apps.responses import RestResponse
from common.swagger import custom_swagger_auto_schema


@custom_swagger_auto_schema(
    tags=["info"],
    method="GET",
    query_serializer=schemas.EnumQueryIn,
    responses={
        status.HTTP_200_OK: openapi.Response(  # noqa
            description="返回 Json 格式的码表",
            examples={
                "application/json": RestResponse.ok(
                    data={
                        "ResponseCodeEnum": {
                            "100200": "成功",
                            "100999": "失败"
                        }
                    }
                ).dict()
            },

        )
    },
    page_info=False,
)
@api_view(["GET"])
def enums(request, *args, **kwargs):
    return RestResponse.ok(data=get_enum_content(request.param_data["enum_name"], request.param_data["is_inversed"]))
```

# 数据读写

storages 模块<br>
hbase 实现简单序列化, 自动生成 swagger 的响应 schema 待完善, 之前使用的是 pydantic 需要转换成 serializer<br>
redis 使用统一的 storages.redis.RedisUtil 进行操作, 全部 key 定义在 storages.redis.keys.RedisCacheKey<br>

```python
# hbase
from storages.hbase import BaseModel


class AntiTamperQueryData(BaseModel):
    vin = ("a01", "车架号")
    obd_time = ("a02", "obd上传时间")
    create_time = ("a03", "创建时间")
    tboxSn = ("b01", "终端设备编号")
    chip_id = ("b02c", "芯片ID")
    raw_data = (b"B:a01", "原始报文",)

    class Meta:
        table_name = "test_qiye6_anti_query"
        column_family_name = "A"
        row_key_format = "{vin}__{create_datetime}"
        hex_fields = ["raw_data"]


# redis
from storages.redis.keys import RedisCacheKey
from storages.redis import RedisUtil

RedisUtil.set(RedisCacheKey.redis_lock.format("lock_target"))
```

# 定时任务

tasks/timed 定时任务
tasks/asynchronous 异步任务

```python
from tasks import TaskType, task_manager


@task_manager.task(
    name="信息同步",
    type_=TaskType.timed,
    description="调用接口同步数据",
    cron="30 * * * *"
)
def info_sync():
    """
    调用接口同步数据 description
    """
    pass


@task_manager.task(
    name="异步任务",
    type_=TaskType.asynchronous,
    description="异步任务示例",
)
def async_task():
    """
    异步任务示例 description
    """
    pass

```
