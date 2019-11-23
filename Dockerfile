FROM quay.io/cdis/python-nginx:pybase3-1.0.0

ENV appname=qabot

ENV DEBIAN_FRONTEND=noninteractive

RUN adduser -D -g '' qabotuser

RUN mkdir -p /opt/ctds/qabot \
    && chown qabotuser /opt/ctds/qabot

RUN apk update \
    && apk add curl bash git

COPY . /opt/ctds/qabot
WORKDIR /opt/ctds/qabot

RUN python -m pip install -r requirements.txt \
    && COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" >qabot/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >>qabot/version_data.py 

WORKDIR /opt/ctds/qabot/qabot

USER qabotuser

ENTRYPOINT ["sh","-c","python3.6 qabot.py"]