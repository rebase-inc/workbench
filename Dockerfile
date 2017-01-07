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

RUN pyvenv /venv
RUN pip --quiet install --upgrade pip
RUN pip install jupyter
RUN mkdir -p /usr/app/notebooks

COPY ./config.py /root/.jupyter/

WORKDIR /usr/app/notebooks

CMD sh -c 'jupyter notebook --ip=* --port 8888 --no-browser'
