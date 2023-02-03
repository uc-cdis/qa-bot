FROM quay.io/cdis/python:python3.9-buster-2.0.0

ENV appname=qabot

RUN pip install --upgrade pip
RUN pip install --upgrade poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc musl-dev libffi-dev openssl libssl-dev curl bash

RUN adduser --disabled-login --gecos '' qabotuser

RUN mkdir -p /opt/ctds/qabot

COPY . /opt/ctds/qabot

WORKDIR /opt/ctds/qabot

RUN poetry config virtualenvs.create false \
    && poetry install -vv --no-root --no-dev --no-interaction \
    && poetry show -v

ENTRYPOINT poetry run python qabot/qabot.py
