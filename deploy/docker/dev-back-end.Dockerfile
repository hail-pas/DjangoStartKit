FROM 192.168.3.22/xev/dev-xev-back:base
ADD ./ /code
WORKDIR /code
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
RUN pip install -v --trusted-host mirrors.aliyun.com -i http://mirrors.aliyun.com/pypi/simple poetry
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install
#RUN python manage.py migrate
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["python", "main.py"]
