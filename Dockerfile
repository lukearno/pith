

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install build-essential python3-distutils postgresql-server-dev-15 -y
RUN python3 -m venv --copies /app/venv
WORKDIR /app
RUN . /app/venv/bin/activate && pip install wheel
COPY www /app/www
COPY tmpl /app/tmpl
COPY . /tmp/app/
RUN . /app/venv/bin/activate && pip install -r /tmp/app/requirements.txt
RUN . /app/venv/bin/activate && pip install /tmp/app


FROM python:3.12-slim AS deploy

WORKDIR /app
COPY --from=builder /app/ /app/
ENV PATH /app/venv/bin:$PATH
EXPOSE ${PORT:-8080}
ENTRYPOINT pith http "0.0.0.0" "${PORT:-8080}"


