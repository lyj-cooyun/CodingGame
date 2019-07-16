FROM python:2.7

EXPOSE 8000
RUN mkdir /app
WORKDIR /app
ADD ./ColorFight/requirements.txt /app
RUN pip install -r requirements.txt
ADD ./ColorFight /app

ENTRYPOINT ["gunicorn", "-k",  "gevent", "-w", "2", "-b", "0.0.0.0:8000",  "wsgi:wsgi"]
