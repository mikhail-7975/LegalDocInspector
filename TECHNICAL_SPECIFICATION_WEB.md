# Техническое задание на разработку веб-интерфейса для системы автоматизации подготовки исковых заявлений
## (Версия на HTML/CSS/JavaScript с Flask бэкендом)

## 1. Общие сведения

### 1.1. Наименование проекта
**LegalDocInspector Web** - веб-интерфейс для автоматизации обработки юридических документов и генерации исковых заявлений

### 1.2. Назначение системы
Веб-интерфейс предназначен для автоматизации процесса подготовки исковых заявлений в арбитражный суд на основе загруженных документов (договоров, претензий, справок о задолженности) с использованием технологий машинного обучения и обработки естественного языка.

### 1.3. Цели разработки
- Автоматизация процесса обработки юридических документов
- Ускорение подготовки исковых заявлений
- Минимизация ошибок при заполнении документов
- Упрощение работы с множественными наборами документов
- Создание современного, отзывчивого веб-интерфейса без использования Streamlit

---

## 2. Технические требования

### 2.1. Технологический стек

#### Frontend:
- **HTML5** - структура страницы
- **CSS3** - стилизация и адаптивный дизайн
- **JavaScript (ES6+)** - клиентская логика и интерактивность
- **Fetch API** - взаимодействие с бэкендом
- **LocalStorage/SessionStorage** - хранение состояния на клиенте

#### Backend (Flask):
- **Python 3.11+**
- **Flask** - веб-фреймворк для API endpoints
- **Flask-CORS** - поддержка CORS для фронтенда
- **requests** - взаимодействие с основным бэкенд-сервером
- **python-docx** - работа с документами (если требуется)

#### Интеграция:
- **Основной бэкенд-сервер**: `http://localhost:5001`
- **Эндпоинты основного сервера**:
  - `POST /parse` - парсинг документов
  - `POST /calculate_penalty` - расчёт пени
  - `POST /create_doc` - создание иска
  - `POST /create_calculating_table` - создание расчёта к иску

### 2.2. Архитектура приложения

```
LegalDocInspector/
├── web_frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   ├── js/
│   │   │   └── app.js
│   │   └── images/
│   ├── templates/
│   │   └── index.html
│   └── app.py (Flask приложение)
├── LegalDocInspector/
│   └── ... (существующий код)
└── requirements.txt
```

### 2.3. Flask API Endpoints

Flask приложение должно предоставлять следующие endpoints:

- `GET /` - главная страница (отдача HTML)
- `GET /api/parse-inn/<inn>` - получение данных по ИНН
- `POST /api/calculate-duty` - расчёт госпошлины
- `POST /api/proxy/parse` - проксирование запроса к основному серверу для парсинга
- `POST /api/proxy/calculate-penalty` - проксирование запроса для расчёта пени
- `POST /api/proxy/create-doc` - проксирование запроса для создания иска
- `POST /api/proxy/create-calculating-table` - проксирование запроса для создания расчёта

---

## 3. Структура HTML страницы

### 3.1. Основная структура

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LegalDocInspector - Загрузка и обработка документов</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body>
    <div class="container">
        <!-- Заголовок -->
        <!-- Этап 1: Загрузка документов -->
        <!-- Этап 2: Обработка (скрыт по умолчанию) -->
        <!-- Этап 3: Заполнение данных (скрыт по умолчанию) -->
        <!-- Этап 4: Проверка данных (скрыт по умолчанию) -->
        <!-- Этап 5: Скачивание документов (скрыт по умолчанию) -->
    </div>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>
```

### 3.2. Секции страницы

#### 3.2.1. Заголовок
```html
<header class="page-header">
    <h1>Загрузка и обработка документов (Нейросети включены)</h1>
</header>
```

#### 3.2.2. Этап 1: Загрузка документов
- Общие параметры (дата, тип компании)
- Динамические наборы документов
- Кнопки управления наборами

#### 3.2.3. Этап 2: Обработка
- Индикатор прогресса
- Сообщения о статусе обработки

#### 3.2.4. Этап 3: Заполнение данных
- Формы для суда, истца, ответчика
- Формы для договоров
- Кнопка расчёта пени

#### 3.2.5. Этап 4: Проверка данных
- Форма данных об иске
- Кнопка генерации документов

#### 3.2.6. Этап 5: Скачивание
- Кнопки скачивания готовых документов

---

## 4. Управление состоянием приложения

### 4.1. Хранение состояния

Использовать JavaScript объект `appState` для хранения состояния:

```javascript
const appState = {
    formData: {
        courtInfo: {},
        plaintiffInfo: {},
        defendantInfo: {},
        lawsuitInfo: {},
        result: null,
        result2: null,
        flags: {
            step1Complete: false,
            step2Complete: false,
            step3Complete: false,
            formsChanged: false
        },
        numComplects: 1,
        companyType: 'Прочие',
        endDate: null
    },
    complects: {},
    contracts: {}
};
```

### 4.2. Сохранение в LocalStorage

Реализовать функции:
- `saveState()` - сохранение состояния в LocalStorage
- `loadState()` - загрузка состояния из LocalStorage
- `clearState()` - очистка состояния

### 4.3. Обработчик изменений

Реализовать функцию `onFormChange()`:
```javascript
function onFormChange() {
    appState.formData.flags.formsChanged = true;
    saveState();
}
```

---

## 5. Функциональные требования

### 5.1. Этап 1: Загрузка документов

#### 5.1.1. Общие параметры

**HTML структура:**
```html
<div class="form-row">
    <div class="form-group">
        <label for="end-date">Выберите дату конца просрочки</label>
        <input type="date" id="end-date" class="form-control" 
               onchange="handleDateChange(event)">
    </div>
    <div class="form-group">
        <label for="company-type">Выберите тип компании</label>
        <select id="company-type" class="form-control" 
                onchange="handleCompanyTypeChange(event)">
            <option value="Прочие">Прочие</option>
            <option value="УК">УК</option>
            <option value="ТСЖ">ТСЖ</option>
        </select>
    </div>
</div>
```

**JavaScript функции:**
- `handleDateChange(event)` - обработка изменения даты
- `handleCompanyTypeChange(event)` - обработка изменения типа компании
- Форматирование даты в формат `DD.MM.YYYY` для отображения

#### 5.1.2. Форма загрузки документов для набора

**HTML структура:**
```html
<div class="complect-container" data-complect-id="1">
    <h3>Набор <span class="complect-number">1</span></h3>
    
    <div class="file-upload-group">
        <label>Поле для договора</label>
        <input type="file" 
               class="file-input" 
               data-file-type="contract"
               accept=".pdf,.doc,.docx"
               onchange="handleFileUpload(event, this.dataset.complectId, 'contract')">
        <div class="file-name-display"></div>
    </div>
    
    <div class="file-upload-group">
        <label>Поле для претензии</label>
        <input type="file" 
               class="file-input" 
               data-file-type="claim"
               accept=".pdf,.doc,.docx"
               onchange="handleFileUpload(event, this.dataset.complectId, 'claim')">
        <div class="file-name-display"></div>
    </div>
    
    <div class="file-upload-group">
        <label>Поле для Excel справки о задолженности</label>
        <input type="file" 
               class="file-input" 
               data-file-type="debt-certificate"
               accept=".xls,.xlsx,.xlsm"
               multiple
               onchange="handleFileUpload(event, this.dataset.complectId, 'debt-certificate')">
        <div class="file-name-display"></div>
    </div>
</div>
```

**JavaScript функции:**
- `handleFileUpload(event, complectId, fileType)` - обработка загрузки файлов
- `validateComplect(complectId)` - валидация набора документов
- `updateFileDisplay(input, displayElement)` - отображение имён загруженных файлов

#### 5.1.3. Управление наборами документов

**HTML структура:**
```html
<div class="complect-controls">
    <button class="btn btn-primary" onclick="addComplect()">
        ➕ Добавить набор документов
    </button>
    <button class="btn btn-danger" onclick="removeComplect()">
        ➖ Убрать набор документов
    </button>
</div>
```

**JavaScript функции:**
- `addComplect()` - добавление нового набора
- `removeComplect()` - удаление последнего набора
- `renderComplects()` - отрисовка всех наборов
- `createComplectHTML(complectId)` - создание HTML для набора

#### 5.1.4. Валидация и отправка

**HTML структура:**
```html
<button id="submit-btn" 
        class="btn btn-success" 
        onclick="submitDocuments()"
        disabled>
    Отправить на сервер
</button>
```

**JavaScript функции:**
- `validateAllComplects()` - проверка всех наборов
- `updateSubmitButton()` - обновление состояния кнопки отправки
- `submitDocuments()` - отправка документов на сервер

**Логика отправки:**
```javascript
async function submitDocuments() {
    const formData = new FormData();
    
    // Добавление даты
    const endDate = document.getElementById('end-date').value;
    formData.append('date', endDate);
    
    // Добавление файлов для каждого набора
    for (const [complectId, complect] of Object.entries(appState.complects)) {
        if (complect.contract) {
            formData.append(`complect_${complectId}_contract_file`, 
                          complect.contract, complect.contract.name);
        }
        if (complect.claim) {
            formData.append(`complect_${complectId}_claim_file`, 
                          complect.claim, complect.claim.name);
        }
        if (complect.debtCertificates && complect.debtCertificates.length > 0) {
            complect.debtCertificates.forEach((file, index) => {
                formData.append(`complect_${complectId}_certificate_file_${index}`, 
                              file, file.name);
            });
            formData.append(`${complectId}_certificates_count`, 
                          complect.debtCertificates.length.toString());
        }
    }
    
    formData.append('complects_count', 
                   Object.keys(appState.complects).length.toString());
    
    // Показать спиннер
    showSpinner('Ваш запрос обрабатывается, пожалуйста, подождите, обработка одного набора занимает в среднем 2 минуты');
    
    try {
        const response = await fetch('/api/proxy/parse', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            appState.formData.result = result;
            appState.formData.pathToSave = result.path_to_save;
            appState.formData.flags.step1Complete = true;
            showStep2();
        } else {
            showError(`Ошибка: ${response.status}`, await response.text());
        }
    } catch (error) {
        showError('Ошибка при отправке запроса', error.message);
    } finally {
        hideSpinner();
    }
}
```

---

### 5.2. Этап 2: Обработка результатов

#### 5.2.1. Отображение результатов

**HTML структура:**
```html
<div id="step2" class="step-container" style="display: none;">
    <div class="success-message">
        <h2>✅ Файл успешно обработан!</h2>
        <p>Результат обработки документов</p>
    </div>
    
    <div class="info-section">
        <h3>Заполнение информации для генерации иска</h3>
        <p class="warning">Пожалуйста, внимательно проверьте все пункты!</p>
    </div>
</div>
```

**JavaScript функции:**
- `showStep2()` - отображение второго этапа
- `initializeContracts()` - инициализация данных о договорах из результатов

---

### 5.3. Этап 3: Заполнение данных для иска

#### 5.3.1. Данные о суде

**HTML структура:**
```html
<div class="form-section">
    <h3>Данные о месте проведения</h3>
    <div class="form-group">
        <label for="court-name">Название Органа</label>
        <input type="text" 
               id="court-name" 
               class="form-control"
               value="Арбитражный суд города Москвы"
               onchange="onFormChange()">
    </div>
    <div class="form-group">
        <label for="court-address">Адрес Органа</label>
        <input type="text" 
               id="court-address" 
               class="form-control"
               value="115225, г. Москва, ул. Большая Тульская, д. 17"
               onchange="onFormChange()">
    </div>
</div>
```

#### 5.3.2. Данные об истце

**HTML структура:**
```html
<div class="form-section">
    <h3>Данные об Истце</h3>
    <div class="form-group">
        <label for="plaintiff-inn">ИНН Истца</label>
        <input type="text" 
               id="plaintiff-inn" 
               class="form-control"
               value="7720518494"
               onchange="handlePlaintiffINNChange(event)">
    </div>
    
    <div id="plaintiff-fields">
        <div class="form-group">
            <label for="plaintiff-full-name">Название Истца</label>
            <input type="text" 
                   id="plaintiff-full-name" 
                   class="form-control"
                   onchange="onFormChange()">
        </div>
        <!-- Остальные поля истца -->
    </div>
    
    <button class="btn btn-secondary" onclick="updatePlaintiffData()">
        Обновить данные об истце
    </button>
</div>
```

**JavaScript функции:**
- `handlePlaintiffINNChange(event)` - обработка изменения ИНН
- `fetchPlaintiffData(inn)` - запрос данных по ИНН через Flask API
- `updatePlaintiffData()` - обновление данных об истце
- `populatePlaintiffFields(data)` - заполнение полей данными

**Интеграция с Flask:**
```javascript
async function fetchPlaintiffData(inn) {
    try {
        const response = await fetch(`/api/parse-inn/${inn}`);
        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            throw new Error('Не удалось получить данные по ИНН');
        }
    } catch (error) {
        showError('Ошибка', error.message);
        return null;
    }
}
```

#### 5.3.3. Данные об ответчике

**HTML структура:**
```html
<div class="form-section">
    <h3>Данные об ответчике</h3>
    <div class="form-group">
        <label for="defendant-full-name">Название ответчика</label>
        <input type="text" 
               id="defendant-full-name" 
               class="form-control"
               onchange="onFormChange()">
    </div>
    <!-- Остальные поля ответчика -->
</div>
```

**JavaScript функции:**
- `populateDefendantFields(result)` - заполнение полей из результатов парсинга

#### 5.3.4. Форма для договоров

**HTML структура:**
```html
<div class="form-section">
    <h3>Данные о договорах</h3>
    <div id="contracts-container">
        <!-- Динамически генерируемые формы для каждого договора -->
    </div>
</div>
```

**JavaScript функции:**
- `renderContracts()` - отрисовка форм для всех договоров
- `createContractFormHTML(contractNumber, contractData)` - создание HTML формы для договора

**Пример формы договора:**
```html
<div class="contract-form" data-contract-number="04.303360-ТЭ">
    <h4>Информация из договора 04.303360-ТЭ</h4>
    <div class="info-display">
        <p><strong>Информация по дню начала просрочки:</strong></p>
        <p class="info-text">...</p>
    </div>
    <div class="form-row">
        <div class="form-group">
            <label>Выберите число месяца, которое является последним днём оплаты счёта</label>
            <input type="number" 
                   class="form-control"
                   min="1" 
                   max="31" 
                   value="18"
                   onchange="onFormChange()">
        </div>
        <div class="form-group">
            <label>Напишите номер пункта договора, в котором говорится о дне начала просрочки</label>
            <input type="text" 
                   class="form-control"
                   value="5.5"
                   onchange="onFormChange()">
        </div>
    </div>
</div>
```

#### 5.3.5. Расчёт пени

**HTML структура:**
```html
<button class="btn btn-primary" onclick="calculatePenalty()">
    Произвести расчёты по загруженным наборам документов
</button>
```

**JavaScript функции:**
- `calculatePenalty()` - отправка запроса на расчёт пени
- `preparePenaltyRequest()` - подготовка данных для запроса

```javascript
async function calculatePenalty() {
    const requestData = {
        company_type: appState.formData.companyType,
        end_date: appState.formData.endDate,
        parsing_results: []
    };
    
    // Сбор данных о договорах
    for (const contractInfo of appState.formData.result.table_parser_result) {
        const contractNumber = contractInfo[1];
        const contract = appState.contracts[contractNumber];
        
        requestData.parsing_results.push({
            parsed_info: contractInfo[0],
            contract_point: contract.contractPoint,
            day_of_penalty: contract.dayOfPenalty,
            contract_number: contractNumber
        });
    }
    
    showSpinner('Ваш запрос обрабатывается, пожалуйста, подождите');
    
    try {
        const response = await fetch('/api/proxy/calculate-penalty', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (response.ok) {
            const result = await response.json();
            appState.formData.result2 = result;
            appState.formData.flags.step2Complete = true;
            showStep3();
        } else {
            showError(`Ошибка: ${response.status}`, await response.text());
        }
    } catch (error) {
        showError('Ошибка при расчёте пени', error.message);
    } finally {
        hideSpinner();
    }
}
```

---

### 5.4. Этап 4: Проверка данных иска

#### 5.4.1. Данные об иске

**HTML структура:**
```html
<div id="step3" class="step-container" style="display: none;">
    <div class="success-message">
        <h2>✅ Расчёты успешно произведены!</h2>
    </div>
    
    <div class="form-section">
        <h3>Проверьте данные об иске</h3>
        <div class="form-group">
            <label for="lawsuit-cost">Цена иска</label>
            <input type="text" 
                   id="lawsuit-cost" 
                   class="form-control"
                   onchange="onFormChange()">
        </div>
        <div class="form-group">
            <label for="lawsuit-tax">Госпошлина</label>
            <input type="text" 
                   id="lawsuit-tax" 
                   class="form-control"
                   onchange="onFormChange()">
        </div>
        <div class="form-group">
            <label for="lawsuit-service-type">Выберите вид услуги</label>
            <select id="lawsuit-service-type" class="form-control" onchange="onFormChange()">
                <option value="ГВС + ТЭ">ГВС + ТЭ</option>
                <option value="ТЭ">ТЭ</option>
                <option value="ГВС">ГВС</option>
            </select>
        </div>
        
        <div id="claims-container">
            <!-- Динамически генерируемые поля для претензий -->
        </div>
    </div>
    
    <button class="btn btn-success" onclick="generateDocuments()">
        Нажмите, чтобы подтвердить правильность данных
    </button>
</div>
```

**JavaScript функции:**
- `showStep3()` - отображение третьего этапа
- `populateLawsuitFields()` - заполнение полей данными из расчётов
- `calculateDuty(cost)` - расчёт госпошлины через Flask API
- `renderClaims()` - отрисовка полей для претензий
- `generateDocuments()` - генерация документов

**Расчёт госпошлины:**
```javascript
async function calculateDuty(cost) {
    try {
        const response = await fetch('/api/calculate-duty', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ cost: cost })
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.duty;
        }
    } catch (error) {
        console.error('Ошибка расчёта госпошлины:', error);
    }
    return '';
}
```

**Генерация документов:**
```javascript
async function generateDocuments() {
    const docCreatorData = {
        claim_data: {
            ...appState.formData.result2.claim_data,
            plaintiff_info: appState.formData.plaintiffInfo,
            defendant_info: appState.formData.defendantInfo,
            lawsuit_info: appState.formData.lawsuitInfo
        },
        calculator_list: appState.formData.result2.calculator_list,
        path_to_save: appState.formData.pathToSave
    };
    
    appState.formData.flags.formsChanged = false;
    saveState();
    
    showSpinner('Создание документов...');
    
    try {
        // Создание иска
        const lawsuitResponse = await fetch('/api/proxy/create-doc', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(docCreatorData)
        });
        
        if (!lawsuitResponse.ok) {
            throw new Error(`Ошибка создания иска: ${lawsuitResponse.status}`);
        }
        
        const lawsuitBlob = await lawsuitResponse.blob();
        appState.formData.lawsuitBlob = lawsuitBlob;
        
        // Создание расчёта
        const tableResponse = await fetch('/api/proxy/create-calculating-table', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(docCreatorData)
        });
        
        if (!tableResponse.ok) {
            throw new Error(`Ошибка создания расчёта: ${tableResponse.status}`);
        }
        
        const tableBlob = await tableResponse.blob();
        appState.formData.lawsuitTableBlob = tableBlob;
        
        appState.formData.flags.step3Complete = true;
        showStep4();
        
    } catch (error) {
        showError('Ошибка при создании документов', error.message);
    } finally {
        hideSpinner();
    }
}
```

---

### 5.5. Этап 5: Скачивание документов

#### 5.5.1. Кнопки скачивания

**HTML структура:**
```html
<div id="step4" class="step-container" style="display: none;">
    <div class="download-section">
        <h3>Документы готовы к скачиванию</h3>
        <div class="download-buttons">
            <a id="download-lawsuit" 
               class="btn btn-primary" 
               download="Иск.docx">
                Скачать иск
            </a>
            <a id="download-calculation" 
               class="btn btn-primary" 
               download="Расчёт к иску.docx">
                Скачать расчёт к иску
            </a>
        </div>
    </div>
</div>
```

**JavaScript функции:**
- `showStep4()` - отображение четвёртого этапа
- `setupDownloadLinks()` - настройка ссылок для скачивания

```javascript
function setupDownloadLinks() {
    if (appState.formData.lawsuitBlob) {
        const url = URL.createObjectURL(appState.formData.lawsuitBlob);
        document.getElementById('download-lawsuit').href = url;
    }
    
    if (appState.formData.lawsuitTableBlob) {
        const url = URL.createObjectURL(appState.formData.lawsuitTableBlob);
        document.getElementById('download-calculation').href = url;
    }
}
```

---

## 6. CSS требования

### 6.1. Общие стили

- Современный, чистый дизайн
- Адаптивная вёрстка (mobile-first подход)
- Использование CSS Grid и Flexbox
- Цветовая схема: профессиональная, юридическая тематика
- Типографика: читаемые шрифты, правильные размеры

### 6.2. Компоненты

#### Контейнеры:
- `.container` - основной контейнер страницы
- `.step-container` - контейнер для каждого этапа
- `.form-section` - секция формы
- `.complect-container` - контейнер набора документов

#### Формы:
- `.form-group` - группа полей формы
- `.form-control` - поля ввода
- `.form-row` - строка с несколькими полями

#### Кнопки:
- `.btn` - базовая кнопка
- `.btn-primary` - основная кнопка
- `.btn-success` - кнопка успеха
- `.btn-danger` - кнопка удаления
- `.btn-secondary` - вторичная кнопка

#### Сообщения:
- `.success-message` - сообщение об успехе
- `.error-message` - сообщение об ошибке
- `.warning` - предупреждение
- `.info-message` - информационное сообщение

#### Индикаторы:
- `.spinner` - индикатор загрузки
- `.progress-bar` - прогресс-бар

### 6.3. Адаптивность

- Breakpoints:
  - Mobile: до 768px
  - Tablet: 768px - 1024px
  - Desktop: от 1024px

---

## 7. JavaScript архитектура

### 7.1. Структура кода

```javascript
// app.js

// Глобальное состояние
const appState = { ... };

// Утилиты
const utils = {
    saveState: function() { ... },
    loadState: function() { ... },
    formatDate: function(date) { ... }
};

// Управление этапами
const stepManager = {
    showStep: function(stepNumber) { ... },
    hideStep: function(stepNumber) { ... },
    showStep1: function() { ... },
    showStep2: function() { ... },
    showStep3: function() { ... },
    showStep4: function() { ... }
};

// Управление наборами документов
const complectManager = {
    addComplect: function() { ... },
    removeComplect: function() { ... },
    renderComplects: function() { ... },
    validateComplect: function(complectId) { ... }
};

// API взаимодействие
const api = {
    parseDocuments: async function(formData) { ... },
    calculatePenalty: async function(data) { ... },
    generateDocuments: async function(data) { ... },
    fetchPlaintiffData: async function(inn) { ... },
    calculateDuty: async function(cost) { ... }
};

// UI компоненты
const ui = {
    showSpinner: function(message) { ... },
    hideSpinner: function() { ... },
    showError: function(title, message) { ... },
    showSuccess: function(message) { ... }
};

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    loadState();
    renderComplects();
    setupEventListeners();
}
```

### 7.2. Обработка событий

- Использование Event Delegation где возможно
- Обработчики для всех интерактивных элементов
- Валидация в реальном времени

### 7.3. Обработка ошибок

- Try-catch блоки для всех асинхронных операций
- Понятные сообщения об ошибках для пользователя
- Логирование ошибок в консоль для отладки

---

## 8. Flask Backend требования

### 8.1. Структура Flask приложения

```python
# app.py
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from LegalDocInspector.legal_doc_inspector.utils.parse_info_by_inn import parse_html
from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import calculate_state_duty

app = Flask(__name__)
CORS(app)

BACKEND_URL = "http://localhost:5001"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse-inn/<inn>')
def parse_inn(inn):
    try:
        full_name, short_name, address, kpp, ogrn = parse_html(inn)
        return jsonify({
            'full_name': full_name,
            'short_name': short_name,
            'address': address,
            'kpp': kpp,
            'ogrn': ogrn
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate-duty', methods=['POST'])
def calculate_duty():
    data = request.get_json()
    cost = data.get('cost')
    try:
        duty = calculate_state_duty(cost)
        return jsonify({'duty': duty})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/proxy/parse', methods=['POST'])
def proxy_parse():
    files = {}
    data = {}
    
    # Обработка файлов из FormData
    for key, file in request.files.items():
        files[key] = (file.filename, file.stream, file.content_type)
    
    # Обработка данных
    for key, value in request.form.items():
        data[key] = value
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/parse",
            files=files,
            data=data,
            timeout=300
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/calculate-penalty', methods=['POST'])
def proxy_calculate_penalty():
    data = request.get_json()
    try:
        response = requests.post(
            f"{BACKEND_URL}/calculate_penalty",
            json=data,
            timeout=300
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/create-doc', methods=['POST'])
def proxy_create_doc():
    data = request.get_json()
    try:
        response = requests.post(
            f"{BACKEND_URL}/create_doc",
            json=data,
            timeout=300
        )
        return response.content, response.status_code, {'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/create-calculating-table', methods=['POST'])
def proxy_create_calculating_table():
    data = request.get_json()
    try:
        response = requests.post(
            f"{BACKEND_URL}/create_calculating_table",
            json=data,
            timeout=300
        )
        return response.content, response.status_code, {'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### 8.2. Обработка ошибок

- Обработка исключений во всех endpoints
- Возврат понятных сообщений об ошибках
- Логирование ошибок

### 8.3. CORS

- Настройка CORS для работы фронтенда и бэкенда на разных портах
- Разрешение необходимых заголовков и методов

---

## 9. Требования к обработке ошибок

### 9.1. Клиентская обработка

- Валидация форм перед отправкой
- Проверка наличия обязательных файлов
- Обработка ошибок сети
- Отображение понятных сообщений пользователю

### 9.2. Серверная обработка

- Валидация входных данных
- Обработка ошибок от основного бэкенд-сервера
- Возврат корректных HTTP статусов
- Логирование ошибок

---

## 10. Требования к производительности

### 10.1. Оптимизация загрузки

- Минимизация размера JavaScript и CSS файлов
- Ленивая загрузка компонентов где возможно
- Кэширование статических ресурсов

### 10.2. Оптимизация работы с данными

- Эффективное использование LocalStorage
- Минимизация перерисовок DOM
- Использование debounce для частых операций

---

## 11. Требования к безопасности

### 11.1. Валидация данных

- Валидация на клиенте и сервере
- Проверка типов файлов
- Ограничение размера файлов

### 11.2. Защита от XSS

- Экранирование пользовательского ввода
- Использование textContent вместо innerHTML где возможно

### 11.3. CORS политика

- Правильная настройка CORS
- Ограничение разрешённых источников в production

---

## 12. Тестирование

### 12.1. Функциональное тестирование

- Тестирование всех этапов работы интерфейса
- Тестирование загрузки файлов
- Тестирование валидации
- Тестирование API endpoints

### 12.2. Кроссбраузерное тестирование

- Chrome/Chromium
- Firefox
- Safari
- Edge

### 12.3. Тестирование адаптивности

- Mobile устройства
- Планшеты
- Desktop

---

## 13. Документация

### 13.1. Код документация

- Комментарии в JavaScript коде
- Описание функций и их параметров
- Описание структуры данных

### 13.2. Пользовательская документация

- Инструкция по использованию интерфейса
- Описание этапов работы
- FAQ

---

## 14. Критерии приёмки

### 14.1. Функциональные критерии

- ✅ Все этапы интерфейса работают последовательно
- ✅ Загрузка множественных наборов документов функционирует корректно
- ✅ Автозаполнение данных об истце работает
- ✅ Расчёт пени выполняется успешно
- ✅ Генерация и скачивание документов работает
- ✅ Сохранение состояния между перезагрузками страницы

### 14.2. Технические критерии

- ✅ Интеграция с Flask API работает корректно
- ✅ Интеграция с основным бэкенд-сервером работает
- ✅ Обработка ошибок реализована на всех этапах
- ✅ Валидация данных работает корректно
- ✅ Адаптивный дизайн работает на всех устройствах

### 14.3. UX критерии

- ✅ Интерфейс интуитивно понятен
- ✅ Сообщения об ошибках информативны
- ✅ Обратная связь с пользователем присутствует на всех этапах
- ✅ Процесс работы логичен и последователен
- ✅ Дизайн современный и профессиональный

---

## 15. Структура файлов проекта

```
LegalDocInspector/
├── web_frontend/
│   ├── app.py                    # Flask приложение
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css        # Основные стили
│   │   ├── js/
│   │   │   ├── app.js            # Основная логика приложения
│   │   │   ├── api.js            # API взаимодействие
│   │   │   ├── state.js          # Управление состоянием
│   │   │   └── ui.js             # UI компоненты
│   │   └── images/
│   │       └── (изображения)
│   └── templates/
│       └── index.html            # Главная страница
├── LegalDocInspector/
│   └── ... (существующий код)
└── requirements.txt
```

---

**Дата создания**: 2024  
**Версия**: 1.0  
**Статус**: Утверждено  
**Технологии**: HTML5, CSS3, JavaScript (ES6+), Flask, Python 3.11+

