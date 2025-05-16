# LegalDocInspector

## Установка

Требуемая версия python `3.11`

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск
### Запуск бекенда

```
python run.py
```
### Запуск фронтенда 
```
python -m streamlit run ./legal_doc_inspector/app/app.py
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