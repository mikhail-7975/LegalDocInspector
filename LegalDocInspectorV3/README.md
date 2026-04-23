# LegalDocInspectorV3 Demo

Демо показывает целевую архитектуру:
- клиент (веб UI или Python-скрипт),
- API/BFF (FastAPI),
- RabbitMQ broker,
- `Parser Service` worker,
- `Document Generator Service` worker.

Реальная обработка не выполняется: сервисы используют `sleep` и отправляют прогресс-сообщения (`10%`, `40%`, `70%`, `100%`).

## Структура

- `demo_app/models/messages.py` — строгие `dataclass` с `from_json()` и `to_json()`
- `demo_app/api/main.py` — API/BFF
- `demo_app/broker/rabbit.py` — работа с RabbitMQ
- `demo_app/workers/parser_worker.py` — этап парсинга
- `demo_app/workers/doc_generator_worker.py` — этап генерации
- `demo_app/client/http_demo_client.py` — Python-клиент
- `run_demo.sh` — запуск всей демонстрации

## Как запустить

1. Из каталога `LegalDocInspectorV3`:

```bash
bash run_demo.sh
```

Скрипт:
- поднимет RabbitMQ в Docker (если не запущен),
- создаст `.venv` и установит зависимости,
- запустит API + 2 worker-а,
- завершит все процессы по `Ctrl+C`.

2. В отдельном терминале запустить клиент:

```bash
cd LegalDocInspectorV3
source .venv/bin/activate
python -m demo_app.client.http_demo_client
```

Клиент выполнит полный сценарий:
- `POST /packages`
- `POST /packages/{id}/parse`
- polling `GET /packages/{id}/events` до `event.package.parsed`
- `GET /packages/{id}/parsed`
- `POST /packages/{id}/generate`
- polling до `event.package.completed`

## API

- `POST /api/v1/packages`
- `POST /api/v1/packages/{package_id}/parse`
- `GET /api/v1/packages/{package_id}/parsed`
- `POST /api/v1/packages/{package_id}/generate`
- `GET /api/v1/packages/{package_id}/events?since=0`
- `GET /api/v1/health`

## Строгая JSON-модель

Все модели сообщений — `dataclass` с явными полями.

`from_json()`:
- принимает только разрешенные ключи,
- валидирует обязательные поля,
- отклоняет неизвестные поля (`ValueError`).

`to_json()`:
- возвращает только фиксированную структуру,
- не создает динамические поля.

Это гарантирует детерминированный формат данных между сервисами.
