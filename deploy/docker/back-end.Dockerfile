ARG BASE_IMAGE=DjangoStartKit:base
FROM ${BASE_IMAGE}
ADD ./ /code
WORKDIR /code
RUN mkdir logs
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
RUN pip install -v poetry
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "--config", "conf/gunicorn/config.py", "--log-config", "conf/gunicorn/logging.conf", "core.wsgi:application"]
