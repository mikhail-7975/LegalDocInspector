# Дополнение 12. Использование существующей реализации (без изменений ядра)

## 12.0. Ограничение

**Запрещено вносить изменения** в файлы:

- [`LegalDocInspector/legal_doc_inspector/calculator/penalty_calculator.py`](../LegalDocInspector/legal_doc_inspector/calculator/penalty_calculator.py)
- [`LegalDocInspector/legal_doc_inspector/exel_parser.py`](../LegalDocInspector/legal_doc_inspector/exel_parser.py)

Любая новая логика (OCR, API, очереди, React) должна **вызывать** эти модули как есть или **оборачивать** их, адаптируя только входные/выходные данные снаружи.

Эталонные структуры JSON: каталог [`LegalDocInspectorV2/jsons/`](./jsons/). Подробная расшифровка полей — в [`TZ-supplement-08-modeli-json.md`](./TZ-supplement-08-modeli-json.md).

---

## 12.1. Парсер Excel — `TableParser` (`exel_parser.py`)

### 12.1.1. Назначение

Класс **`TableParser`** читает **один** файл справки о задолженности в формате Excel (через `pandas.read_excel`, **лист 0**, **без заголовка**, `header=None`). Разметка листа **жёстко зашита** в коде: осмысленные строки таблицы начинаются с **индекса строки 12** (строки 0–11 — шапка). Файл должен быть **без формул в ячейках** (только значения), иначе поведение чтения не гарантируется.

### 12.1.2. Последовательность вызовов

```python
from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser

parser = TableParser()
parser.open("/абсолютный/путь/к/справке.xlsx")
try:
    periods = parser.parse()  # dict
finally:
    parser.close()
```

### 12.1.3. Результат `parse()`

Возвращается **`dict`**, ключи — строки вида **`"Январь 2025"`** (название месяца на русском + год). Значение по каждому ключу:

```text
{
  "accrual": {
    "accruals": [ {"accrual": <number>, "period": "MM.YYYY"}, ... ],
    "payments": [ {"payment": <number>, "date": "DD.MM.YYYY", "contract_type": <int>}, ... ],
    "additionals": [ {"accrual": <number>, "period": "MM.YYYY"}, ... ],
    "total_amount_of_accruals": <number | None>,
    "total_amount_of_payments": <number | None>,
    "debt": <number | None>
  },
  "adjustment": { ... та же структура ... }
}
```

Пустые месяцы (нулевые долги в обоих блоках) **удаляются** перед возвратом. При несоответствии строки ожидаемым шаблонам парсер **бросает** `RuntimeError` (см. `row_type` в коде).

### 12.1.4. Связь с эталонными JSON

- Фрагменты с ключами месяцев и вложенными `accrual` / `adjustment` в [`parse_output.json`](./jsons/parse_output.json) (внутри `table_parser_result`) и в [`calculate_penalty_input.json`](./jsons/calculate_penalty_input.json) (поле `parsing_results[].parsed_info`) соответствуют **прямому выводу** `parse()` для одного договора/справки, если их собрать в одну структуру по месяцам.

### 12.1.5. Интеграция в пайплайн

- Один файл справки → один вызов `open` + `parse` → один словарь `periods`.
- Несколько комплектов → **отдельный** разбор каждой справки; дальше для каждого комплекта формируется элемент `parsing_results[]` (см. §12.3).
- Ошибки парсинга **не перехватываются** внутри `exel_parser.py`: новый код должен ловить исключения и переводить их в UX/ответ API (см. ТЗ про ручной ввод и сообщения).

---

## 12.2. Калькулятор пени — `calculate_penalty` (`penalty_calculator.py`)

### 12.2.1. Сигнатура

```python
from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import calculate_penalty

result = calculate_penalty(
    parsed_data: dict,      # тот же формат, что parse() для ОДНОГО договора
    day_of_penalty: int,    # число месяца оплаты (день дедлайна)
    company_type: str,     # например "ТСЖ" — влияет на разбиение периодов пени
    end_date: str,          # конец расчёта: "DD.MM.YYYY"
)
```

- **`parsed_data`**: словарь месяцев **`"Месяц ГГГГ"` → `{ "accrual": {...}, "adjustment": {...} }`**, как после `TableParser.parse()`. Калькулятор внутри вызывает **`sort_dict_by_months`** — порядок ключей может быть нормализован.
- **`end_date`**: строго **`%d.%m.%Y`** (как в `strptime` внутри функции).
- Возвращается **`dict`**, описывающий таблицу расчёта для **одного** договора (без номера договора внутри; его добавляет обёртка, см. §12.3).

### 12.2.2. Структура возвращаемого значения

Корневые ключи результата (имена месяцев — как во входе):

| Ключ | Содержимое |
|------|------------|
| `start_of_table` | `{ "text1", "text2", "start", "end" }` — даты строкой `DD.MM.YYYY`. |
| `"Январь 2025"`, … | **Список** элементов-строк таблицы: `type` = `debt_accrual`, `correcting`, `payment_before_penalty`, `penalty_period`, `field`, `debt_info` и т.д. (как в [`calculate_penalty_output.json`](./jsons/calculate_penalty_output.json) → `calculator_list[0]`). |
| `end_of_table1` | Итог основного долга: `text`, `money`, `type`. |
| `end_of_table2` | Итог пеней. |
| `debt_info` | Сводные `accrual_debt`, `correcting_debt`. |

Суммы в строках — в основном **строки**, отформатированные через **`StrictFormattedMoney`** (пробелы тысяч, запятая в дробной части).

### 12.2.3. Внешние зависимости калькулятора

Модуль использует **HTTP** к сервису выходных дней (логика `_is_holiday` / `requests`) — при интеграции в новый деплой нужно обеспечить доступность этого сервиса или учитывать сетевые ошибки **снаружи** `penalty_calculator.py` (файл не менять).

### 12.2.4. Связь с эталонными JSON

- Вход: [`calculate_penalty_input.json`](./jsons/calculate_penalty_input.json) (`company_type`, `end_date`, `parsing_results[]`; для одного вызова функции используется **один** элемент и его `parsed_info`).
- Выход до обогащения полями договора: структура совпадает с элементом [`calculate_penalty_output.json`](./jsons/calculate_penalty_output.json) → `calculator_list[]` (после добавления `contract_number` и `contract_type` в текущем backend).

---

## 12.3. Как это собрано в действующем backend (ориентир для нового кода)

Файл [`LegalDocInspector/backend/routes.py`](../LegalDocInspector/backend/routes.py), маршрут **`POST /calculate_penalty`**:

1. Тело запроса — JSON с полями **`company_type`**, **`end_date`** (`DD.MM.YYYY`), **`parsing_results`** — массив.
2. Для **каждого** элемента `parsing_results` вызывается:

   ```python
   calculate_penalty(
       parsed_data=item["parsed_info"],
       day_of_penalty=item["day_of_penalty"],
       company_type=data["company_type"],
       end_date=data["end_date"],
   )
   ```

3. К каждому результату дописываются **`contract_number`** и **`contract_type`** из того же элемента.
4. Список результатов прогоняется через **`convert_data`** ([`calculator_adapter.py`](../LegalDocInspector/legal_doc_inspector/utils/calculator_adapter.py)), формируется **`claim_data`** для генераторов DOCX; в ответе клиенту — **`claim_data`** + **`calculator_list`**.

Новый оркестратор может повторить этот контракт **без правок** `penalty_calculator.py` / `exel_parser.py`, только вызывая их и при необходимости копируя шаг с `convert_data` (или эквивалент с той же семантикой).

### 12.3.1. Минимальный псевдо-контракт тела `POST /calculate_penalty`

См. образец в [`calculate_penalty_input.json`](./jsons/calculate_penalty_input.json): верхний уровень + массив `parsing_results`, где каждый элемент содержит как минимум:

- `parsed_info` — словарь месяцев (выход `TableParser.parse()`),
- `contract_point`, `day_of_penalty`, `contract_type`, `contract_number`.

---

## 12.4. Сквозная цепочка «справка → расчёт → эталон выхода»

1. **Excel** → `TableParser.open` + `parse()` → `parsed_info`.
2. Собрать объект **`parsing_results[]`** (договорные поля из PDF/ручного ввода + `parsed_info`).
3. **`calculate_penalty(parsed_info, …)`** → элемент **`calculator_list`** (+ `contract_number` / `contract_type`).
4. **`convert_data(...)`** (как в backend) → **`claim_data`**.
5. **`claim_data` + `calculator_list` + `path_to_save`** — вход для [`create_doc_input.json`](./jsons/create_doc_input.json) / генераторов исков и расчёта (см. `ClaimGenerator`, `CalculationClaimGenerator` в `doc_creator`).

Полные поля **`claim_data`** (истец, ответчик, `lawsuit_info`, …) эталоном служат [`create_doc_input.json`](./jsons/create_doc_input.json) и §8.6 в дополнении 08; они наполняются не только калькулятором, но и парсерами PDF/ЕГРЮЛ и адаптером.

---

## 12.5. Практические замечания

1. **Один вызов `calculate_penalty` — один договор** (одна `parsed_info`). Несколько договоров = несколько элементов в `parsing_results` и несколько объектов в `calculator_list`.
2. **Форматы дат**: для `calculate_penalty` поле `end_date` — **`DD.MM.YYYY`**; в `claim_data.current_date` после `convert_data` получается **`YYYY-MM-DD`** — это нормализация адаптера, не калькулятора.
3. **Не смешивать** ключи адреса ответчика: в выдаче парсера ЕГРЮЛ в коде встречается `address`, в `claim_data` — `addres`; при сборке объекта для Word нужно следовать ожиданиям **`convert_data`** и генераторов (их можно менять; **`penalty_calculator` / `exel_parser`** — нет).
4. При сбое сети/праздников внутри калькулятора обработка — на стороне вызывающего кода (повтор запроса, сообщение пользователю), **без правок** `penalty_calculator.py`.

---

## 12.6. Быстрая проверка по репозиторию

| Шаг | Файл-образец |
|-----|----------------|
| Метаданные запроса разбора (дата, число комплектов/справок) | [`parse_input.json`](./jsons/parse_input.json) |
| Результат разбора: таблица + `defendant_info` + путь сохранения | [`parse_output.json`](./jsons/parse_output.json) |
| Вход калькулятора | [`calculate_penalty_input.json`](./jsons/calculate_penalty_input.json) |
| Выход API расчёта (`claim_data` + `calculator_list`) | [`calculate_penalty_output.json`](./jsons/calculate_penalty_output.json) |
| Вход генерации DOCX | [`create_doc_input.json`](./jsons/create_doc_input.json) |

Для локальной отладки **только** пары «справка → словарь месяцев» достаточно скрипта с `TableParser` + сохранение `periods` в JSON и сравнение с фрагментом `parsed_info` из эталона.
