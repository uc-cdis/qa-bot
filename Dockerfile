ARG AZLINUX_BASE_VERSION=feat_py3.13_hardened

FROM quay.io/cdis/python-nginx-al:${AZLINUX_BASE_VERSION} AS base

# Install vim and findutils (which provides `find`)
RUN dnf install -y vim findutils jq && \
    dnf install -y openssl && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Install Kubectl
RUN curl -LO https://dl.k8s.io/release/v1.33.0/bin/linux/amd64/kubectl && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

COPY --chown=gen3:gen3 . /src

WORKDIR /src

USER gen3

#RUN poetry install --no-interaction --only main

CMD ["python", "--version"]

#CMD ["poetry", "run", "python", "qabot.py"]