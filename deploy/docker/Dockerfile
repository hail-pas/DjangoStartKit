FROM python:3.9
ADD ./ /code
WORKDIR /code
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
RUN pip3 install poetry
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install
#CMD ["gunicorn", "--config", "./deploy/gunicorn/conf.py", "--log-config", "./deploy/gunicorn/logging.conf", "main:app"]