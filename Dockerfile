FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md alembic.ini ./
RUN mkdir -p app && touch app/__init__.py && pip install --no-cache-dir .

COPY app ./app
COPY migrations ./migrations

USER appuser

CMD ["sh", "-c", "alembic upgrade head && python -m app"]
