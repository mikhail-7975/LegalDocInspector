# LegalDocInspector — веб-контур иска (MVP)

Монорепозиторий по целевой структуре из `LegalDocInspectorV2/ProjectStructure.md`:

| Каталог | Назначение |
|--------|------------|
| `apps/web/` | React (Vite) SPA |
| `services/bff-orchestrator/` | FastAPI, Celery-задачи, вызов легаси `LegalDocInspector/legal_doc_inspector/` |
| `contracts/openapi/` | Черновик OpenAPI |
| `infra/` | `docker-compose.yml`, примеры переменных окружения |
| `LegalDocInspectorV2/` | ТЗ, эталонные JSON, макет UI |

Легаси-код калькулятора и Excel-парсера **не копируется** — импортируется из каталога `LegalDocInspector/`.

## Быстрый старт

См. подробно [`LegalDocInspectorV2/quickstart.md`](LegalDocInspectorV2/quickstart.md).

Кратко (локально):

1. Поднять RabbitMQ (например `docker run -p 5672:5672 rabbitmq:3-management-alpine`).
2. Backend: `cd services/bff-orchestrator`, venv, `pip install -r requirements.txt`, `PYTHONPATH=../../:src`, `uvicorn app.main:app --port 8000`.
3. Worker: `celery -A app.workers.celery_app worker`.
4. Frontend: `cd apps/web`, `npm ci`, `npm run dev` (прокси `/api` на порт 8000).

## Ограничения MVP

- UI рассчитан на **один комплект** документов за сессию (расширение формы — по необходимости).
- Для полного извлечения PDF (OCR/нейросети) установите зависимости из корневого `requirements.txt` в то же окружение, что и BFF.
