ARG BASE_IMAGE=DjangoStartKit:base
# optional environment: development、test、production
ARG ENVIRONMENT
FROM ${BASE_IMAGE}
ADD ./ /code
WORKDIR /code
RUN mkdir logs
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
RUN pip install -v poetry
ENV POETRY_VIRTUALENVS_CREATE=false
ENV environment ${ENVIRONMENT}
RUN poetry install
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "--config", "conf/gunicorn/config.py", "--log-config", "conf/gunicorn/logging.conf", "core.wsgi:application"]
# docker build --build-arg BASE_IMAGE="" ENVIRONMENT=""