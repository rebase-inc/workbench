FROM python:alpine

RUN apk --quiet update && \
    apk --quiet add \
        bash \
        ca-certificates \
        gcc \
        g++ \ 
        musl-dev \
        py-virtualenv \
        python3-dev \
        docker

RUN mkdir -p /usr/app/notebooks /usr/app/site-packages /usr/app/src

COPY ./requirements.txt /

ARG PYTHON_COMMONS_HOST
ARG PYTHON_COMMONS_SCHEME
ARG PYTHON_COMMONS_PORT

RUN pip --quiet install --upgrade pip && \
    pip install \
        --no-cache-dir \
        --trusted-host ${PYTHON_COMMONS_HOST} \
        --extra-index-url ${PYTHON_COMMONS_SCHEME}${PYTHON_COMMONS_HOST}:${PYTHON_COMMONS_PORT} \
        --requirement /requirements.txt

COPY ./ /usr/app/src
COPY ./config.py /root/.jupyter/
ENV PYTHONPATH=/usr/app/src

WORKDIR /usr/app/notebooks

RUN jupyter nbextension enable --py --sys-prefix widgetsnbextension
CMD sh -c 'jupyter notebook --ip=* --port 8888 --no-browser' # has to be in a string because of a bug in jupyter
