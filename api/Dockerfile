FROM python:3.8-alpine3.11

WORKDIR /api

COPY requirements.txt ./

RUN apk add --update build-base libffi-dev && \
    rm -rf /var/cache/apk/*

RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "main:create_app", "--bind", "0.0.0.0:80", "--worker-class", "aiohttp.GunicornWebWorker"]
