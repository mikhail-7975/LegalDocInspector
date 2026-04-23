# BFF / orchestrator (FastAPI)

Серверное приложение по структуре из `LegalDocInspectorV2/ProjectStructure.md`: пакеты документов, извлечение через легаси-парсеры, расчёт пени, генерация DOCX.

## Запуск (разработка)

Из каталога `services/bff-orchestrator`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
# Выполняйте из этого каталога (иначе не разрешится -e ../../LegalDocInspectorV2/python)
pip install -r requirements.txt
# Для полного контура PDF/OCR: pip install -r ../../requirements.txt
export PYTHONPATH="../../:src"
export STORAGE_ROOT="../../tmp/legaldoc-storage"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Celery worker (отдельный терминал, нужен RabbitMQ):

```bash
export PYTHONPATH="../../:src"
celery -A app.workers.celery_app worker --loglevel=INFO
```

Требуется **Python 3.10+** (легаси `penalty_calculator` использует `match`).

## OCR (LegalDocInspector V2)

Извлечение текста из PDF договора/претензии идёт через пакет `legaldoc-v2` (`../../LegalDocInspectorV2/python` в `requirements.txt`) и `DoclingOcrEngine` по файлу `LegalDocInspectorV2/config/ocr_engine.yaml` (`backend: docling`, `device: cuda|cpu`).

Переопределение пути: переменная окружения `OCR_ENGINE_CONFIG_PATH` или поле `ocr_engine_config_path` в `app.config.Settings` (по умолчанию — YAML внутри `LegalDocInspectorV2/config/`).
