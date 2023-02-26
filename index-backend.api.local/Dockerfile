FROM python:alpine3.16

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt && \
    apk update && \
    apk add bind-tools curl
COPY app.py  .

CMD flask run -h 0.0.0.0 -p 5000