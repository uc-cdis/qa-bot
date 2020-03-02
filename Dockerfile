FROM quay.io/cdis/python-nginx:master

ENV appname=qabot

ENV DEBIAN_FRONTEND=noninteractive

RUN adduser -D -g '' qabotuser

RUN mkdir -p /opt/ctds/qabot \
    && chown qabotuser /opt/ctds/qabot

COPY . /opt/ctds/qabot
WORKDIR /opt/ctds/qabot

RUN apk --update add python py-pip openssl ca-certificates py-openssl wget curl bash git
RUN apk --update add --virtual build-dependencies libffi-dev openssl-dev python-dev py-pip build-base \
  && pip install --upgrade pip \
  && pip install -r requirements.txt \
    && COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" >qabot/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >>qabot/version_data.py \
  && apk del build-dependencies

WORKDIR /opt/ctds/qabot/qabot

USER qabotuser

ENTRYPOINT ["sh","-c","python3.6 qabot.py"]
