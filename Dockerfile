FROM python:3.11-alpine

WORKDIR /hlasys2

COPY . /hlasys2

RUN ls -la /hlasys2

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

ENV FLASK_APP hlasys2_app
ENV HLASYS2_VERSION 0.0.1

CMD ["./entry.sh"]
