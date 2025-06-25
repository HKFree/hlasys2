FROM 3.11-alpine

WORKDIR /app

COPY . /app

RUN ls -la .
RUN ls -la /app

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev