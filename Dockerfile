FROM python:3.11-slim

WORKDIR /hlasys2

RUN apt-get update \
 && apt-get install -y --no-install-recommends locales tzdata \
 && sed -i 's/# cs_CZ.UTF-8/cs_CZ.UTF-8/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=cs_CZ.UTF-8 \
    LC_ALL=cs_CZ.UTF-8 \
    TZ=Europe/Prague

RUN pip3 install poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY hlasys2_app ./hlasys2_app
COPY entry.sh ./

ARG HLASYS2_COMMIT_HASH
RUN sed -i "s/HLASYS2_COMMIT_HASH = \"unknown\"/HLASYS2_COMMIT_HASH = \"${HLASYS2_COMMIT_HASH}\"/" hlasys2_app/version.py

ENV FLASK_APP=hlasys2_app

RUN mkdir -p /hlasys2/instance

CMD ["./entry.sh"]
