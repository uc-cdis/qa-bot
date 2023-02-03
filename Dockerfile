FROM quay.io/cdis/python:python3.9-buster-master

ENV appname=qabot

ENV DEBIAN_FRONTEND=noninteractive

RUN adduser --disabled-login --gecos '' qabotuser

RUN mkdir -p /opt/ctds/qabot \
    && chown qabotuser /opt/ctds/qabot

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

COPY . /opt/ctds/qabot
WORKDIR /opt/ctds/qabot

RUN     apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc musl-dev libffi-dev openssl-dev curl

USER qabotuser

RUN pip install --upgrade pip poetry

# cache so that poetry install will run if these files change
COPY poetry.lock pyproject.toml /opt/ctds/qabot/

RUN poetry config virtualenvs.create false \
    && poetry install -vv --no-root --no-dev --no-interaction \
    && poetry show -v

WORKDIR /opt/ctds/qabot/qabot

ENTRYPOINT poetry run python qabot.py
