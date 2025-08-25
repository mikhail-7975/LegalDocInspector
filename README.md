# Legal Document Inspector

**Система анализа юридических документов с расчетом неустойки**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://www.python.org/static/community_logos/python-powered-logo-2-32x32.png)](http://mypy-lang.org/)

## 🏗️ Архитектура

Система построена на основе принципов **Clean Architecture**, **SOLID** и **DRY** с использованием современных паттернов проектирования:

```
legal_doc_inspector/
├── domain/              # Доменные модели и бизнес-правила
│   ├── models.py       # Pydantic модели с валидацией
│   └── exceptions.py   # Иерархия исключений
├── services/           # Бизнес-логика и сервисы
│   └── penalty_service.py  # Расчет неустойки (Strategy + Factory)
├── api/               # Слой представления
│   ├── controllers.py # Контроллеры с валидацией и безопасностью
│   └── schemas.py     # API схемы запросов/ответов
└── legacy/           # Устаревший код (планируется к удалению)
```

## 🚀 Установка

### Требования
- Python 3.11+
- Git

### Установка зависимостей

```bash
# Клонирование репозитория
git clone git@github.com:Covald/docinspector.git
cd docinspector

# Установка uv (если не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Создание виртуального окружения и установка зависимостей
uv sync --dev

# Установка системных зависимостей
sudo apt-get install -y poppler-utils tesseract-ocr-rus  # Ubuntu/Debian
# brew install poppler tesseract          # macOS
```

### Настройка среды разработки

```bash
# Автоматическая настройка (рекомендуется)
python scripts/dev.py setup

# Или вручную:
uv run pre-commit install
```

## 🏃 Запуск

### Запуск backend сервера

**FastAPI (рекомендуется):**
```bash
python run_fastapi.py
```

**Flask (legacy):**
```bash
python run.py
```

### Запуск полной системы (FastAPI + Streamlit)

**Docker Compose (рекомендуется):**
```bash
# Запуск всей системы
docker-compose up -d

# Только для разработки (без nginx)
docker-compose --profile development up
```

**Ручной запуск:**
```bash
# 1. Запуск FastAPI backend
python run_fastapi.py

# 2. Запуск Streamlit frontend (в отдельном терминале)
streamlit run streamlit/interface.py
```

**Доступ к приложению:**
- **Streamlit UI**: http://localhost:8501 
- **FastAPI API**: http://localhost:5001
- **API Docs**: http://localhost:5001/docs

### API Endpoints

- `GET /` - Проверка работоспособности
- `POST /parse` - Обработка документов
- `POST /create_doc` - Создание искового заявления
- `POST /create_calculating_table` - Создание таблицы расчетов

## 🧪 Тестирование

### Запуск всех тестов

```bash
pytest
```

### Запуск с покрытием кода

```bash
pytest --cov=legal_doc_inspector --cov-report=html
```

### Запуск определенной категории тестов

```bash
pytest -m unit          # Только unit тесты
pytest -m integration   # Только интеграционные тесты
pytest -m "not slow"    # Исключить медленные тесты
```

## 🏗️ Архитектурные решения

### 1. **Доменные модели (Domain Models)**
- **Pydantic модели** с встроенной валидацией
- **Типизированные перечисления** для бизнес-значений
- **Immutable структуры** для критичных данных

```python
from legal_doc_inspector.domain.models import CompanyType, PenaltyPeriod

# Строгая типизация и валидация
company_type = CompanyType.UK  # Управляющая компания
period = PenaltyPeriod(...)    # Автоматическая валидация полей
```

### 2. **Strategy Pattern для расчета неустойки**
- **Разные стратегии** для разных типов компаний
- **Легко расширяемая** архитектура
- **Единый интерфейс** для всех вычислений

```python
from legal_doc_inspector.services.penalty_service import PenaltyService

service = PenaltyService(cb_rate_provider, holiday_checker)
periods = service.calculate_penalty_from_data(
    certificate_data, 
    CompanyType.UK, 
    current_date, 
    penalty_start_day=10
)
```

### 3. **Иерархия исключений**
- **Структурированная обработка ошибок**
- **Богатый контекст** для диагностики
- **Безопасная сериализация** для API

```python
from legal_doc_inspector.domain.exceptions import PenaltyCalculationError

try:
    result = calculate_penalty(data)
except PenaltyCalculationError as e:
    logger.error("Ошибка расчета", error=e.to_dict())
    return {"error": e.error_code, "message": e.message}
```

### 4. **Современный API дизайн**
- **Pydantic схемы** для валидации
- **Структурированное логирование**
- **Безопасность файловых операций**

## 🔒 Безопасность

### Валидация файлов
- **Ограничение размера** (50MB)
- **Проверка расширений** (.pdf, .docx, .xlsx, .xls, .zip)
- **Защита от Zip-bomb** (коэффициент сжатия < 100)
- **Безопасная распаковка** архивов

### Обработка ошибок
- **Детальное логирование** без утечки sensitive данных
- **Graceful degradation** при недоступности внешних сервисов
- **Валидация входных данных** на всех уровнях

## 📊 Качество кода

### Современная тулчейн разработки
- **🚀 uv** - ультрабыстрый менеджер пакетов Python (замена pip/pip-tools)
- **⚡ ruff** - универсальный линтер и форматтер (замена black/isort/flake8)
- **🔍 mypy --strict** - строгая типизация
- **🛡️ bandit** - анализ безопасности

### Команды разработки
```bash
# Форматирование кода
python scripts/dev.py format

# Проверка кода  
python scripts/dev.py lint

# Запуск тестов
python scripts/dev.py test

# Обновление зависимостей
python scripts/dev.py update

# Запуск API сервера
python scripts/dev.py api

# Запуск Streamlit
python scripts/dev.py streamlit

# Полная очистка проекта
python scripts/dev.py clean
```

### Тестовое покрытие
- **Unit тесты** для бизнес-логики
- **Integration тесты** для API  
- **Property-based тесты** для граничных случаев
- **Моки** для внешних зависимостей

### Performance Benefits
- **uv**: до 80x быстрее pip при установке зависимостей
- **ruff**: до 100x быстрее flake8 при проверке кода
- **Docker**: многоэтапная сборка с кешированием слоев
- **Pre-commit**: быстрые проверки перед коммитом

### CI/CD готовность
- **Pre-commit hooks** с ruff и mypy
- **Docker поддержка** с uv
- **GitHub Actions** готовые конфиги

## 🔧 Разработка

### Добавление новой стратегии расчета

```python
from legal_doc_inspector.services.penalty_service import PenaltyStrategy

class NewCompanyStrategy(PenaltyStrategy):
    def get_stages(self) -> List[PenaltyStage]:
        return [
            PenaltyStage(days_threshold=30, rate_multiplier=Decimal('0.01')),
            # ...
        ]
    
    def get_company_type(self) -> CompanyType:
        return CompanyType.NEW_TYPE

# Регистрация в фабрике
PenaltyStrategyFactory._strategies[CompanyType.NEW_TYPE] = NewCompanyStrategy()
```

### Добавление нового API endpoint

```python
from legal_doc_inspector.api.controllers import DocumentController

class DocumentController:
    def new_endpoint(self) -> tuple[Dict[str, Any], int]:
        try:
            # Валидация
            request_data = self._validate_request()
            
            # Бизнес-логика
            result = self.service.process_data(request_data)
            
            # Ответ
            return {"data": result}, 200
            
        except LegalDocInspectorError as e:
            return {"error": e.error_code}, 400
```

## 📚 Документация API

**FastAPI интерактивная документация:**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI спецификация**: http://localhost:8000/openapi.json

**Тестирование миграции:**
```bash
python test_migration.py
```

## 🛠️ Мониторинг и диагностика

### Structured logging
```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("Расчет неустойки завершен", 
           total_periods=len(periods),
           total_penalty=sum(p.penalty for p in periods))
```

### Health checks
```bash
curl http://localhost:5001/
# {"status": "healthy", "timestamp": "2024-01-01T00:00:00", "version": "0.1.0"}
```

## 🗂️ Миграция с legacy кода

### Устаревший код
- `penalty_calculator/penalty_calculator.py` → `services/penalty_service.py`
- `app/routes.py` → `api/controllers.py`
- Глобальные переменные → Dependency injection

### План миграции
1. ✅ Новая архитектура с тестами
2. ⏳ Постепенная замена legacy кода
3. ⏳ Удаление устаревших модулей
4. ⏳ Обновление документации

## 🤝 Участие в разработке

### Workflow
1. Fork репозитория
2. Создание feature branch
3. Коммиты с описательными сообщениями
4. Pull request с описанием изменений
5. Code review и merge

### Стандарты кода
- **Строгая типизация** (mypy --strict)
- **Документация** для публичных методов
- **Тесты** для новой функциональности
- **Логирование** критичных операций

---

## 📞 Поддержка

Для вопросов и предложений:
- **GitHub Issues** - для багов и feature requests
- **Pull Requests** - для предложения кода
- **Discussions** - для общих вопросов

---

**Legal Document Inspector** - надежная и современная система для профессионального анализа юридических документов.
