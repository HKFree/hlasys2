FROM python:3.11-alpine

WORKDIR /hlasys2

COPY . /hlasys2

RUN ls -la /hlasys2

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

ENV FLASK_APP hlasys2_app

ARG HLASYS2_REF_NAME
ARG HLASYS2_COMMIT_HASH

ENV HLASYS2_REF_NAME=${HLASYS2_REF_NAME}
ENV HLASYS2_COMMIT_HASH=${HLASYS2_COMMIT_HASH}

CMD ["./entry.sh"]
