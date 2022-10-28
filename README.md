# DjangoStartKit

[![Code style: black](https://img.shields.io/badge/DjangoStartKit-v0.01-green)](https://github.com/hail-pas/DjangoStartKit)
[![Code style: black](https://img.shields.io/badge/Python-3.9-blue)](https://github.com/python/cpython)
[![Code style: black](https://img.shields.io/badge/Django-3.2.9-blue)](https://github.com/django/django)
[![Code style: black](https://img.shields.io/badge/djangorestframework-3.12.4-blue)](https://github.com/encode/django-rest-framework)
[![Code style: black](https://img.shields.io/badge/redisearch-2.1.1-blue)](https://github.com/RediSearch/RediSearch)
[![Code style: black](https://img.shields.io/badge/gunicorn-20.1.0-blue)](https://github.com/benoitc/gunicorn)

> 项目创建、开发参考文档，目的在于快速上手、敏捷开发，尽可能减少后续沟通、维护和运维成本
> DJango + djangorestframework
> base 分支：不带websocket，websocket 分支：整合websocket

## 快速启动
```shell
# 复制对应方式的默认配置文件并修改
cp conf/content/default_template.json conf/content/development.json  # 普通json 方式配置
# cp conf/content/consul_template.json conf/content/development_consul.json  conusl 方式配置

python -m venv ./venv  # 创建虚拟环境
pip install poetry && poetry update  # 安装依赖
chmod +x ./start.sh && ./start.sh  # 启动
```

## Makefile
```shell
make check  # 代码检测
make style  # 代码统一格式化
make up  # 依赖更新
make deps  # 依赖安装
```

## 版本

### Python
3.9.12

### Django
3.2.9

### djangorestframework
3.12.4

## 部署Dockerfile
> 基础镜像 + 业务代码镜像，不同的环境传递 build-arg 参数

### 文件目录
```shell
{{project}}/deploy/docker/back-end-base.Dockerfile
{{project}}/deploy/docker/back-end.Dockerfile
```
### back-end-base.Dockerfile
```Dockerfile
FROM python:3.9.12
ADD ./ /code
WORKDIR /code
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
RUN pip install -v poetry
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install
```

### back-end.Dockerfile

```Dockerfile
# docker build --build-arg BASE_IMAGE="" -build-arg ENVIRONMENT=""
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
# optional environment: development、test、production;  From 为变量作用域
ARG ENVIRONMENT
ENV environment ${ENVIRONMENT}
ADD ./ /code
WORKDIR /code
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
RUN pip install -v poetry
RUN poetry install
# RUN python manage.py migrate  使用 Django 自带的 call_command 执行
EXPOSE 8000
RUN chmod +x start.sh
#CMD ["gunicorn", "--config", "conf/gunicorn/config.py", "--log-config", "conf/gunicorn/logging.conf", "core.wsgi:application"]
CMD ["./start.sh"]
```

## 配置管理
> 可以类型检查 和 启动时检测必填项；django默认的配置和代码混合不方便管理，将配置项和代码独立，类和配置进行映射

可选方式：
- pydantic + json
- consul + json

### 配置文件目录
```shell
{{project}}/conf/content/{{environment}}.json
# 可选environment：development、test、prodcution；
# 与Dockerfile 的 ENVIRONMENT ARG一致
```

### 配置解析文件
```shell
{{project}}/conf/config.py
# 根据需求复制config_consul.py 或 config_pydantic.py 到 config.py
```

### 示例Pydantic Model
```python
class LocalConfig(BaseSettings):
    """
    全部的配置信息
    """
    PROJECT: Project

    RELATIONAL_DB: RelationalDb

    REDIS: Optional[Redis]

class Project(BaseModel):
    NAME: str = "DjangoStartKit"
    DEBUG: bool = False
    ENVIRONMENT: str = Environment.production.value
    DESCRIPTION: str = "Django-start-kit"
    LANGUAGE_CODE: str = "zh-hans"
    TIME_ZONE: str = "Asia/Shanghai"
    USE_TZ: str = False
    BASE_DIR = BASE_DIR

class HostAndPort(BaseModel):
    HOST: str
    PORT: Optional[int]

class RelationalDb(HostAndPort):
    USER: str
    PASSWORD: str
    DB: str

class Redis(HostAndPort):
    USERNAME: Optional[str] = None
    PASSWORD: Optional[str] = None
    DB: int = 0

settings = LocalConfig()
```

### 示例json
```json
{
  "RELATIONAL": {
    "HOST": "localhost",
    "PORT": 3306,
    "USERNAME": "root",
    "DB": "django-start-kit",
    "PASSWORD": "pwd"
  },
  "REDIS": {
    "HOST": "localhost",
    "PORT": 6379,
    "DB": 0,
    "PASSWORD": "pwd"
  },
  "OSS": {
    "ACCESS_KEY_ID": "",
    "ACCESS_KEY_SECRET": "",
    "ENDPOINT": "",
    "BUCKET_NAME": "",
    "BUCKET_ACL_TYPE": "private",
    "EXPIRE_TIME": 300
  }
}
```

## 依赖管理 - poetry

```shell
# 初始化
poetry init
# lock文件生成
poetry lock
# 安装
poetry install
# 更新依赖
poetry update
# 清除缓存
poetry cache clear . --all
```

## 响应体

http状态码只使用 200、400、401、403，错误全部捕获
- 200 表示成功的请求，响应体包含 code 业务状态码，唯一成功业务状态为0，其余场景自定义
- 400 表示请求参数错误
- 401 表示用户授权信息错误
- 403 表示用户无权限

### 无分页信息响应结构
```python
class _Resp(BaseModel):
    """"
    响应体格式
    res = {
        "code": 0,
        "success": True
        "message": "message",
        "data": "data",
        }
    """

    code: int = ResponseCodeEnum.success.value
    success: bool = True
    message: Optional[str] = "success"
    timestamp: str
    data: Optional[Any] = None
```

### 带分页信息响应结构
```python
class _PageInfo(BaseModel):
    """
    翻页相关信息
    """

    total_page: int
    total_count: int
    page_size: int
    page_num: int

class _Resp(BaseModel):
    """"
    响应体格式
    res = {
        "code": 0,
        "success": True
        "message": "message",
        "data": "data",
        "page_info": "page_info"  # 可选
        }
    """

    code: int = ResponseCodeEnum.success.value
    success: bool = True
    message: Optional[str] = "success"
    timestamp: str
    data: Optional[Any] = None
    page_info: Optional[_PageInfo] = None
```

## 脚本
> 脚本文件集中，脚本一般可分为 初始化脚本、版本迭代脚本、工具脚本
```shell
# 脚本根目录
{{project}}/scripts/
# 初始化脚本
{{project}}/scripts/initial/*
# 工具脚本, 另外的推荐做法是整合进django-manage命令
{{project}}/scripts/tools/*
# 版本迭代脚本
{{project}}/scripts/release/{{version}}/*
```

## 定时/异步任务
> K8s 创建任务封装

### 目录
```shell
{{project}}/tasks/asynchronous/
{{project}}/tasks/timed/
{{project}}/tasks/yaml_template/
# 使用 @task_manager.task 装饰器注册任务
# 使用 django-manage 命令管理命令
python manage.py tasks
```

## 权限管理

> 基于 RBAC，高并发需求不高的前提；兼容django原生权限

### 接口权限
> 权限控制粒度：API，可以自定义实现到更细的 API+参数 粒度

### 数据库ER

![Alt text](https://i.imgur.com/F3T9PM7.png "django-start-kit-perms")

### 配置使用

1. 系统用于多子系统业务场景，单系统情况下可忽略，默认为项目名称
2. 配合 token 使用，每一个用户 token 的 payload 都会携带 system 和 scene，通过 Authenticate 中间件解析，并保存到请求上下文

```python
payload = {
    'user_id': 1,
    'username': 'admin',
    'exp': "2022-09-16 15:24:53",
    'email': 'example@example.com',
    'phone': 'admin',
    'system': 'DjangoStartKit',
    'scene': 'user'
}
# 解析token之后将 system 和 scene 赋值到request
# 这里会校验用户 token 携带 system 和 scene 的合法性
request.system = payload["system"]
request.scene = payload["scene"]
```

3. 生成权限
```shell
# 脚本直接生成 permission ，沿用的 django permission
# codename 为 f"{view.__module__}.{view.__class__.__name__}.{action}"
# codename示例：apis.account.views.ProfileViewSet.reset_password
# name 为接口描述
python manage.py generate-api-perms
```

4. 配置
```python
# 将权限和系统资源关联上，用户只需要关注于分配系统资源而无需关心有哪些权限
# 另外可以在settings文件中配置免校验的 module、class、action，任一匹配则不校验
URI_PERMISSION_AUTHENTICATE_EXEMPT = {
    "modules": [],
    "classes": [],
    "actions": ["self"],
}
```

### 数据权限
> 数据权限场景比较业务强相关
参考：可以配合 request.scene、request.system 为 get_queryset 函数编写针对性的装饰器

## 项目目录

### 以该项目为模版快速建立新项目
```shell
python manage.py tools copy-project --name [project-name] --dest [absolute-dest-path]
```

### 常用自定义django-manage命令
```shell
python manage.py
  |-serverstart
  |-generate-api-perms
  |-mysql
  |----|--createdb
  |----|--dropdb
  |----|--shell
  |----|--execute-file --file-path [path]
  |-redis
  |----|--shell
  |-tasks
  |----|--show-all-jobs
  |----|--create-job
  |----|--create-all-job
  |-tools
  |----|--copy-project --name [project-name] --dest [absolute-dest-path]
```

### 目录结构
```shell
|-- apis
|       |-- 模块 API<br>
|-- common
|       |-- 通用模块（自定义swagger装饰器、类型、加解密函数、工具）<br>
|-- conf
|       |-- 配置相关（Pydantic加载时校验配置生成 local_settings）<br>
|-- core
|       |-- Core目录（中间件、根urls、service exception）<br>
|-- deploy
|       |-- 部署相关（Dockerfile、K8S yaml）<br>
|-- logs
|       |-- Error错误日志收集 <br>
|-- scripts
|       |-- 初始化/发版等脚本 <br>
|-- storages
|       |-- 存储相关(Hbase、Redis、Oss、Mysql) 以及 自定义 manage.py 命令<br>
|-- tasks
|       |-- 异步、定时任务目录<br>
|-- third_apis
|       |-- 对接第三方接口<br>
|- Makefile<br>
|- manage.py<br>
|- poetry.toml 依赖定义文件<br>
|- project.lock 依赖管理文件<br>
|- README.md<br>
```

### apis
```shell
apis
├── __init__.py
├── account            # 用户api
├── auth               # 授权api
├── chat               # websocket consumer 封装
├── info               # 返回定义的choices 以及 其他业务无关的信息数据
├── permissions.py     # 权限类定义 URIBasedPermission、AuthorizedServicePermission
└── responses.py       # 响应结构定义
```

### common
```shell
common
├── __init__.py
├── decorators.py          # 装饰器函数
├── django
│   ├── __init__.py
│   ├── mixins.py          # Django Mixin
│   ├── paths.py           # 遍历获取接口path
│   └── perms.py           # permission backend 函数
├── drf
│   ├── __init__.py
│   ├── filters.py         # drf 自定义filters
│   ├── mixins.py          # DRF Mixins
│   └── serializers.py     # drf 自定义通用 serializer
├── encrypt.py             # 加密工具函数
├── k8s_api.py             # k8s 封装API
├── messages.py            # 所有的响应message集中定义
├── schemas.py             # 通用请求schema
├── signed_request.py      # 签名请求requests.request
├── types.py               # 自定义通用类型
├── utils.py               # 工具函数合集
└── validators.py          # 校验函数：正则等
```

### conf
```shell
conf
├── config.py                # 配置映射类定义
├── content                  # 配置文件目录
│   ├── development.yaml
│   └── template.yaml
├── enums.py                 # 配置相关常量定义
└── gunicorn                 # gunicorn配置
    ├── __pycache__
    ├── config.py
    └── logging.conf
```

### core
```shell
core
├── __init__.py
├── asgi.py
├── authenticate.py            # 权限校验
├── exceptions.py              # 自定义业务Exception
├── main.py                    # 启动入口main
├── middlewares.py             # 中间件
├── restful                    # Swagger、日志格式等设置
│   ├── __init__.py
├── settings.py
├── urls.py
└── wsgi.py
```

### deploy
```shell
deploy
└── docker
     ├── back-end-base.Dockerfile    # 基础镜像Dockerfile
     ├── back-end.Dockerfile         # 业务代码镜像Dockerfile
```

### scripts
```shell
scripts
├── django_setup.py    # django setup
└── initial            # 初始化脚本目录
```

### storages
```shell
storages
├── __init__.py
├── enums.py                # choices 定义
├── hbase
│   ├── __init__.py
│   └── models.py           # hbase model 定义
├── mysql                   # 作为数据管理APP注册
│   ├── __init__.py
│   ├── admin.py            # 系统统一admin
│   ├── apps.py
│   ├── base.py             # mysql 通用model
│   ├── management          # django manage,py 命令整合
│   │   ├── __init__.py
│   │   └── commands
│   │       ├── __init__.py
│   │       ├── generate-api-perms.py
│   │       ├── mysql.py
│   │       ├── redis.py
│   │       ├── serverstart.py
│   │       ├── tasks.py
│   │       └── tools.py
│   ├── migrations           # 迁移文件
│   ├── models               # models 定义
│   │   ├── __init__.py      # 需要导入到__init__
│   │   ├── account.py
│   │   ├── chat.py
│   │   └── info.py
│   └── validators.py        # django model validators
├── oss                      # 待封装 OSS
│   ├── __init__.py
└── redis                    # Redis
    ├── __init__.py          # 同步/异步 Redis 示例， RedisUtil.r.xxx
    ├── keys.py              # redis 缓存 key 定义
    └── redis_serach.py      # redis-search
```

### task
```shell
task
├── __init__.py
├── asynchronous
├── timed
└── yaml_template
    ├── cronjob_template.yaml
    └── job_template.yaml
```

#### 示例
```python
from tasks import TaskType, task_manager


@task_manager.task(
    name="任务唯一名称",
    type_=TaskType.timed,
    description="描述",
    cron="30 * * * *"
)
def some_task():
    """
    description
    """
    pass
```

### third_apis
```shell
third_apis
├── __init__.py
```

#### 示例
```python
from third_apis import Third, API
class GoogleAPI(Third):
    @abc.abstractmethod
    def search(self, *args, **kwargs)  -> DefaultResponse:
        pass

google_apis = [
    API("search", method="GET", uri="/search", response_cls=DefaultResponse)
]

google_api = GoogleAPI(
    name="GoogleAPI",
    protocol="https",  # htpp、rpc
    host="www.google.com",
    port=None,
    response_cls=DefaultResponse,
    timeout=6,
    request=requests.request,
    headers={"auth": ":"},
)
for api in google_apis:
    google_api.register_api(api)

response = google_api.search(params={"q": "test"})
```
