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