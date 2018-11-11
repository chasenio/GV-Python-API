ARG VERSION=0.1
FROM ubuntu:latest
LABEL author="cvno"
LABEL maintainer="x@cvno.me"

ARG PHANTOM_JS_VERSION
ENV PHANTOM_JS_VERSION ${PHANTOM_JS_VERSION:-2.1.1-linux-x86_64}

ENV TZ=Asia/Shanghai
ENV DEBIAN_FRONTEND=noninteractive

ENV GV_USR <your email>
ENV GV_PWD <your passwd>
ENV GVAPI_IS_DEV false
ENV TO_NUMBER 13212969527

RUN mkdir -p /usr/src/app  && \
    mkdir -p /var/log/gunicorn

COPY . /usr/src/app
WORKDIR /usr/src/app

RUN set -x \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        tzdata \
        ca-certificates \
        bzip2 \
        libfontconfig \
        curl \
        python3 \
        python3-pip \
        python3-setuptools \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
	&& echo "Asia/Shanghai" > /etc/timezone \
    && mkdir /tmp/phantomjs \
    && curl -L https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-${PHANTOM_JS_VERSION}.tar.bz2 \
        | tar -xj --strip-components=1 -C /tmp/phantomjs \
    && mv /tmp/phantomjs/bin/phantomjs /usr/local/bin \
    && pip3 install --no-cache-dir gunicorn \
    && pip3 install --no-cache-dir -r requirements.txt -i https://pypi.doubanio.com/simple \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

CMD ["/usr/local/bin/gunicorn", "-w", "1", "-b", ":5000", "app:app"]