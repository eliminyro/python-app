FROM python:3.10.0-alpine

RUN adduser pyapp -D

USER pyapp

WORKDIR /app

COPY ./app/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./app/ .

CMD ["python3", "app.py"]