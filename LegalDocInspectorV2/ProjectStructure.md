# Структура проекта при реализации ТЗ (FullSpecification)

Документ описывает **целевую раскладку** создаваемых каталогов и файлов по консолидированному ТЗ [`technical_specification/FullSpecification.md`](technical_specification/FullSpecification.md) и базовому [`technical_specification/TecnicalSpecification.md`](technical_specification/TecnicalSpecification.md) (§ 9). Уточнения по архитектуре MVP — [`technical_specification/TZ-supplement-06-arkhitektura.md`](technical_specification/TZ-supplement-06-arkhitektura.md); использование существующего кода — [`technical_specification/TZ-supplement-12-existing-code-usage.md`](technical_specification/TZ-supplement-12-existing-code-usage.md).

---

## 1. Два уровня: целевой монорепозиторий и текущий артефакт `LegalDocInspectorV2/`

| Уровень | Назначение |
|--------|------------|
| **Новая кодовая база сервиса** | По § 9 базового ТЗ — отдельное дерево (ниже), условное имя корня `legal-doc-claim-service/`. |
| **Каталог `LegalDocInspectorV2/`** | Сейчас: ТЗ, дополнения, эталонные JSON, макет UI. При реализации может оставаться «документация + контракты» или быть объединён с корнем монорепозитория — **не зафиксировано** (вопросы в [`TZ-supplement-09-struktura-proekta.md`](technical_specification/TZ-supplement-09-struktura-proekta.md)). |

**Фактический репозиторий с легаси-кодом** (не создаётся заново, а подключается): `LegalDocInspector/` — модули `legal_doc_inspector/`, `backend`, `streamlit`, каталог шаблонов `data/templates/` (см. FullSpecification § 1, § 9, § 11).

---

## 2. Целевая структура монорепозитория (базовое Т § 9)

Игнорируется старая раскладка только внутри репозитория; **ниже — ориентир для создаваемых папок и типовых файлов**.

```
legal-doc-claim-service/
├── apps/
│   └── web/                          # SPA React: исходники UI, сборка статики
├── services/
│   ├── bff-orchestrator/             # HTTP API для UI, оркестрация, агрегация
│   ├── extract-egrul/
│   ├── extract-contract/
│   ├── extract-preclaim/
│   ├── extract-debt-certificate/
│   ├── ocr-pipeline/                 # OCR для PDF; используется при необходимости extract-*
│   ├── calculation-service/          # обёртка вызова калькулятора (см. § 11)
│   └── docx-generator/               # генерация Word (обёртка doc_creator)
├── packages/                         # опционально: общие библиотеки
│   ├── shared-types/
│   └── debt-certificate-parser/      # опционально: типы/обёртка над парсером Excel
├── contracts/
│   ├── openapi/                      # OpenAPI (единый или по сервисам) — детали в Доп. 07 без фиксации
│   └── json-schema/                  # схемы form, extraction, calculation
├── infra/
│   ├── docker-compose.yml            # локальный стенд: gateway, bff, очередь, воркеры, при необходимости сервисы
│   ├── data/                         # опционально: монтируемое хранилище для dev (часто в .gitignore)
│   └── k8s/                          # опционально: прод
├── docs/                             # документация развёртывания, ADR и т.д.
└── README.md
```

### 2.1. Типовые файлы внутри сервисов `services/*`

По требованию базового Т § 9: **каждый** каталог в `services/*` — отдельный деплойный артефакт:

- `Dockerfile`
- собственные переменные окружения (описание в README сервиса или в `infra/`)
- при необходимости: `requirements.txt` / `pyproject.toml` (Python), точка входа приложения, тесты

**Примечание (FullSpecification § 6):** для MVP допускается **монолитный** Python с Celery без обязательного выделения **каждого** шага в отдельный HTTP-микросервис; физически дерево `services/*` может появиться поэтапно или быть свёрнуто в один пакет с модулями — ориентир заказчика: **версия B** дополнений (локальный ПК, упрощённый деплой).

### 2.2. Фронтенд `apps/web/`

- Проект React (SPA), сборка статики для раздачи через reverse proxy (Nginx/Caddy) вместе с `/api` → backend (FullSpecification § 6).

### 2.3. Контракты `contracts/`

- `openapi/` — спецификации API (`/api/v1`, ресурсы из FullSpecification § 7).
- `json-schema/` — схемы, согласованные с эталонами в `LegalDocInspectorV2/jsons/` и [`TZ-supplement-08-modeli-json.md`](technical_specification/TZ-supplement-08-modeli-json.md).

### 2.4. Инфраструктура `infra/`

- `docker-compose.yml` — локальный стенд: gateway, оркестратор, RabbitMQ, воркеры Celery, при полной микросервисной раскладке — образы `extract-*`, `ocr-pipeline` и т.д.
- `data/` — корень для локального файлового хранилища (см. Т § 9: `STORAGE_ROOT` или монтирование тома); структура внутри по **`packageId`** (FullSpecification § 6).
- `k8s/` — опционально для прода (базовое Т допускает; дополнения ориентируются на локальный сервер без обязательного Kubernetes).

---

## 3. Интеграция с существующим кодом (§ 11 FullSpecification)

Не создаются новые копии логики внутри монорепозитория вместо:

- `LegalDocInspector/legal_doc_inspector/calculator/penalty_calculator.py` — **изменять запрещено**
- `LegalDocInspector/legal_doc_inspector/exel_parser.py` — **изменять запрещено**

Новая система **вызывает или оборачивает** их; цепочка и форматы — [`TZ-supplement-12-existing-code-usage.md`](technical_specification/TZ-supplement-12-existing-code-usage.md).

**Шаблоны Word:** каталог `data/templates/` в существующем репозитории; заполнение через `legal_doc_inspector/doc_creator/` (FullSpecification § 1).

---

## 4. Что уже есть в `LegalDocInspectorV2/` (артефакты ТЗ)

Структура **уже создаваемых** при подготовке ТЗ файлов и папок:

```
LegalDocInspectorV2/
├── ProjectStructure.md               # этот файл
├── technical_specification/
│   ├── FullSpecification.md
│   ├── TecnicalSpecification.md
│   ├── TZ-supplement-01-…md … TZ-supplement-12-…md
│   ├── jsons/                        # эталонные JSON: parse_*, calculate_penalty_*, create_doc_*, …
│   └── interface/                    # макет UI (HTML/CSS/JS), не прод-приложение
│       ├── index.html
│       ├── css/app.css
│       ├── js/mock.js
│       └── README.md
```

При старте реализации **прод-код** обычно живёт в корне монорепозитория (`apps/`, `services/`, …); содержимое `technical_specification/` и `jsons/` может **копироваться или ссылаться** из `docs/` / `contracts/` нового репозитория — на усмотрение команды.

---

## 5. Открытые решения по структуре (Доп. 9)

В [`TZ-supplement-09-struktura-proekta.md`](technical_specification/TZ-supplement-09-struktura-proekta.md) заданы вопросы **без зафиксированных ответов** в ТЗ: инструмент монорепо (Nx, Turborepo, …), единый язык vs polyglot, фреймворк фронтенда (React зафиксирован в § 6, детали сборки — в вопросах), CI/CD, объём тестов и т.д. Итоговая детализация веток `packages/*`, именования сервисов и репозитория может уточняться после ответов на Q-9.x.

---

## 6. Сводка: что «создаётся» в первую очередь по ТЗ

| Область | Каталоги / файлы |
|--------|-------------------|
| UI | `apps/web/` — приложение React |
| API и оркестрация | `services/bff-orchestrator/` (или модуль внутри одного Python-пакета при MVP) |
| Извлечение и OCR | `services/extract-*`, `services/ocr-pipeline/` (или подпакеты одного деплоя) |
| Расчёт и DOCX | `services/calculation-service/`, `services/docx-generator/` + вызовы легаси без правок ядра |
| Очередь | конфигурация Celery + RabbitMQ в `infra/` и код воркеров у оркестратора/сервисов |
| Контракты | `contracts/openapi/`, `contracts/json-schema/` |
| Развёртывание | `infra/docker-compose.yml`, опционально `infra/k8s/` |
| Документация | `docs/`, корневой `README.md` |

Эталонные данные и текст ТЗ остаются опорой: **`LegalDocInspectorV2/technical_specification/`**, **`LegalDocInspectorV2/jsons/`**.

---

## 7. Детализация: файлы по каталогам и классы/модули

Ниже — **ориентир для реализации**, а не жёсткое ТЗ: имена классов и файлов можно уточнить при выборе фреймворка (FastAPI, структура React). Для **Python** перечислены классы там, где уместна ОО-модель; **Celery-задачи** часто оформляют как функции — это отмечено. Для **React** (§ 6) используются **функциональные компоненты**; вместо «классов» в привычном смысле — **типы/интерфейсы TypeScript** и **модульные хуки**; где полезен единый контракт с API — класс **`ApiClient`**.

Легаси **не дублируется**: классы **`TableParser`**, функция **`calculate_penalty`**, генераторы **`ClaimGenerator`** / **`CalculationClaimGenerator`** из `LegalDocInspector` — **внешние**; ниже — **обёртки и оркестрация** в новом коде.

### 7.1. Вариант MVP: один Python-пакет внутри `services/bff-orchestrator/`

При монолитном деплое (FullSpecification § 6, версия B) всё серверное может жить в одном репозитории с такой раскладкой:

```
services/bff-orchestrator/
├── Dockerfile
├── pyproject.toml / requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── main.py                         # точка входа: FastAPI app, lifespan, подключение роутеров
│   ├── config.py                       # класс Settings (pydantic-settings) — STORAGE_ROOT, CELERY_BROKER, TTL, пути к легаси
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                     # зависимости FastAPI: get_package_service, get_storage
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── packages.py             # POST /packages, GET/PUT …/form, extract, calculate, documents
│   │       ├── auth.py                 # login/logout (если сессия в API)
│   │       └── health.py               # GET /health
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── package_state.py            # enum PackageState (created → … → documents_ready)
│   │   └── models.py                   # dataclass / Pydantic: PackageMeta, DocumentSet, поля формы (см. jsons)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── package_registry.py         # класс PackageRegistry — in-memory хранилище пакетов по packageId
│   │   ├── package_service.py          # класс PackageService — создание пакета, смена состояния, привязка файлов
│   │   ├── upload_service.py           # класс UploadService — приём multipart, сохранение в FileSystemStorage
│   │   ├── extraction_service.py       # класс ExtractionService — постановка задач Celery, агрегация extraction progress
│   │   ├── parse_facade.py             # класс ParseFacade — сборка parse JSON → вызовы цепочки парсеров (PDF/ЕГРЮЛ/Excel)
│   │   ├── calculation_service.py      # класс CalculationService — сборка calculate_penalty_input, вызов адаптера калькулятора
│   │   └── document_generation_service.py  # класс DocumentGenerationService — create_doc_input, вызов генераторов DOCX
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── legacy/
│   │   │   ├── table_parser_adapter.py # класс TableParserAdapter — open/parse/close TableParser, перехват RuntimeError
│   │   │   ├── penalty_adapter.py      # класс PenaltyAdapter — вызов calculate_penalty + enrich contract_number/type
│   │   │   ├── calculator_adapter.py   # класс/модуль: обёртка convert_data (как в legal_doc_inspector.utils)
│   │   │   └── docx_generator_adapter.py # класс DocxGeneratorAdapter — вызов ClaimGenerator / CalculationClaimGenerator
│   │   └── storage/
│   │       └── filesystem_storage.py   # класс FileSystemStorage — абстракция путей по packageId, TTL-удаление
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py               # экземпляр Celery, конфиг брокера RabbitMQ
│   │   └── tasks/
│   │       ├── extract_pipeline.py     # задачи: extract_egrul_task, extract_contract_task, … (функции или классы Task)
│   │       └── ocr_pipeline.py         # задача OCR-страницы / очереди
│   └── integrations/
│       └── ocr_engine.py               # класс OcrEngine (интерфейс) + реализация по config (движок как в ТЗ § 4.2)
```

**Кратко по ответственности классов:**

| Класс | Назначение |
|--------|------------|
| `Settings` | Конфигурация окружения и путей. |
| `PackageRegistry` | Единственный in-memory реестр активных пакетов (нет БД, § 6). |
| `PackageService` | Жизненный цикл пакета, валидация лимитов (30 комплектов, 20 справок). |
| `UploadService` | Загрузка файлов во вложенность по `packageId`. |
| `ExtractionService` | Запуск/отслеживание извлечения, polling-ответы для UI. |
| `ParseFacade` | Маппинг данных в контракт `parse_*` / `parsing_results`. |
| `CalculationService` | Формирование входа калькулятора, объединение `claim_data` + `calculator_list`. |
| `DocumentGenerationService` | Подготовка `create_doc_input`, пути выдачи `isk_*.docx`, `calculation_*.docx`. |
| `TableParserAdapter` | Изолированный вызов `TableParser` без изменения легаси. |
| `PenaltyAdapter` | Вызов `calculate_penalty` и постобогащение результата. |
| `DocxGeneratorAdapter` | Вызов генераторов DOCX из `doc_creator`. |
| `FileSystemStorage` | Контракт хранения файлов по Т § 9 (`STORAGE_ROOT`). |
| `OcrEngine` (+ реализация) | Подменяемый OCR по config (§ 4.2). |

---

### 7.2. Выделенные сервисы `services/*` (если не монолит)

Если каждый каталог из § 2 — отдельный образ, типовое содержимое:

| Каталог | Ключевые файлы | Классы / сущности |
|---------|----------------|-------------------|
| `extract-egrul/` | `main.py` или worker, `extractor.py` | `EgrulExtractor` — OCR + поля из PDF выписки |
| `extract-contract/` | `extractor.py` | `ContractExtractor` |
| `extract-preclaim/` | `extractor.py` | `PreClaimExtractor` |
| `extract-debt-certificate/` | `extractor.py` | `DebtCertificateExtractor` — использует `TableParserAdapter` или внутренний вызов `TableParser` |
| `ocr-pipeline/` | `pipeline.py`, `page_worker.py` | `OcrPipeline`, `PageTask` |
| `calculation-service/` | `service.py` | `CalculationService` (тонкий слой; дублирует логику с 7.1 или вызывается по HTTP) |
| `docx-generator/` | `service.py` | `DocumentGenerationService` / `DocxGeneratorAdapter` |

В каждом — свой `Dockerfile`, `requirements.txt`, при необходимости HTTP-сервер с одним ресурсом или только Celery worker.

---

### 7.3. Фронтенд `apps/web/`

Рекомендуемая раскладка (создание через Vite или CRA — на выбор):

```
apps/web/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── public/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/
│   │   └── AppRouter.tsx               # маршруты: login, package workspace
│   ├── api/
│   │   ├── client.ts                 # класс ApiClient — baseURL, fetch, заголовки, cookie/session
│   │   └── endpoints.ts              # функции-обёртки: createPackage, uploadFiles, extract, getForm, calculate, getDocuments
│   ├── types/
│   │   ├── package.ts                # TypeScript: interface PackageDto, DocumentSetDto, FormState …
│   │   └── api.ts                    # типы ответов API
│   ├── features/
│   │   ├── auth/
│   │   │   └── LoginPage.tsx
│   │   ├── package-upload/
│   │   │   ├── PackageUploadPage.tsx
│   │   │   └── components/           # Dropzone, DocSetList, SpravkaRow …
│   │   ├── extraction/
│   │   │   └── ExtractionProgress.tsx
│   │   ├── form/
│   │   │   ├── ClaimFormPage.tsx     # суд, истец, ответчик, иск, расчёты по комплектам
│   │   │   └── components/           # FieldGroup, ConflictBanner …
│   │   └── documents/
│   │       └── DownloadToolbar.tsx   # два скачивания DOCX
│   ├── hooks/
│   │   ├── usePackagePolling.ts      # polling extraction status
│   │   └── useBeforeUnload.ts
│   └── styles/
│       └── global.css
```

**По «классам» на фронте:** в React 18 **компоненты — функции**; «классом» в архитектурном смысле можно считать **`ApiClient`** (инкапсуляция HTTP). Дополнительно полезны **интерфейсы TypeScript** в `types/` для строгого соответствия `contracts/` и `jsons/`.

---

### 7.4. `contracts/`

```
contracts/
├── openapi/
│   └── api-v1.yaml                   # или api-v1.yaml + fragments/ — ресурсы из FullSpecification § 7
└── json-schema/
    ├── package-upload.json
    ├── form-state.json
    ├── extraction-result.json
    ├── calculate-request.json
    └── calculate-response.json       # claim_data + calculator_list
```

Файлы — **не классы**, а **схемы**; валидация на сервере: `jsonschema` / Pydantic, сгенерированные модели из OpenAPI (опционально).

---

### 7.5. `packages/shared-types/` (опционально)

```
packages/shared-types/
├── package.json
└── src/
    ├── index.ts                      # реэкспорт типов пакета, формы, API
    └── package.ts
```

Общие **TypeScript-типы** для `apps/web` и, при необходимости, генерации клиента из OpenAPI.

---

### 7.6. `packages/debt-certificate-parser/` (опционально)

Если выносим обёртку над легаси в отдельный пакет:

- `wrapper.py` — класс **`DebtCertificateParser`** (тонкая оболочка над `TableParser` + единый формат ошибок).
- Или только типы для `parsed_info` без дублирования логики парсера.

---

### 7.7. `infra/`

| Файл | Содержимое |
|------|------------|
| `docker-compose.yml` | Сервисы: `web` (nginx/caddy + статика), `api` (bff-orchestrator), `rabbitmq`, `worker` (celery), при необходимости отдельные `ocr-worker`. |
| `nginx.conf` / `Caddyfile` | Прокси `/` → SPA, `/api` → Python, TLS при необходимости. |
| `data/.gitkeep` | Плейсхолдер; реальные файлы в .gitignore. |
| `k8s/*.yaml` | Опционально: Deployment/Service для сервисов из § 2. |

---

### 7.8. Связь с легаси (импорты, не новые файлы внутри легаси)

Новый код **импортирует** (пути зависят от установки пакета `LegalDocInspector`):

- `legal_doc_inspector.exel_parser.TableParser`
- `legal_doc_inspector.calculator.penalty_calculator.calculate_penalty`
- `legal_doc_inspector.utils.calculator_adapter` — `convert_data` (как в TZ-12 § 12.3)
- `legal_doc_inspector.doc_creator` — классы генерации DOCX (имена как в текущем репозитории)

Классы **`ClaimGenerator`** / **`CalculationClaimGenerator`** упоминаются в TZ-12 § 12.4; точные имена файлов — в каталоге `doc_creator/` легаси (см. при реализации).

---

## 8. Примечание о неопределённости

Точный список файлов в `doc_creator`/`routes.py` легаси и выбор **FastAPI vs Flask** для оркестратора в ТЗ **не зафиксированы**; при появлении единого OpenAPI (Доп. 7 — открытые вопросы) структуру `api/routes/` и DTO можно **свести** к одному файлу `openapi.yaml` в `contracts/openapi/`.
