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

### Запуск бекенда

```
python run.py
```

### Запуск фронтенда 

```
python -m streamlit run streamlit/interface.py
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
