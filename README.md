# LegalDocInspector

## Установка

Требуемая версия python `3.11`

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo apt-get install -y poppler-utils tesseract-ocr-rus
```

## Запуск

### Бэкенд и Streamlit вместе

Из корня репозитория (активированное виртуальное окружение):

```
python scripts/run_dev.py
```

Поднимаются API-бэкенд (`http://localhost:5001`) и Streamlit (`http://127.0.0.1:8501`, не порт 3000). Остановка — `Ctrl+C`.

### Сборка exe (Windows)

```
pip install -r requirements-build.txt
python scripts/build_exe.py
```

Перед сборкой не открывайте терминал в `dist\LegalDocInspector`. Рекомендуется: `python scripts/build_exe.py --force-kill --clean` (старый dist переименуется в `dist\_LegalDocInspector_backup_*`).

Запуск: `dist\LegalDocInspector\LegalDocInspector.exe` (нужен Tesseract OCR в PATH). Сборка может занять много времени и места на диске из‑за torch/docling. После `build_exe.py` рядом с exe: `data\`, `configs\`, `.streamlit\`, `LegalDocInspector\streamlit\`.

### Запуск бекенда

```
python run.py
```

### Запуск фронтенда

Веб-интерфейс (Flask):

```
cd web_frontend
python app.py
```

Streamlit:

```
python -m streamlit run LegalDocInspector/streamlit/interface.py
```

## Тестирование

### вариант 1

```
python -m pytest
```

### вариант 2

```
pytest
```
