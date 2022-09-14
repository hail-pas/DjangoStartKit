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
RUN python manage.py collectstatic --noinput
# RUN python manage.py migrate  使用 Django 自带的 call_command 执行
EXPOSE 8000
#CMD ["gunicorn", "--config", "conf/gunicorn/config.py", "--log-config", "conf/gunicorn/logging.conf", "core.wsgi:application"]
#CMD ["daphne", "--bind", "0.0.0.0", "--port", "8000", "core.asgi:application"]
CMD ["python", "server.py"]