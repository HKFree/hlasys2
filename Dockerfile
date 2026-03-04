FROM python:3.11-alpine

WORKDIR /hlasys2

RUN pip3 install poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY hlasys2_app ./hlasys2_app
COPY entry.sh ./

ARG HLASYS2_COMMIT_HASH=unknown
RUN sed -i "s/HLASYS2_COMMIT_HASH = \"unknown\"/HLASYS2_COMMIT_HASH = \"${HLASYS2_COMMIT_HASH}\"/" hlasys2_app/version.py

ENV FLASK_APP=hlasys2_app

RUN mkdir -p /hlasys2/instance

CMD ["./entry.sh"]
