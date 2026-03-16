# Описание модулей LegalDocInspector

Документ описывает структуру проекта, назначение каждого модуля и основные функции/классы.

---

## Точки входа

| Файл | Назначение |
|------|------------|
| **`run.py`** | Запуск Flask-бэкенда на порту 5001. Создаёт приложение через `create_app()` из `LegalDocInspector.backend`. |
| **`LegalDocInspector/streamlit/interface.py`** | Streamlit-интерфейс. Запуск: `streamlit run streamlit/interface.py`. |

---

## Backend (API) — `LegalDocInspector/backend/`

### `__init__.py`
- **`create_app()`** — создаёт Flask-приложение, загружает YAML-конфиг из `configs/debug_config.yaml`, регистрирует маршруты. В `g` перед каждым запросом поднимаются: `config`, `table_parser`, `claim_generator`, `calc_claim_generator`, `contract_parser`, `claim_parser`.

### `routes.py`
- **`home()`** — маршрут `/`, проверка работы сервера.
- **`parse()`** — POST `/parse`: приём комплекта документов (договор PDF, претензия PDF, Excel-справки), парсинг через `TableParser`, `PDFContractParser`, `PDFClaimParser`, получение данных ответчика по ИНН; сохранение результата в JSON и возврат.
- **`calc_penalty()`** — POST `/calculate_penalty`: расчёт пеней по результатам парсинга, вызов `calculate_penalty()` и `convert_data()`, возврат `claim_data` и `calculator_list`.
- **`create_doc()`** — POST `/create_doc`: генерация искового заявления (DOCX) по шаблону через `ClaimGenerator`.
- **`create_table()`** — POST `/create_calculating_table`: генерация расчёта к иску (DOCX) через `CalculationClaimGenerator`.
- **`get_request_files()`** — разбор загруженных файлов по ключам и сохранение в папку; поддержка ZIP-архивов.
- **`find_parent_dir_with_name()`** — поиск родительской директории по имени.
- **`safe_decode_filename()`, `safe_decode_filename_linux()`** — декодирование имён файлов из архивов (Windows/Linux кодировки).
- **`sort_data_structure()`** — сортировка структуры данных калькулятора: `start_of_table`, месяцы по порядку, `end_of_table1`, `end_of_table2`, `debt_info`, `contract_number`.

### `llm_functions.py` (опционально, в routes закомментировано)
- **`extract_first_10_digits(text)`** — извлечение первых 10 цифр из строки (ИНН).
- **`parse_contract(file)`** — парсинг договора через LLM (Qwen): тип услуги, срок оплаты, номер договора.
- **`parse_claim(file)`** — парсинг претензии через LLM: ИНН истца, дата и номер претензии.
- Классы **`ContractParser`**, **`ClaimParser`** из `pdf_parser` используются с LLM-моделью и процессором.

---

## Конфигурация — `configs/`

### `config.py`
- **`AppConfig`** — dataclass: `claim_template_path`, `calculation_claim_template_path`, `save_data_folder`, `debug_mode`.
- **`load_yaml_config(filename)`** — загрузка конфига из YAML, возврат `AppConfig`.
- **`save_yaml_config(filename, config)`** — сохранение конфига в YAML.

---

## Ядро приложения — `LegalDocInspector/legal_doc_inspector/`

### `exel_parser.py` — парсинг Excel-справок о задолженности

**Класс `ExcelReader`**
- **`open(filename)`** — открыть Excel только на чтение (pandas).
- **`close()`** — закрыть документ.
- **`cell(row, column)`** — значение ячейки.
- **`last_valid_cell_index(column)`** — индекс последней непустой ячейки в столбце.

**Класс `TableParser`**
- **`open(filename)`** / **`close()`** — открыть/закрыть файл через `ExcelReader`.
- **`parse()`** — разбор листа: блоки по месяцам, начисления (accruals), платежи (payments), доборы (additionals), корректировки (adjustment), долг по периоду; возврат словаря период → структура (accrual/adjustment, debt, totals).
- **`parse_defendant_inn()`** — ИНН ответчика из фиксированной ячейки.
- **`parse_contract_number()`** — номер и дата договора из ячеек.
- **`row_type(row)`** — тип строки (начало блока месяца, корректировка, конец, начисление, платёж, долг, итоги и т.д.).
- **`find_month()`, `transform_month_to_another_form()`** — определение месяца (именительный/предложный падеж).
- **`parse_period()`, `parse_accrual()`, `parse_payment_date()`, `parse_payment_amount()`, `parse_debt()`** — извлечение полей из строки.
- **`is_additional()`, `check_if_is_correcting()`** — проверка добора и годовой корректировки.
- **`add_period_if_is_new()`, `block_type()`** — управление структурой периодов.

---

### `pdf_parser/` — парсинг PDF (договоры и претензии)

#### `parser_models.py` (основной API для backend)

**Класс `PDFClaimParser`**
- **`_parse_claim_text(path)`** — конвертация PDF в Docling-документ.
- **`_extract_text_with_page(data)`** — извлечение текста по страницам из экспорта Docling.
- **`analyse_claim(path)`** — полный разбор претензии: номер и дата претензии по страницам, возврат списка `{"claim_date", "claim_number"}`.
- **`_parse_claim_number_and_date(texts_with_pages)`** — поиск номера (6 цифр) и даты (ДД.ММ.ГГГГ) в тексте.
- **`_standartize_claims()`** — приведение к единому формату словарей.

**Класс `PDFContractParser`**
- **`_parse_contract_text(path)`** — конвертация PDF в Docling (первые 30 страниц).
- **`analyse_contract(path)`** — возврат `(overdue_date_fragment, service_type_fragment)`.
- **`_find_point_of_overdue_date(html)`** — фрагмент о сроке оплаты по ключевым словам (срок, оплата, число, месяц и т.д.).
- **`_find_point_of_service_type(html)`** — фрагмент о типе услуги (теплоноситель, вода).
- **`_find_top5_elements_weighted(html, keyword_weights, exclude_words)`** — взвешенный поиск по ключевым словам в HTML (лемматизация через pymorphy2), топ-5 элементов.
- **`_lemmatize_words()`, `_lemmatize_word()`, `_strip_html()`** — вспомогательные для текста/HTML.

#### `contract_parser.py` (LLM-вариант)
- **`ContractParser(llm_model, processor)`** — парсинг договора через OCR (Tesseract) + эмбеддинги (SentenceTransformer) + RAG + LLM.
- **`pdf_to_text(pdf_path)`** — PDF → изображения → OCR → разбиение по пунктам.
- **`find_info(chunks, question, service_flag)`** — поиск релевантных фрагментов и ответ LLM на вопрос.

#### `claim_parser.py` (LLM-вариант)
- **`ClaimParser(model, processor)`** — парсинг претензии через OCR + LLM.
- **`pdf_to_text(pdf_path)`** — извлечение текста по страницам (первая страница по зонам).
- **`find_info(pdf_text)`** — запрос к модели: ИНН истца, дата и номер претензии.

#### `utils.py`
- **`split_by_points(text)`** — разбиение текста по пунктам (для договора).
- **`retrieve_relevant_chunks(question_embedding, chunk_embeddings, chunks, top_k)`** — RAG: топ-k фрагментов по косинусной близости.
- **`get_conversation_for_contract(chunks, question)`** — формирование диалога для LLM (договор).
- **`get_conversation_for_claim(pdf_text)`** — диалог для парсинга претензии.
- **`get_text_for_zip()`, `get_pdf_files()`, `get_conversation_for_zip()`** — работа с ZIP и примерами названий документов.
- **`calculate_state_duty(amount_str)`** — расчёт госпошлины по сумме (ступенчатая шкала НК РФ); форматирование в строку с пробелами и копейками.

---

### `calculator/penalty_calculator.py` — расчёт пеней

- **`StrictFormattedMoney`** — класс для денежных сумм (Decimal, формат с разделителями, арифметика, сравнения).
- **`sort_dict_by_months(data_dict)`** — сортировка словаря по ключам «Месяц ГГГГ».
- **`_add_last_day_of_month(date_str)`**, **`_add_last_day_of_next_month(date_str)`** — последний день месяца в формате ДД.ММ.ГГГГ.
- **`_get_start_date(day)`** — первый рабочий день после даты (через isdayoff.ru).
- **`_is_holiday(day)`** — проверка выходного/праздника.
- **`_get_penalty_periods(start_date, end_date, debt, type_of_split)`** — разбиение периода просрочки на этапы по типу организации: УК (60/30/+∞ дней), ТСЖ (30/60/+∞), Прочие (одна ставка 1/130).
- **`_calculate_penalty_for_each_period(periods)`** — расчёт пени по каждому подпериоду (ставка 9,5%, доли 1/300, 1/170, 1/130, 0), формулы и итоги.
- **`_split_stage_by_date()`**, **`_split_stage_by_date_correcting()`** — разбиение этапа по дате платежа/корректировки.
- **`_sort_all_payments()`**, **`_find_overdue_start()`** — сортировка платежей и определение начала просрочки по месяцу.
- **`_check_month_for_four_party()`**, **`_check_is_correcting_done()`**, **`_check_month_for_only_correcting_debt()`**, **`_check_month_for_only_accrual_additionals()`** — служебные проверки по типу начислений и корректировок.
- **`calculate_penalty(parsed_data, day_of_penalty, company_type, end_date)`** — основной вход: данные из Excel-парсера, день оплаты по договору, тип компании (УК/ТСЖ/Прочие), конечная дата; возврат структуры с месяцами, периодами пени, погашениями, корректировками и итогами (долг, пени).

---

### `doc_creator/` — генерация DOCX

#### `claim_generator.py` — исковое заявление

- **`ClaimGenerator`**
  - **`make_instance(config, template_filename, output_filename)`** — копирование шаблона, подстановка данных из `config`, сохранение.
  - **`fill_file()`** — подготовка данных, замена кавычек, заполнение таблиц и списков.
  - **`fill_first_table()`** — истец/ответчик (полное имя, ОГРН, ИНН, адрес).
  - **`fill_second_table()`**, **`fill_third_table()`** — таблицы по договорам (номер, период, задолженность, срок оплаты, пункт договора; неустойка, цена иска).
  - **`fill_first_list()`** — текст со списком разделов/пунктов договоров.
  - **`fill_second_list()`**, **`fill_third_list()`** — списки претензий и договоров с деталями.
  - **`fill_other_parts()`** — цена иска, госпошлина, тип договора, поставляемые ресурсы, шаблоны окончаний, значимый абзац (статьи ТЭ/ГВС).
  - **`prepare_data()`** — формирование `contract_types_templates` (ТЭ/ГВС/ТЭ+ГВС, единственное/множественное число, статьи закона).
  - **`get_paragraph_type_of(str_type)`** — выбор шаблона абзаца по типу компании и услуги (ТСЖ/УК/Прочие × ТЭ/ГВС).
  - **`fix_quotes()`**, **`normalize_quotes()`** — нормализация кавычек в названиях организаций.
  - **`borders()`** — обёртка плейсхолдера в `/*...*/`.
  - Вспомогательные: **`second_table_fill_*`**, **`third_table_fill_*`**, **`third_table_clone_row`**, **`third_table_merge_rows`**, **`parse_info_for_first_list()`**, **`create_text_for_first_list()`**.

#### `calculation_claim_generator.py` — расчёт к иску

- **`CalculationClaimGenerator`**
  - **`make_instance(config, config2, template_filename, output_filename)`** — конвертация данных калькулятора в формат таблиц, клонирование шаблона, заполнение расчёта и второй таблицы, сохранение.
  - **`convert_data_from_calculator(contracts)`** — преобразование вывода калькулятора в структуру по договорам и периодам (даты просрочки, суммы, строки по начислениям/ставкам/формулам/пеням).
  - **`fill_file()`** — заполнение блоков по каждому договору, очистка лишних таблиц.
  - **`fill_contract()`**, **`fill_period()`** — заполнение таблицы по договору и по периодам (заголовки и строки с числами).
  - **`fill_second_table()`** — сводная таблица по договорам (из `config2`).
  - **`fill_common_contract_info()`**, **`fill_common_period_info()`** — общие поля (номер договора, даты, суммы).
  - **`fill_row_type_1()`**, **`fill_row_type_2()`** — строки-заголовки и строки с формулами/пенями.
  - **`clone_block()`**, **`clone_row_type_1()`**, **`clone_row_type_2()`** — клонирование блоков и строк шаблона.
  - **`merge_row_*()`** — объединение ячеек в строках таблицы.
  - **`delete_table_and_next_paragraph()`**, **`clear_document_from_index()`** — удаление таблиц и следующего параграфа.
  - **`fill_other_parts()`** — цена иска, госпошлина, текущая дата.
  - **`type_of_row()`**, **`count_row_by_types()`** — определение типа строки (заголовок/числа).
  - **`_correct_table_height()`**, **`_correct_table_width()`**, **`set_exact_cell_dimensions()`** — размеры таблицы и ячеек.
  - **`borders()`** — плейсхолдеры `/*...*/`.

#### `docx_editor.py` — низкоуровневая работа с DOCX

- **`DocxRedactor`**
  - **`open(filename)`**, **`close()`**, **`save()`** — открытие/закрытие/сохранение документа.
  - **`clone_file(src, clone)`** — копирование файла-шаблона.
  - **`find_paragraph_contains_text()`**, **`find_paragraph_consists_of_text()`** — поиск параграфа по тексту.
  - **`replace_text_in_run()`**, **`replace_text_in_paragraph()`**, **`replace_text_in_document()`**, **`replace_text_in_table_cell()`** — замена текста с сохранением форматирования где нужно.
  - **`insert_paragraph()`**, **`clone_paragraph()`**, **`delete_paragraph()`** — вставка/клонирование/удаление параграфа.
  - **`copy_paragraph_styles()`**, **`copy_run_styles()`** — копирование стилей параграфа и run.
  - **`insert_row_in_table()`**, **`clone_table_row()`**, **`delete_row_in_table()`** — строки таблицы.
  - **`get_table()`**, **`get_paragraph()`** — доступ по индексу.
  - **`merge_table_cells()`** — объединение ячеек.
  - **`copy_cell_properties()`**, **`set_border_to_cell()`**, **`set_vertical_alignment_to_cell()`** — свойства ячеек.
  - **`insert_paragraph_after_table()`**, **`insert_paragraph_after_paragraph()`**, **`insert_table_after_table()`** — вставка элементов после таблицы/параграфа.
  - **`paragraph_text_set_bold()`**, **`run_text_set_bold()`** — жирный шрифт.
  - **`print_table()`** — отладочный вывод таблицы.

---

### `utils/` — вспомогательные модули

#### `calculator_adapter.py`
- **`convert_data(calculated_data_list, last_days_of_penalty, contract_points, company_type, current_date)`** — преобразование списка результатов калькулятора в структуру для генераторов: `contracts_info`, `table_info` (в т.ч. периоды, долги, пени, пункты договора, даты), `company_type`, `current_date`, цена иска (без госпошлины и шаблонов типов договора — их дополняет ClaimGenerator).
- **`group_consecutive_months(dates_list)`** — группировка списка дат ММ.ГГГГ в диапазоны (например, 01.2024, 02.2024 → «01.2024-02.2024»).

#### `parse_info_by_inn.py`
- **`parse_html(inn)`** — запрос к egrul.itsoft.ru по ИНН, парсинг HTML: полное и краткое наименование, адрес, КПП, ОГРН.
- **`replace_quotes(text)`** — замена кавычек на « ».
- **`clean_address(text)`** — нормализация адреса (лишние запятые и пробелы).

#### `calculate_tax.py`
- **`calculate_state_duty(amount_input)`** — расчёт госпошлины по сумме иска (строка или `StrictFormattedMoney`), ступенчатая шкала НК РФ, округление до целого рубля; возврат отформатированной строки.

#### `table_clone.py`
- **`get_cell_tcW()`**, **`get_cell_shading()`**, **`get_cell_borders()`** — чтение свойств ячейки (ширина, заливка, границы).
- **`parse_table_full_structure(table)`** — извлечение полной структуры таблицы (строки, ячейки, текст, gridSpan, vMerge, размеры, заливки, границы).
- **`apply_cell_formatting(cell, info)`** — применение ширины, заливки и границ к ячейке.
- **`clone_table_full(document, structure)`** — создание таблицы по сохранённой структуре с копированием стилей.
- **`copy_paragraph_formatting()`**, **`copy_run_formatting()`**, **`copy_cell_text_with_styles()`** — копирование форматирования и текста.
- **`clone_table_from_table(document, table)`** — полная копия таблицы (структура, стили, текст) без автоматической вставки в документ.

#### `strict_formatted_money.py`
- **`StrictFormattedMoney`** — дубликат класса из penalty_calculator для использования в utils: сумма в рублях с двумя знаками, форматирование с разделителями тысяч и запятой, арифметика и сравнения.

#### `convert_month.py`
- **`convert_month(month)`** — русское название месяца → «01»–«12».
- **`last_day_of_month(month)`** — для строки ММ.ГГГГ возвращает последний день месяца в формате ДД.ММ.ГГГГ.

---

## Streamlit — `LegalDocInspector/streamlit/interface.py`

- Управление состоянием: **`form_data`**, **`complects`** (загруженные файлы, данные парсинга, флаги).
- **`get_documents_complect_form()`** — форма набора: загрузка договора, претензии, Excel-справок.
- **`get_contract_form()`** — отображение и редактирование данных по договору (срок оплаты, тип услуги, день оплаты).
- Дальнейшая логика: вызовы backend (`/parse`, `/calculate_penalty`, `/create_doc`, `/create_calculating_table`), отображение результатов и скачивание DOCX.

---

## Данные и шаблоны

- **`data/`** — каталог из конфига `save_data_folder`: подпапки запросов, `result_parser.json`, сгенерированные DOCX; подпапки `templates/`, `input_examples/`.
- **`configs/debug_config.yaml`** — пути к папке сохранения, шаблонам искового заявления и расчёта, флаг `debug`.

---

## Скрипты и тесты

- **`scripts/example_file_uploading.py`** — пример загрузки файлов и вызова API.
- **`scripts/eval_pdf_parser.py`**, **`scripts/eval.py`** — оценка парсеров и пайплайна.
- **`test/`** — тесты калькулятора, госпошлины, парсеров, генераторов документов.
- **`experiments/`** — прототипы и эксперименты (не входят в основной код).

---

## Краткий поток данных

1. Пользователь загружает комплект: договор PDF, претензия PDF, Excel-справки.
2. **`/parse`**: TableParser → долги по месяцам; PDFContractParser → срок оплаты и тип услуги; PDFClaimParser → даты и номера претензий; по ИНН ответчика → реквизиты организации. Всё сохраняется в JSON.
3. **`/calculate_penalty`**: по JSON и параметрам (тип компании, конечная дата, день оплаты) вызывается **`calculate_penalty()`**, затем **`convert_data()`** → данные для искового заявления и расчёта.
4. **`/create_doc`**: **ClaimGenerator** заполняет шаблон иска по `claim_data`.
5. **`/create_calculating_table`**: **CalculationClaimGenerator** заполняет шаблон расчёта по `calculator_list` и `claim_data`.

Госпошлина считается в **`calculate_tax.calculate_state_duty()`** (и при необходимости в **`pdf_parser.utils.calculate_state_duty()`** для старого формата строки).
