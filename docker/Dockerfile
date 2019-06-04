FROM python:3.7-alpine
# docker build -f docker/Dockerfile -t pyaleph .
# docker run -v `pwd`/config.yml:/pyaleph/config.yaml --name pyaleph-server pyaleph
# docker rm pyaleph-server
# docker rmi pyaleph

RUN apk update; \
    apk upgrade; \
    apk add --no-cache ca-certificates gnupg wget git autoconf automake openssh build-base \
    py3-aiohttp libuv-dev libffi-dev openssl-dev;

ADD . /pyaleph
WORKDIR /pyaleph

RUN python setup.py develop

ENTRYPOINT [ "pyaleph", "-c", "config.yaml" ]