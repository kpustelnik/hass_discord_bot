FROM python:3.12.9-slim-bookworm

WORKDIR /app
COPY . /app

RUN python -m pip install -r requirements.txt

ENTRYPOINT [ "python", "main.py" ]