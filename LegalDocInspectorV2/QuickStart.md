# Quickstart: развёртывание сервиса (Linux, macOS, Windows)

Краткая инструкция по запуску целевого стека по [`technical_specification/FullSpecification.md`](technical_specification/FullSpecification.md) и [`ProjectStructure.md`](ProjectStructure.md): **React (SPA)**, **Python API (оркестратор)**, **Celery**, **RabbitMQ**, **reverse proxy**, файловое хранилище по `packageId`, зависимость от легаси [`LegalDocInspector`](../LegalDocInspector/) и `data/templates/`.

> В репозитории есть рабочий каркас: `infra/docker-compose.yml`, `services/bff-orchestrator/`, `apps/web/`. Пути к Python и переменные окружения уточняйте в [`README.md`](../README.md) и `services/bff-orchestrator/README.md`.

---

## Общие требования

| Компонент | Назначение |
|-----------|------------|
| **Docker** (для варианта A) | Docker Engine / Docker Desktop, **Compose v2** (`docker compose`, не обязательно старый `docker-compose`) |
| **Python 3.11+** (для варианта B) | Backend и Celery worker в `venv` |
| **Node.js 20 LTS** (для варианта B) | Сборка `apps/web` |
| **RabbitMQ** | Брокер для Celery (в Docker или отдельная установка) |
| **Легаси** | Репозиторий `LegalDocInspector` доступен для `PYTHONPATH` или установки пакета; шаблоны Word — `data/templates/` |

Переменные окружения (типовые имена, уточнять в реализации):

- `STORAGE_ROOT` — корень файлового хранилища (FullSpecification § 6, Т § 9).
- `CELERY_BROKER_URL` — например `amqp://guest:guest@localhost:5672//`.
- Пути к шаблонам и легаси — по [`TZ-supplement-12-existing-code-usage.md`](technical_specification/TZ-supplement-12-existing-code-usage.md).

---

## Вариант A: Docker (рекомендуется для всех ОС)

Одинаковая логика на **Linux**, **macOS** и **Windows** (через **Docker Desktop**).

### A.1. Установка Docker

| ОС | Действия |
|----|----------|
| **Linux** | Установите [Docker Engine](https://docs.docker.com/engine/install/) и плагин Compose; пользователь в группе `docker` или запуск с `sudo` по политике организации. |
| **macOS** | [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) (Apple Silicon / Intel — соответствующая сборка). |
| **Windows** | [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) с **WSL 2** (рекомендуется для объёма файлов и путей). Без WSL возможны ограничения; для разработки удобнее WSL2 + Linux-дистрибутив и Docker внутри WSL. |

### A.2. Запуск

```bash
cd /путь/к/репозиторию/LegalDocInspector
cp infra/.env.example infra/.env   # при необходимости; отредактировать STORAGE_ROOT и прочее
docker compose -f infra/docker-compose.yml up --build
```

- Статика SPA и API обычно доступны на порту **80** или **443** у reverse proxy (см. `infra/docker-compose.yml`).
- Проверка API: `curl -sf http://localhost:<порт>/health` (см. [`MonitoringGuide.md`](MonitoringGuide.md)).

### A.3. Остановка

```bash
docker compose -f infra/docker-compose.yml down
```

Добавьте `-v` только если нужно удалить именованные тома (данные хранилища).

---

## Вариант B: Без Docker — `venv` + локальные процессы

Подходит для разработки backend/frontend на машине разработчика. **RabbitMQ** проще всего поднять **одним контейнером** (гибрид) или установить нативно.

### B.1. Linux

1. Установите зависимости системы (пример для Debian/Ubuntu): build-essential, при необходимости библиотеки для OCR/Python wheels.
2. **RabbitMQ:**  
   `sudo apt install rabbitmq-server` и включите сервис **или** только брокер в Docker:  
   `docker run -d --hostname rabbit --name rabbit -p 5672:5672 rabbitmq:3-management`
3. Клонируйте монорепозиторий и легаси рядом, как ожидает `PYTHONPATH`.
4. Backend:

```bash
cd services/bff-orchestrator
python3.12 -m venv .venv   # нужен Python 3.10+ (легаси-калькулятор)
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
# Для полного контура PDF/OCR: pip install -r ../../requirements.txt
export STORAGE_ROOT=/var/tmp/legaldoc-storage
export CELERY_BROKER_URL=amqp://guest:guest@127.0.0.1:5672//
export PYTHONPATH="../../:src"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. В **втором терминале** — worker Celery:

```bash
cd services/bff-orchestrator
source .venv/bin/activate
export STORAGE_ROOT=... CELERY_BROKER_URL=... PYTHONPATH=../../:src
celery -A app.workers.celery_app worker --loglevel=INFO
```

6. Frontend:

```bash
cd apps/web
npm ci
npm run dev
```

Прокси `vite.config.ts` перенаправляет `/api` на `http://127.0.0.1:8000`; при смене порта API обновите прокси.

---

### B.2. macOS

1. Установите **Python 3** и **Node** (официальные установщики или [Homebrew](https://brew.sh/): `brew install python node rabbitmq` — по желанию).
2. RabbitMQ: `brew services start rabbitmq` **или** Docker-контейнер как в Linux.
3. Далее те же команды, что в **B.1**, с активацией venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Пути к `LegalDocInspector` и `STORAGE_ROOT` задайте в POSIX-формате, например `/Users/you/projects/...`.

---

### B.3. Windows

1. Установите **Python 3** с [python.org](https://www.python.org/) (отметьте «Add Python to PATH») и **Node.js** LTS.
2. **RabbitMQ:** проще всего **Docker Desktop** только для контейнера `rabbitmq` (порт **5672**) **или** установка RabbitMQ для Windows с [официального сайта](https://www.rabbitmq.com/docs/install-windows) (требуется Erlang).
3. Откройте **PowerShell** или **cmd** в каталоге `services/bff-orchestrator`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
$env:STORAGE_ROOT = "C:\temp\legaldoc-storage"
$env:CELERY_BROKER_URL = "amqp://guest:guest@127.0.0.1:5672//"
$env:PYTHONPATH = "C:\path\to\LegalDocInspector"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Во **втором окне** с активированным тем же `venv`:

```powershell
celery -A app.workers.celery_app worker --loglevel=INFO
```

4. Frontend:

```powershell
cd apps\web
npm ci
npm run dev
```

**Замечания для Windows:**

- Используйте пути с обратными слэшами или экранирование в `PYTHONPATH`.
- Если политика запрещает скрипты: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Для путей совместимости с легаси иногда удобнее разрабатывать в **WSL2** (Ubuntu) и следовать разделу **B.1**.

---

## Гибрид: только RabbitMQ в Docker, остальное в venv

Универсально для всех ОС:

```bash
docker run -d --name rabbitmq-dev -p 5672:5672 -p 15672:15672 rabbitmq:3-management
export CELERY_BROKER_URL=amqp://guest:guest@127.0.0.1:5672//
```

Далее API и Celery запускаются локально из **venv**, как в **B.1–B.3**.

---

## Проверка после запуска

1. `GET /health` у API.
2. Логи без бесконечных traceback при старте (см. [`MonitoringGuide.md`](MonitoringGuide.md)).
3. UI открывается, авторизация по ТЗ (логин/пароль; тестовый `admin` — если включено в конфиге).

---

## Связанные документы

- [`ProjectStructure.md`](ProjectStructure.md) — структура каталогов и модулей.
- [`MonitoringGuide.md`](MonitoringGuide.md) — логи, health, расследование сбоев.
- [`technical_specification/TZ-supplement-12-existing-code-usage.md`](technical_specification/TZ-supplement-12-existing-code-usage.md) — подключение легаси.
