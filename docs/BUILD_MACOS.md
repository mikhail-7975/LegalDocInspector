# Сборка дистрибутива LegalDocInspector для macOS

Дистрибутив собирается из той же точки входа, что и локальная разработка — [`scripts/run_dev.py`](../scripts/run_dev.py). После сборки запускается один бинарник, который поднимает Flask-бэкенд (`:5001`) и Streamlit (`:8501`).

## Требования

| Компонент | Версия / примечание |
|-----------|---------------------|
| macOS | 12+ (Monterey и новее) |
| Python | 3.11 |
| Xcode CLI | `xcode-select --install` |
| Homebrew | для Tesseract OCR |
| Свободное место | 8–15 ГБ (torch + docling + модели) |
| Интернет | при первой сборке (скачивание моделей docling) |

**Архитектура:** сборку нужно выполнять на той же платформе, для которой предназначен дистрибутив:

- Apple Silicon (M1/M2/M3) → `arm64`
- Intel Mac → `x86_64`

Универсальный бинарник (fat binary) для torch/docling в этом проекте не поддерживается.

## Подготовка окружения

Из корня репозитория (рекомендуется один скрипт — учитывает macOS 13 и `docling-parse`):

```bash
cd /path/to/LegalDocInspector

python3.11 -m venv .venv
source .venv/bin/activate

python scripts/setup_macos_env.py
```

Скрипт [`scripts/setup_macos_env.py`](../scripts/setup_macos_env.py):
- ставит `requirements-macos.txt` (не `requirements.txt` — там `pywin32` только для Windows);
- на macOS 13 и ниже перетегирует wheel `docling-parse` (официальные wheel — только `macosx_14_0_*`);
- ставит `requirements-build.txt` (PyInstaller);
- опционально Tesseract через Homebrew.

Вручную (macOS 14+):

```bash
pip install --upgrade pip
pip install -r requirements-macos.txt
pip install -r requirements-build.txt
```

Tesseract (нужен для OCR в PDF):

```bash
brew install tesseract tesseract-lang
tesseract --version
tesseract --list-langs | grep rus
```

## Сборка

### Базовая (рекомендуется для первого раза)

```bash
source .venv/bin/activate
python scripts/build_macos.py --clean
```

Скрипт:

1. Скачивает модели docling в `vendor/docling-models/` (если их ещё нет).
2. Запускает PyInstaller по [`scripts/LegalDocInspector.spec`](../scripts/LegalDocInspector.spec).
3. Копирует `data/`, `configs/`, `.streamlit/`, модели и UI Streamlit в каталог дистрибутива.
4. Создаёт `Launch LegalDocInspector.command` и `README.txt`.

По умолчанию результат попадает в каталог с меткой времени:

```
dist/LegalDocInspector_YYYYMMDD_HHMMSS/
```

### Фиксированное имя каталога

```bash
python scripts/build_macos.py --fixed-name --force-kill --clean
```

Результат: `dist/LegalDocInspector/` (старая сборка переименуется или удалится).

### Быстрая сборка (меньше моделей)

```bash
python scripts/build_macos.py --models-minimal --clean
```

Скачиваются только layout и tableformer — быстрее и меньше размер `dist/`.

### Пропуск повторной загрузки моделей

Если `vendor/docling-models/` уже заполнен:

```bash
python scripts/build_macos.py --skip-models --clean
```

### DMG для распространения

Вариант 1 — сразу при сборке:

```bash
python scripts/build_macos.py --clean --dmg
```

Вариант 2 — из готовой папки:

```bash
python scripts/build_macos_dmg.py
python scripts/build_macos_dmg.py --dist dist/LegalDocInspector
```

DMG создаётся в `dist/<имя_сборки>.dmg`.

### Ad-hoc подпись (локальный запуск)

Для уменьшения предупреждений Gatekeeper при тестировании на своей машине:

```bash
python scripts/build_macos.py --codesign
```

Для распространения вне организации потребуется подпись Developer ID и нотаризация Apple — это отдельный процесс, не входящий в скрипты проекта.

## Запуск дистрибутива

### Из терминала

```bash
cd dist/LegalDocInspector_YYYYMMDD_HHMMSS
./LegalDocInspector
```

### Двойной клик

Откройте `Launch LegalDocInspector.command` в Finder — откроется Terminal с запущенным приложением.

После старта:

- Бэкенд: http://localhost:5001
- Streamlit: http://localhost:8501

Остановка: `Ctrl+C` в терминале.

## Структура дистрибутива

```
dist/LegalDocInspector_.../
├── LegalDocInspector              # главный бинарник (аналог run_dev.py)
├── Launch LegalDocInspector.command
├── README.txt
├── _internal/                     # зависимости PyInstaller
├── models/                        # модели docling (offline)
├── data/
├── configs/
├── .streamlit/
└── LegalDocInspector/streamlit/   # UI
```

## Устранение проблем

### «Терминал открыт внутри dist»

Перейдите в корень репозитория и повторите сборку:

```bash
cd /path/to/LegalDocInspector
python scripts/build_macos.py --force-kill --clean
```

### macOS блокирует запуск (Gatekeeper / quarantine)

```bash
xattr -cr "dist/LegalDocInspector"
```

или для конкретной сборки с датой в имени.

### Tesseract не найден

```bash
brew install tesseract tesseract-lang
which tesseract
```

Либо укажите путь явно перед запуском:

```bash
export TESSERACT_CMD="$(brew --prefix tesseract)/bin/tesseract"
./LegalDocInspector
```

### Порт 5001 или 8501 занят

Завершите предыдущий экземпляр:

```bash
pkill -x LegalDocInspector
```

### Долгая сборка PyInstaller

Нормально для стека torch + docling + streamlit. Первая сборка может занять 30–60+ минут. Повторные быстрее, если не использовать `--clean`.

### Нехватка места на диске

Используйте `--models-minimal` или очистите старые сборки в `dist/` и `build/`.

## Сравнение с Windows

| | Windows | macOS |
|---|---------|-------|
| Скрипт сборки | `scripts/build_exe.py` | `scripts/build_macos.py` |
| Бинарник | `LegalDocInspector.exe` | `LegalDocInspector` |
| Установщик | `scripts/build_installer.py` (Inno Setup) | DMG (`--dmg` или `build_macos_dmg.py`) |
| OCR | Tesseract installer | `brew install tesseract tesseract-lang` |
| Spec PyInstaller | `scripts/LegalDocInspector.spec` | тот же файл |

## Полезные флаги `build_macos.py`

| Флаг | Описание |
|------|----------|
| `--clean` | Очистить кэш PyInstaller |
| `--force-kill` | Завершить запущенный LegalDocInspector |
| `--fixed-name` | Собрать в `dist/LegalDocInspector` |
| `--skip-models` | Не скачивать модели |
| `--models-minimal` | Только layout + tableformer |
| `--models-force` | Перекачать модели |
| `--dmg` | Создать DMG после сборки |
| `--codesign` | Ad-hoc подпись (`codesign -s -`) |
