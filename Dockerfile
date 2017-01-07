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

RUN mkdir -p /usr/app/notebooks /usr/app/site-packages
COPY ./requirements.txt /root/requirements.txt
RUN pip install -r /root/requirements.txt 
ENV PYTHONPATH /usr/app/site-packages
COPY ./scanner /usr/app/site-packages/scanner
COPY ./config.py /root/.jupyter/

WORKDIR /usr/app/notebooks

CMD sh -c 'jupyter notebook --ip=* --port 8888 --no-browser'
