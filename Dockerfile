FROM python:3.12.7

ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app

ADD --chmod=755 https://github.com/astral-sh/uv/releases/download/0.4.30/uv-installer.sh /install.sh
RUN /install.sh && rm /install.sh

COPY requirements.txt /app/

RUN /root/.cargo/bin/uv pip install --system --no-cache -r /app/requirements.txt
