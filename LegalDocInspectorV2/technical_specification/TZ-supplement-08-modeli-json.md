# Дополнение к разделу 8. Модели JSON

> Эталонные структуры данных сняты с файлов в каталоге [`jsons/`](./jsons/). Они отражают **фактический формат**, в котором существующий Python-код (парсер таблицы, калькулятор пени, генераторы DOCX) принимает и возвращает данные. Поля с опечатками в ключах (`addres`, `correspondency_addres`, `responsitive_name`) **сохраняются как в коде** до отдельного рефакторинга.

---

## 8.0. Перечень эталонных файлов

| Файл | Назначение |
|------|------------|
| [`parse_input.json`](./jsons/parse_input.json) | Вход парсера/пайплайна разбора (дата запроса, число справок и комплектов). |
| [`parse_output.json`](./jsons/parse_output.json) | Выход разбора: таблица задолженности по комплектам + данные ответчика (ЕГРЮЛ) + путь сохранения артефактов. |
| [`calculate_penalty_input.json`](./jsons/calculate_penalty_input.json) | Вход расчёта пени: тип компании, конечная дата, нормализованные `parsing_results` по договорам. |
| [`calculate_penalty_output.json`](./jsons/calculate_penalty_output.json) | Выход расчёта: агрегат `claim_data` для иска + детализированный `calculator_list` (таблица пени по месяцам). |
| [`create_calculating_table_input.json`](./jsons/create_calculating_table_input.json) | Вход построения расчётной таблицы в документе: полный `claim_data` + `calculator_list` + `path_to_save`. |
| [`create_doc_input.json`](./jsons/create_doc_input.json) | Вход генерации иска: тот же состав, что и у `create_calculating_table_input.json` (в эталоне совпадает). |

---

## 8.1. Пакет входных файлов (HTTP / сессия)

В каталоге `jsons/` **нет** модели загрузки файлов (`packageId`, `fileRef`, `mimeType` и т.д.). Это **внешний контракт** нового backend/UI.

**Рекомендация для ТЗ:** идентификатор пакета на стороне API задаётся при создании сессии и **не меняется** при замене файлов в комплекте; метаданные файла (размер, хеш, число страниц) **не выведены из эталонных JSON** — при необходимости добавить в OpenAPI отдельно.

---

## 8.2. `parse_input.json` — запуск разбора

Корневой объект:

| Поле | Тип в эталоне | Описание |
|------|----------------|----------|
| `date` | string | Дата в формате `YYYY-MM-DD`. |
| `1_certificates_count` | string | Число справок (в эталоне строка `"1"`). |
| `complects_count` | string | Число комплектов (строка). |

---

## 8.3. `parse_output.json` — результат разбора

### 8.3.1. `table_parser_result`

Массив **комплектов**. Каждый элемент — массив из семи позиций:

| Индекс | Содержимое |
|--------|------------|
| `0` | Объект: ключи — строки **«Месяц ГГГГ»** (напр. `"Январь 2025"`). Значение — блок `{ "accrual": {…}, "adjustment": {…} }` (структура **8.4**). |
| `1` | Номер договора (строка), напр. `"№ 01.010151-ТЭ от 01.04.2020"`. |
| `2` | Тип договора (строка): `ТЭ`, и т.д. |
| `3` | Пункт договора о сроке оплаты (строка), напр. `"4.5"`. |
| `4` | Число месяца оплаты (строка), напр. `"18"`. |
| `5` | Фрагмент текста договора (условие оплаты / пояснение). |
| `6` | Массив претензий: объекты `{ "claim_date": "DD.MM.YYYY", "claim_number": "…" }`. |

### 8.3.2. `results_of_name_parser`

```json
{
  "defendant_info": {
    "inn": "string",
    "full_name": "string",
    "short_name": "string",
    "address": "string",
    "kpp": "string",
    "ogrn": "string"
  }
}
```

### 8.3.3. Прочее

| Поле | Тип | Описание |
|------|-----|----------|
| `path_to_save` | string | Каталог для сохранения промежуточных/выходных файлов по запросу. |

**Статусы извлечения** (`ok` / `partial` / …) в этих JSON **не представлены** — факт успеха кодируется наличием данных или обрабатывается исключениями в коде.

---

## 8.4. Блок месяца: `accrual` / `adjustment`

Используется в `table_parser_result`, в `parsed_info` и в цепочке до калькулятора.

Внутри каждого из ключей `accrual` и `adjustment`:

| Поле | Тип | Описание |
|------|-----|----------|
| `accruals` | array | Элементы `{ "accrual": number, "period": "MM.YYYY" }`. |
| `payments` | array | Элементы `{ "payment": number, "date": "DD.MM.YYYY", "contract_type": number }`. |
| `additionals` | array | Элементы `{ "accrual": number, "period": "MM.YYYY" }`. |
| `total_amount_of_accruals` | number | |
| `total_amount_of_payments` | number | |
| `debt` | number | |

Денежные величины на этом уровне — **числа** (float). Даты периодов — строки **`DD.MM.YYYY`** или **`MM.YYYY`** в поле `period`.

---

## 8.5. `calculate_penalty_input.json`

Корневой объект:

| Поле | Тип | Описание |
|------|-----|----------|
| `company_type` | string | Напр. `"ТСЖ"`. |
| `end_date` | string | Дата окончания периода расчёта, `DD.MM.YYYY`. |
| `parsing_results` | array | Элементы см. ниже. |

Элемент `parsing_results[]`:

| Поле | Тип | Описание |
|------|-----|----------|
| `parsed_info` | object | Ключи — **«Месяц ГГГГ»**; значения — `{ "accrual": {…}, "adjustment": {…} }` как в **8.4**. |
| `contract_point` | string | Пункт договора. |
| `day_of_penalty` | number | День оплаты (число месяца). |
| `contract_type` | string | Тип договора. |
| `contract_number` | string | Номер договора. |

---

## 8.6. Объект `claim_data` (выход калькулятора / вход генерации)

Встречается в `calculate_penalty_output.json`, `create_calculating_table_input.json`, `create_doc_input.json`.

### 8.6.1. Корневые поля `claim_data`

| Поле | Тип | Описание |
|------|-----|----------|
| `company_type` | string | |
| `current_date` | string | `YYYY-MM-DD`. |
| `contracts_info` | array | Список «кортежей» по одному договору (см. **8.6.2**). |
| `table_info` | object | Сводка по таблице + блоки по номеру договора (см. **8.6.3**). |
| `plaintiff_info` | object | Истец (см. **8.6.4**), в `calculate_penalty_output` может отсутствовать — появляется к генерации. |
| `defendant_info` | object | Ответчик (см. **8.6.5**). |
| `lawsuit_info` | object | Параметры иска (см. **8.6.6**). |
| `responsitive_name` | string | Подписант / ответственное лицо (орфография ключа как в коде). |

### 8.6.2. Элемент `contracts_info`

Массив из **ровно одного элемента** в эталоне — вложенный массив из четырёх элементов:

1. **UUID** (string) — идентификатор договора/комплекта в расчёте.
2. **Номер договора** (string).
3. **Объект показателей** (все суммы — **строки с русским форматированием**: пробелы тысяч, запятая десятичных):

   | Ключ | Пример смысла |
   |------|----------------|
   | `correcting_year` | Год корректировки. |
   | `contract_point` | Пункт договора. |
   | `last_day` | Текст срока оплаты. |
   | `penalty_period` | Период просрочки, текст «с … по …». |
   | `accrual_debt` | Долг начислений. |
   | `correcting_debt` | Долг корректировки. |
   | `contract_periods` | Периоды `MM.YYYY-MM.YYYY`. |
   | `contract_periods_correcting` | То же для корректировки. |
   | `debt` | Суммарный долг. |
   | `penalty` | Пеня. |
   | `debt_penalty` | Долг + пеня. |

4. **Тип договора** (string), напр. `"ТЭ"`.

### 8.6.3. `table_info`

- Ключи **`all_debt`**, **`all_penalty`**, **`cost_of_lawsuit`** — строки сумм.
- Остальные ключи — по **номеру договора** (как в эталоне): объект с теми же полями, что и объект показателей в `contracts_info[2]`.

### 8.6.4. `plaintiff_info`

| Поле | Тип |
|------|-----|
| `inn` | string |
| `full_name` | string |
| `short_name` | string |
| `addres` | string |
| `correspondency_addres` | string |
| `ogrn` | string |

### 8.6.5. `defendant_info`

| Поле | Тип |
|------|-----|
| `full_name` | string |
| `short_name` | string |
| `addres` | string |
| `inn` | string |
| `ogrn` | string |

В `parse_output` у ответчика поле **`address`**, в `claim_data` — **`addres`**; при интеграции учитывать **два варианта ключа**.

### 8.6.6. `lawsuit_info`

| Поле | Тип |
|------|-----|
| `cost` | string (сумма) |
| `tax` | string (госпошлина) |
| `service_type` | string |
| `claims` | array of string — строки вида `"№ … от DD.MM.YYYY"` |

---

## 8.7. `calculator_list` — детализация расчёта пени

Массив объектов (в эталоне один объект на договор). Поля верхнего уровня объекта:

| Поле | Описание |
|------|----------|
| `start_of_table` | `{ "text1", "text2", "start", "end" }` — подписи и даты начала/конца просрочки (`DD.MM.YYYY`). |
| `end_of_table1` | `{ "text", "money", "type": "field" }` — итог основного долга. |
| `end_of_table2` | `{ "text", "money", "type": "field" }` — итог пеней. |
| `debt_info` | `{ "type": "debt_info", "text", "accrual_debt", "correcting_debt" }`. |
| `contract_number`, `contract_type` | Строки. |
| Ключи **`«Месяц ГГГГ»`** | Массив **строк таблицы** (см. ниже). |

### 8.7.1. Типы строк (`type`)

| `type` | Назначение | Характерные поля |
|--------|------------|-------------------|
| `debt_accrual` | Начисление за месяц | `debt`, `period` [date, null, null], `text` |
| `correcting` | Доля годовой корректировки | аналогично |
| `payment_before_penalty` | Погашение до расчёта пени | `debt` может быть отрицательным, `text` |
| `penalty_period` | Период начисления пени | `debt`, `period` [start, end, days], `penalty_period_info` [ставка, коэфф.], `penalty`, `formulae` |
| `field` | Итого за месяц | `text` («Итого:»), `penalty` |
| `debt_info` | Сводка долга внутри месяца | `accrual_debt`, `correcting_debt` |

Суммы в строках — **строки** с русским форматированием. В `penalty_period` поле `period`: третий элемент — **число дней** (integer).

---

## 8.8. `path_to_save` у генерации

В `create_calculating_table_input.json` и `create_doc_input.json` дублируется **`path_to_save`** — каталог вывода DOCX (как в `parse_output`).

---

## 8.9. Даты и деньги (вывод по эталонам)

| Контекст | Формат |
|----------|--------|
| `parse_input.date`, `claim_data.current_date` | `YYYY-MM-DD` |
| Сроки в таблице пени, претензии | `DD.MM.YYYY` |
| Периоды в текстовых полях | «`DD.MM.YYYY` по …», «`MM.YYYY-MM.YYYY`» |
| Суммы в `parsed_info` / месячных блоках | **number** |
| Суммы в `claim_data`, `calculator_list` | **string** с пробелами и **`,`** как десятичным разделителем |
| Валюта / `currency` | **не кодируется** — рубли по смыслу ТЗ |

Поля **суммы прописью** в JSON **нет**.

---

## 8.10. Вопросы, не закрытые эталонными JSON

- **Версионирование схем** (`schemaVersion`) — в файлах отсутствует.
- **Nullable vs отсутствие поля** — в эталоне используются **`null`** (напр. в `period`, `penalty_period_info`, `text`) и **опускание** `plaintiff_info` на промежуточном шаге; единый контракт для API нужно зафиксировать в OpenAPI.
- **Пагинация списка пакетов** — вне эталонов (БД не используется, см. архитектурное дополнение).
- **Слияние `extracted` → форма** — в JSON показан **результат** после расчёта (`claim_data`), а не промежуточная модель «по документам»; конфликты полей описываются в **Q-3.1.6** дополнения по входным данным.

---

## Источник истины

При расхождении текста этого дополнения с кодом приоритет у **фактической сериализации** в [`LegalDocInspectorV2/jsons/`](./jsons/) и реализации в `legal_doc_inspector` (парсер, `penalty_calculator`, `doc_creator`).
