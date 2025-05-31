FROM python:3.11-slim

RUN --mount=type=cache,target=/root/.cache/pip pip install -U pip

RUN apt-get update; \
    apt-get install --no-install-recommends -y curl ffmpeg; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*
ENV PATH=/root/.cargo/bin:${PATH}

WORKDIR /app
RUN mkdir -p voices config

COPY requirements.txt /app/
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY *.py /app/

CMD python main.py $EXTRA_ARGS $@
