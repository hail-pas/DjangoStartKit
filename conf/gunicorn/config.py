# coding=utf-8
import os

import django

# 把标准库中的thread/socket等给替换掉
from gevent import monkey

monkey.patch_all()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.conf import settings  # noqa

debug = settings.DEBUG
# //绑定与Nginx通信的端口
bind = settings.SERVER_URL
daemon = False

worker_class = "gevent"  # 默认为阻塞模式，最好选择gevent模式,默认的是sync模式
loglevel = "info"
# 访问日志路径
accesslog = "-"  # 表示标准输出
# 错误日志路径
errorlog = "-"
# 设置gunicorn访问日志格式，错误日志无法设置
access_log_format = "%(h)s %(r)s %(s)s %(M)s %(b)s"

# 最大请求数之和重启worker，防止内存泄漏
max_requests = 4096
# 随机重启防止所有worker一起重启：randint(0, max_requests_jitter)
max_requests_jitter = 512
graceful_timeout = 120
timeout = 180
keepalive = 5
