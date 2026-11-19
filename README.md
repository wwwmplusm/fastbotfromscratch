# Fastbot — дневник питания в Telegram.

Оценка по фото остаётся черновиком, пока пользователь явно не нажмёт «Сохранить». Нутриенты считаются из каталога по весу: правка веса не вызывает модель заново.

## Запуск

```bash
cp .env.example .env
# вписать BOT_TOKEN и OPENAI_API_KEY
docker compose up --build
```

Compose поднимает PostgreSQL и бота. Бот ходит в Telegram long polling и слушает healthcheck на порту 8080 внутри контейнера.

Локально, если база уже запущена:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app
```

`DATABASE_URL` в `.env` для локального запуска смотрит на `localhost`. В Compose адрес базы переопределяется на сервис `db`.

Часовой пояс дневника по умолчанию — `DEFAULT_TIMEZONE` (`Europe/Moscow`). Границы дня считаются в этой зоне, в базе время хранится в UTC.

Модель распознавания — любой OpenAI-совместимый vision endpoint (`OPENAI_BASE_URL`, `OPENAI_MODEL`). Без ключа бот запускается, но фото завершается понятной ошибкой, черновик не подтверждается.

Резервная копия базы:

```bash
docker compose exec db pg_dump -U fastbot fastbot > backup.sql
```

## Проверки

```bash
pytest
```

Архитектурный контекст: `fastbot_architecture_context.md`.
