FROM python:3.7.3-alpine3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py  .

CMD flask run -h 0.0.0.0 -p 5000