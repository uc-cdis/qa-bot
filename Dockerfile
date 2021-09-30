FROM quay.io/cdis/python-nginx:master

ENV appname=qabot

ENV DEBIAN_FRONTEND=noninteractive

RUN adduser -D -g '' qabotuser

RUN mkdir -p /opt/ctds/qabot \
    && chown qabotuser /opt/ctds/qabot

COPY . /opt/ctds/qabot
WORKDIR /opt/ctds/qabot

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev openssl-dev curl

USER qabotuser

RUN pip install --upgrade pip

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

# cache so that poetry install will run if these files change
COPY poetry.lock pyproject.toml /opt/ctds/qabot/

# install qa-bot and dependencies via poetry
RUN source $HOME/.poetry/env \
    && poetry install --no-dev --no-interaction \
    && poetry show -v

WORKDIR /opt/ctds/qabot/qabot

ENTRYPOINT source $HOME/.poetry/env && poetry run python3.6 qabot.py
