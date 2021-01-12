FROM quay.io/cdis/python-nginx:master

ENV appname=qabot

ENV DEBIAN_FRONTEND=noninteractive

RUN adduser -D -g '' qabotuser

RUN mkdir -p /opt/ctds/qabot \
    && chown qabotuser /opt/ctds/qabot

COPY . /opt/ctds/qabot
WORKDIR /opt/ctds/qabot

RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev openssl-dev curl

USER qabotuser

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
COPY . /opt/ctds/qabot
WORKDIR /opt/ctds/qabot
RUN python -m venv $HOME/env && . $HOME/env/bin/activate && $HOME/.poetry/bin/poetry install --no-dev --no-interaction

WORKDIR /opt/ctds/qabot/qabot

ENTRYPOINT [".", "$HOME/env/bin/activate", "&&", "$HOME/.poetry/bin/poetry", "run", "python3.6", "qabot.py"]
