ARG AZLINUX_BASE_VERSION=master

FROM quay.io/cdis/python-nginx-al:${AZLINUX_BASE_VERSION} AS base

# Install vim and findutils (which provides `find`)
RUN dnf install -y vim findutils jq && \
    dnf install -y openssl && \
    dnf clean all && \
    rm -rf /var/cache/dnf

COPY --chown=gen3:gen3 . /src

WORKDIR /src

USER gen3

RUN python --version && python3 --version

RUN poetry env use python3.12 && poetry install --no-interaction --only main

CMD ["poetry", "run", "python", "qabot.py"]