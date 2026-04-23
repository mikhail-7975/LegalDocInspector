# LegalDocInspector V3: Целевой дизайн (Frontend + Backend + RabbitMQ)

## 1) Цель и область применения

Этот документ описывает целевую архитектуру, в которой:
- frontend и backend взаимодействуют в реальном времени,
- backend-сервисы обмениваются сообщениями асинхронно через RabbitMQ,
- долгие операции выполняются по событийной модели,
- уведомления о прогрессе и результате доставляются в UI без polling.

Дизайн сохраняет текущую концепцию репозитория:
- web-приложение в `apps/web`,
- API/BFF в `services/bff-orchestrator`,
- асинхронные worker-процессы на базе Celery и RabbitMQ.

## 2) Архитектура верхнего уровня

### 2.1 Компоненты

1. Frontend (React, Vite)
- Инициирует команды пользователя (создание пакета, загрузка, извлечение, расчет, генерация документов).
- Подписывается на уведомления backend в реальном времени по WebSocket (или через SSE как fallback).

2. BFF / API Gateway (FastAPI)
- Аутентификация и управление сессией.
- Командный API для UI.
- Real-time gateway для передачи backend-событий в UI-клиенты.
- Публикация командных событий в RabbitMQ (там, где это уместно).
- Потребление доменных событий из RabbitMQ и доставка их подключенным клиентам UI.

3. Worker(ы)
- Celery worker-ы для тяжелых задач (parse/extract/calculate/generate).
- Публикаторы доменных событий (смена состояния, прогресс, ошибки, завершение).

4. RabbitMQ
- Брокер команд и событий между backend-компонентами.
- Маршрутизация через exchange с явными routing key.

5. Storage
- Файловое хранилище артефактов пакета.
- Хранилище состояния (рекомендуется персистентное: Redis/PostgreSQL) для жизненного цикла пакета и восстановления.

### 2.2 Модель взаимодействия

- UI -> BFF:
  - HTTP для запуска команд и загрузки файлов.
  - WebSocket/SSE для получения асинхронных обновлений.
- BFF -> RabbitMQ:
  - публикация командных событий (опционально для некоторых синхронных команд),
  - потребление доменных событий от worker-ов.
- Worker -> RabbitMQ:
  - потребление команд,
  - публикация событий прогресса/состояния/результата.
- BFF -> UI:
  - push доменных событий с фильтрацией по доступу пользователя/сессии/пакета.

## 3) Контракты событийной модели

## 3.1 Общий envelope

Каждое сообщение события должно использовать единый envelope:

```json
{
  "event_id": "uuid",
  "event_type": "package.extraction.progress",
  "event_version": 1,
  "occurred_at": "2026-04-22T12:00:00Z",
  "correlation_id": "request-or-package-id",
  "causation_id": "parent-event-id-or-command-id",
  "tenant_id": "optional",
  "user_id": "optional",
  "payload": {}
}
```

## 3.2 Рекомендуемые командные события

- `package.extract.requested`
- `package.calculate.requested`
- `package.documents.generate.requested`

## 3.3 Рекомендуемые доменные события

- `package.created`
- `package.files.uploaded`
- `package.extraction.started`
- `package.extraction.progress`
- `package.extraction.completed`
- `package.extraction.failed`
- `package.form.updated`
- `package.calculation.started`
- `package.calculation.completed`
- `package.calculation.failed`
- `package.documents.generation.started`
- `package.documents.generation.completed`
- `package.documents.generation.failed`

## 4) Топология RabbitMQ

## 4.1 Exchanges

- `legaldoc.commands` (topic)
- `legaldoc.events` (topic)
- `legaldoc.dlx` (topic, dead-letter)

## 4.2 Очереди (пример)

- `bff.commands.package` (если BFF делегирует обработку команд асинхронно)
- `worker.extract`
- `worker.calculate`
- `worker.generate_docs`
- `bff.events.ui_push` (consumer в BFF для real-time уведомлений клиентов)
- `audit.events` (опционально)

## 4.3 Routing keys (пример)

- commands:
  - `command.package.extract`
  - `command.package.calculate`
  - `command.package.generate_docs`
- events:
  - `event.package.extraction.*`
  - `event.package.calculation.*`
  - `event.package.documents.*`

## 4.4 Надежность

- Durable exchanges/queues.
- Persistent messages (`delivery_mode=2`).
- Acknowledgements у consumer-ов и политика повторов (retry).
- Dead-letter очереди по типам нагрузок.
- Idempotency key на стороне команд (`package_id + operation + version`).

## 5) Доставка событий в UI в реальном времени

## 5.1 Предпочтительный путь

- UI открывает WebSocket-соединение: `/api/v1/ws`.
- После аутентификации UI подписывается на каналы пакетов:
  - `package:{package_id}`
- BFF потребляет события RabbitMQ и отправляет только авторизованные события соответствующим клиентам.

## 5.2 Fallback путь

- SSE endpoint `/api/v1/events`, если WebSocket недоступен.

## 5.3 Поведение клиента

- Сохранить HTTP endpoint-ы для старта команд и загрузки файлов.
- Заменить polling статуса извлечения на подписку на события.
- Оставить временный fallback на polling на период миграции.

## 6) Рекомендации по модели состояния и данных

Текущий in-memory registry следует эволюционировать в персистентное состояние:
- метаданные пакета,
- состояние жизненного цикла,
- таймстемпы операций,
- детали ошибок,
- offsets/checkpoints отправленных событий (опционально).

Рекомендуемый минимальный набор таблиц:
- `packages`
- `package_operations`
- `package_events` (опциональный event log)

## 7) Безопасность и управление

- Не открывать прямой доступ к RabbitMQ из браузера.
- AuthN/AuthZ в BFF для HTTP и WebSocket/SSE каналов.
- Проверка прав по пакету до подписки и до пересылки событий.
- Редакция чувствительных полей payload во внешних UI-событиях.
- Correlation ID в логах и трассировках.

## 8) Наблюдаемость

- Структурированные логи с `package_id`, `event_id`, `correlation_id`.
- Метрики:
  - глубина очередей,
  - lag consumer-ов,
  - длительность задач по стадиям,
  - число ошибок/повторов.
- Трассировка цепочки HTTP -> publish -> consume -> push-to-client.

## 9) Поэтапный план миграции

Фаза 1 (низкий риск)
- Сохранить текущий HTTP API и поток Celery.
- Добавить публикацию событий из worker-ов при смене состояний.
- Добавить consumer событий в BFF и WebSocket endpoint.
- Использовать WebSocket пока только для прогресса извлечения.

Фаза 2
- Перевести уведомления по calculate/generate на события.
- Сократить/отключить frontend polling.

Фаза 3
- Ввести персистентное хранилище состояния пакета.
- Усилить надежность: retry/DLQ/idempotency.

Фаза 4
- Опционально: выделить BFF и orchestration/event сервисы для независимого масштабирования.

## 10) Совместимость с текущей концепцией

Целевой дизайн совместим с текущей архитектурой репозитория, потому что:
- RabbitMQ и Celery уже присутствуют,
- API endpoint-ы и жизненный цикл пакета уже реализованы,
- frontend уже построен вокруг состояния пакета.

Основные необходимые доработки:
- event contracts,
- real-time gateway в BFF (WebSocket/SSE),
- персистентное хранилище состояния (рекомендуется),
- устойчивая топология очередей и обработка ошибок.

## 11) Definition of done (архитектурный уровень)

- UI получает прогресс extraction/calculation/generation в реальном времени.
- Нет прямого подключения браузера к RabbitMQ.
- Все долгие этапы публикуют доменные события с correlation metadata.
- Ошибки наблюдаемы, повторяемы и аудируемы.
- Polling endpoint остается только как backward-compatible fallback.
