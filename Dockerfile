# Stage 1: Build stage

FROM --platform=linux/amd64 deepset/haystack:base-v2.6.1 AS builder


WORKDIR /code

ENV PIP_DEFAULT_TIMEOUT=100 
# Allow statements and log messages to immediately appear
ENV PYTHONUNBUFFERED=1 
# disable a pip version check to reduce run-time & log-spam
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 
# cache is useless in docker image, so disable to reduce image size
ENV PIP_NO_CACHE_DIR=1 

# install core and fixed libs for easy caching
COPY ./core-requirements.txt /code/requirements.txt

# Install build dependencies
RUN set -ex \
    # Upgrade the package index and install security upgrades
    apt-get update \
    && apt-get upgrade -y \
    # Install dependencies
    && pip install -r requirements.txt  --no-cache-dir  --extra-index-url https://download.pytorch.org/whl/cpu\
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*# Copy and install dependencies

COPY ./requirements.txt /code/requirements.txt
# Install build dependencies
RUN set -ex \
    pip install -r requirements.txt  --no-cache-dir \
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*# Copy and install dependencies



COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]


