# Fastbot

Дневник питания в Telegram. Отправьте фото блюда, проверьте список продуктов и вес порций, затем сохраните запись. Бот покажет примерные калории, белки, жиры и углеводы.

- Распознавание создаёт черновик. В дневник запись попадает после нажатия **«Сохранить»**.
- Можно поправить вес или убрать продукт. Бот пересчитает нутриенты по каталогу без повторного запроса к модели.
- Команда `/today` открывает дневник за текущий день.

## Запуск через Docker Compose

Скопируйте файл конфигурации и заполните `BOT_TOKEN` и `OPENAI_API_KEY` в `.env`.

```bash
cp .env.example .env
docker compose up --build
```

Compose запускает PostgreSQL, применяет миграции и поднимает бота. Для распознавания фотография передаётся провайдеру модели, настроенному через `OPENAI_BASE_URL` и `OPENAI_MODEL`. Без ключа бот запустится, а распознавание фотографий будет недоступно.

Дата записи определяется по `DEFAULT_TIMEZONE` (по умолчанию `Europe/Moscow`). Время в базе хранится в UTC.

## Локальная разработка

Понадобятся Python 3.12+ и PostgreSQL. Укажите адрес базы в `DATABASE_URL` в файле `.env`.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app
```

Запуск тестов: `pytest`.

Резервная копия базы в Compose:

```bash
docker compose exec db pg_dump -U fastbot fastbot > backup.sql
```

[Архитектура](ARCHITECTURE.md) · [Контекст проекта](fastbot_architecture_context.md)
