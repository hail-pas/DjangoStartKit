# DjangoStartKit
Django Quick Start Kit

# 目录结构
|-- apps
|    |-- 子App API
|-- command
|    |-- 命令行工具（MySQL、Redis、Hbase、K8S任务创建）
|-- common
|    |-- 通用模块（自定义swagger装饰器、类型、加解密函数）
|-- conf
|    |-- 配置相关（Pydantic加载时校验配置生成 local_settings、配置项在根目录 .env）
|-- core
|    |-- 主App目录
|-- deploy
|    |-- 部署相关（Dockerfile、K8S yaml）
|-- storage
|    |-- 存储相关(Hbase、Redis、Oss、Mysql)
|-- tasks
|    |-- 异步、定时任务实现目录
|- command.py 命令行工具
|- main.py
|- manage.py
|- poetry.toml 依赖定义文件
|- project.lock 依赖管理文件
|- README.md


# 依赖管理 poetry
## 增加依赖
```shell
# 搜索
poetry search target-pack
# 增加
poetry add target-pack[==version]
```
## 安装更新依赖:
```shell
poetry update
```
# Response 格式化
使用统一的 Response 类
将分页响应信息单独提出来: apps.responses._Page_info
分页参数统一化: 常规 page 分页 - apps.common.schemas.PageParam, hbase分页 - apps.common.schemas.HbasePageParam
```python
from apps.responses import RestResponse

def view_func(self, *args, **kwargs):
    return RestResponse.ok(data={"foo": "bar"})
```

# CURD 接口
使用重写之后的viewMixin, 返回的统一响应体结构，list接口增加指定字段返回
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
使用 custom_swagger_auto_schema 对接口装饰, 使用该装饰器时会对GET query_params 和 json 传输的 body 进行指定的 serializer 自动校验, 并存入 request.param_data 和 request.body_data;
增加额外参数 page_info
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
storages 模块
hbase 实现简单序列化, 自动生成 swagger 的响应 schema 待完善, 我之前使用的是 pydantic 需要转换成 serializer
redis 使用统一的 storages.redis.RedisUtil 进行操作, 全部 key 定义在 storages.redis.keys.RedisCacheKey
```python
# hbase
from storages.hbase import BaseModel

class FaultRecordData(BaseModel):
    vin = b"A:a01"
    unique_code = b"A:a02"
    first_alert_time = b"A:a03"
    obd_time = b"A:a04"
    receive_time = b"A:a05"

    class Meta:
        table_name = "fault_record"
        row_key_format = "{vin}__{create_datetime}"

# redis
from storages.redis.keys import RedisCacheKey
from storages.redis import RedisUtil

RedisUtil.set(RedisCacheKey.redis_lock.format("lock_target"))
```