FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY alembic ./alembic
COPY alembic.ini ./
COPY monitor ./monitor

RUN pip install --no-cache-dir .

CMD ["bn-monitor", "run"]
