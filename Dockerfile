ARG AZLINUX_BASE_VERSION=master

FROM quay.io/cdis/python-nginx-al:${AZLINUX_BASE_VERSION} AS base

# Install vim and findutils (which provides `find`)
RUN dnf install -y vim findutils jq && \
    dnf install -y openssl && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Install Python 3.12 and pip
RUN tdnf install -y \
    python3-3.12.9 \
    python3-devel-3.12.9 \
 && ln -sf /usr/bin/python3.12 /usr/bin/python \
 && ln -sf /usr/bin/pip3.12 /usr/bin/pip

COPY --chown=gen3:gen3 . /src

WORKDIR /src

USER gen3

RUN poetry install --no-interaction --only main

CMD ["poetry", "run", "python", "qabot.py"]