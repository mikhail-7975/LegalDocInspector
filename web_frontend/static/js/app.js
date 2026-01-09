/**
 * Основная логика приложения LegalDocInspector
 */

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Инициализация приложения
 */
function initializeApp() {
    loadState();
    
    // Восстановление даты
    if (appState.formData.endDate) {
        const dateInput = document.getElementById('end-date');
        if (dateInput) {
            dateInput.value = appState.formData.endDate;
        }
    }
    
    // Восстановление типа компании
    const companyTypeSelect = document.getElementById('company-type');
    if (companyTypeSelect) {
        companyTypeSelect.value = appState.formData.companyType;
    }
    
    // Инициализация наборов документов
    if (Object.keys(appState.complects).length === 0) {
        appState.complects[1] = {
            contract: null,
            claim: null,
            debtCertificates: [],
            egrulCertificate: null
        };
        appState.formData.numComplects = 1;
    }
    
    renderComplects();
    updateSubmitButton();
    
    // Определить какой этап показать
    if (appState.formData.flags.step3Complete) {
        showStep(4);
        setupDownloadLinks();
    } else if (appState.formData.flags.step2Complete) {
        showStep(3);
        populateLawsuitFields();
    } else if (appState.formData.flags.step1Complete) {
        showStep(2);
        initializeContracts();
        initializeClaimsInfo();
        populateDefendantFields();
    } else {
        showStep(1);
    }
}

/**
 * Сброс состояния приложения и возврат к этапу 1
 */
function resetApplication() {
    // Подтверждение действия
    if (!confirm('Вы уверены, что хотите сбросить состояние? Все несохранённые данные будут потеряны.')) {
        return;
    }
    
    // Очистка состояния
    clearState();
    
    // Очистка всех полей формы
    const dateInput = document.getElementById('end-date');
    if (dateInput) {
        dateInput.value = '';
    }
    
    const companyTypeSelect = document.getElementById('company-type');
    if (companyTypeSelect) {
        companyTypeSelect.value = 'Прочие';
    }
    
    // Очистка полей истца
    const plaintiffFields = ['plaintiff-inn', 'plaintiff-full-name', 'plaintiff-short-name', 
                             'plaintiff-address', 'plaintiff-correspondency-address', 'plaintiff-ogrn'];
    plaintiffFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            if (fieldId === 'plaintiff-inn') {
                field.value = '7720518494';
            } else if (fieldId === 'plaintiff-correspondency-address') {
                field.value = '121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613';
            } else {
                field.value = '';
            }
        }
    });
    
    // Очистка полей ответчика
    const defendantFields = ['defendant-full-name', 'defendant-short-name', 
                            'defendant-address', 'defendant-inn', 'defendant-ogrn'];
    defendantFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.value = '';
        }
    });
    
    // Очистка полей суда
    const courtName = document.getElementById('court-name');
    const courtAddress = document.getElementById('court-address');
    if (courtName) courtName.value = 'Арбитражный суд города Москвы';
    if (courtAddress) courtAddress.value = '115225, г. Москва, ул. Большая Тульская, д. 17';
    
    // Очистка полей иска
    const lawsuitFields = ['lawsuit-cost', 'lawsuit-tax', 'lawsuit-service-type'];
    lawsuitFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            if (fieldId === 'lawsuit-service-type') {
                field.value = 'ГВС + ТЭ';
            } else {
                field.value = '';
            }
        }
    });
    
    // Очистка контейнеров
    const complectsContainer = document.getElementById('complects-container');
    if (complectsContainer) {
        complectsContainer.innerHTML = '';
    }
    
    const contractsContainer = document.getElementById('contracts-container');
    if (contractsContainer) {
        contractsContainer.innerHTML = '';
    }
    
    const claimsInfoContainer = document.getElementById('claims-info-container');
    if (claimsInfoContainer) {
        claimsInfoContainer.innerHTML = '';
    }
    
    const claimsContainer = document.getElementById('claims-container');
    if (claimsContainer) {
        claimsContainer.innerHTML = '';
    }
    
    // Очистка ссылок на скачивание
    const downloadLawsuit = document.getElementById('download-lawsuit');
    const downloadCalculation = document.getElementById('download-calculation');
    if (downloadLawsuit) {
        downloadLawsuit.href = '#';
    }
    if (downloadCalculation) {
        downloadCalculation.href = '#';
    }
    
    // Инициализация начального состояния
    appState.complects[1] = {
        contract: null,
        claim: null,
        debtCertificates: [],
        egrulCertificate: null
    };
    appState.formData.numComplects = 1;
    
    // Перерисовка интерфейса
    renderComplects();
    updateSubmitButton();
    
    // Переключение на этап 1
    showStep(1);
    
    // Показать сообщение об успехе
    showSuccess('Состояние приложения сброшено. Вы можете начать заново.');
}

/**
 * Обработка изменения даты
 */
function handleDateChange(event) {
    appState.formData.endDate = event.target.value;
    onFormChange();
}

/**
 * Обработка изменения типа компании
 */
function handleCompanyTypeChange(event) {
    appState.formData.companyType = event.target.value;
    onFormChange();
}

/**
 * Обработка загрузки файла
 */
function handleFileUpload(event, complectId, fileType) {
    const input = event.target;
    const complect = appState.complects[complectId];
    
    if (!complect) {
        console.error(`Набор ${complectId} не найден`);
        return;
    }
    
    if (fileType === 'contract') {
        complect.contract = input.files[0] || null;
    } else if (fileType === 'claim') {
        complect.claim = input.files[0] || null;
    } else if (fileType === 'debt-certificate') {
        complect.debtCertificates = Array.from(input.files);
    } else if (fileType === 'egrul-certificate') {
        complect.egrulCertificate = input.files[0] || null;
    }
    
    // Обновить отображение
    const displayElement = input.parentElement.querySelector('.file-name-display');
    if (displayElement) {
        updateFileDisplay(input, displayElement);
    }
    
    updateSubmitButton();
    saveState();
}

/**
 * Добавить набор документов
 */
function addComplect() {
    appState.formData.numComplects += 1;
    const newId = appState.formData.numComplects;
    appState.complects[newId] = {
        contract: null,
        claim: null,
        debtCertificates: [],
        egrulCertificate: null
    };
    appState.formData.flags.step1Complete = false;
    onFormChange();
    renderComplects();
    updateSubmitButton();
}

/**
 * Удалить набор документов
 */
function removeComplect() {
    if (appState.formData.numComplects === 1) {
        showError('Ошибка', 'Должен быть хотя бы один набор');
        return;
    }
    
    const lastId = appState.formData.numComplects;
    delete appState.complects[lastId];
    appState.formData.numComplects -= 1;
    onFormChange();
    renderComplects();
    updateSubmitButton();
}

/**
 * Отрисовка всех наборов документов
 */
function renderComplects() {
    const container = document.getElementById('complects-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    for (let i = 1; i <= appState.formData.numComplects; i++) {
        if (!appState.complects[i]) {
            appState.complects[i] = {
                contract: null,
                claim: null,
                debtCertificates: []
            };
        }
        
        const complectHTML = createComplectHTML(i);
        container.insertAdjacentHTML('beforeend', complectHTML);
        
        // Восстановить отображение файлов
        const complectElement = container.querySelector(`[data-complect-id="${i}"]`);
        if (complectElement) {
            const contractInput = complectElement.querySelector('[data-file-type="contract"]');
            const claimInput = complectElement.querySelector('[data-file-type="claim"]');
            const debtInput = complectElement.querySelector('[data-file-type="debt-certificate"]');
            const egrulInput = complectElement.querySelector('[data-file-type="egrul-certificate"]');
            
            if (contractInput && appState.complects[i].contract) {
                updateFileDisplay(contractInput, contractInput.parentElement.querySelector('.file-name-display'));
            }
            if (claimInput && appState.complects[i].claim) {
                updateFileDisplay(claimInput, claimInput.parentElement.querySelector('.file-name-display'));
            }
            if (debtInput && appState.complects[i].debtCertificates.length > 0) {
                updateFileDisplay(debtInput, debtInput.parentElement.querySelector('.file-name-display'));
            }
            if (egrulInput && appState.complects[i].egrulCertificate) {
                updateFileDisplay(egrulInput, egrulInput.parentElement.querySelector('.file-name-display'));
            }
        }
    }
}

/**
 * Создание HTML для набора документов
 */
function createComplectHTML(complectId) {
    return `
        <div class="complect-container" data-complect-id="${complectId}">
            <h3>Набор <span class="complect-number">${complectId}</span></h3>
            
            <div class="file-upload-group">
                <label>Поле для договора</label>
                <input type="file" 
                       class="file-input" 
                       data-file-type="contract"
                       data-complect-id="${complectId}"
                       accept=".pdf,.doc,.docx"
                       onchange="handleFileUpload(event, ${complectId}, 'contract')">
                <div class="file-name-display"></div>
            </div>
            
            <div class="file-upload-group">
                <label>Поле для претензии</label>
                <input type="file" 
                       class="file-input" 
                       data-file-type="claim"
                       data-complect-id="${complectId}"
                       accept=".pdf,.doc,.docx"
                       onchange="handleFileUpload(event, ${complectId}, 'claim')">
                <div class="file-name-display"></div>
            </div>
            
            <div class="file-upload-group">
                <label>Поле для Excel справки о задолженности</label>
                <input type="file" 
                       class="file-input" 
                       data-file-type="debt-certificate"
                       data-complect-id="${complectId}"
                       accept=".xls,.xlsx,.xlsm"
                       multiple
                       onchange="handleFileUpload(event, ${complectId}, 'debt-certificate')">
                <div class="file-name-display"></div>
            </div>
            
            <div class="file-upload-group">
                <label>Поле для выписки из ЕГРЮЛ</label>
                <input type="file" 
                       class="file-input" 
                       data-file-type="egrul-certificate"
                       data-complect-id="${complectId}"
                       accept=".pdf,.doc,.docx"
                       onchange="handleFileUpload(event, ${complectId}, 'egrul-certificate')">
                <div class="file-name-display"></div>
            </div>
        </div>
    `;
}

/**
 * Валидация набора документов
 */
function validateComplect(complectId) {
    const complect = appState.complects[complectId];
    return complect &&
           complect.contract !== null &&
           complect.claim !== null &&
           complect.debtCertificates !== null &&
           complect.debtCertificates.length > 0;
}

/**
 * Валидация всех наборов
 */
function validateAllComplects() {
    for (let i = 1; i <= appState.formData.numComplects; i++) {
        if (!validateComplect(i)) {
            return false;
        }
    }
    return true;
}

/**
 * Обновление состояния кнопки отправки
 */
function updateSubmitButton() {
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        submitBtn.disabled = !validateAllComplects();
    }
}

/**
 * Отправка документов на сервер
 */
async function submitDocuments() {
    if (!validateAllComplects()) {
        showError('Ошибка валидации', 'Пожалуйста, загрузите все необходимые файлы во всех наборах');
        return;
    }
    
    const formData = new FormData();
    
    // Добавление даты
    const endDate = document.getElementById('end-date').value;
    if (!endDate) {
        showError('Ошибка', 'Пожалуйста, выберите дату конца просрочки');
        return;
    }
    formData.append('date', endDate);
    
    // Добавление файлов для каждого набора
    console.log('DEBUG: Отправка файлов, наборы:', Object.keys(appState.complects));
    for (const [complectId, complect] of Object.entries(appState.complects)) {
        console.log(`DEBUG: Набор ${complectId}:`, {
            contract: complect.contract ? complect.contract.name : null,
            claim: complect.claim ? complect.claim.name : null,
            debtCertificates: complect.debtCertificates ? complect.debtCertificates.length : 0,
            egrulCertificate: complect.egrulCertificate ? complect.egrulCertificate.name : null
        });
        
        if (complect.contract) {
            formData.append(`complect_${complectId}_contract_file`, complect.contract, complect.contract.name);
        }
        if (complect.claim) {
            formData.append(`complect_${complectId}_claim_file`, complect.claim, complect.claim.name);
        }
        if (complect.debtCertificates && complect.debtCertificates.length > 0) {
            complect.debtCertificates.forEach((file, index) => {
                formData.append(`complect_${complectId}_certificate_file_${index}`, file, file.name);
            });
            formData.append(`${complectId}_certificates_count`, complect.debtCertificates.length.toString());
        }
        if (complect.egrulCertificate) {
            console.log(`DEBUG: Добавляю файл ЕГРЮЛ для набора ${complectId}:`, complect.egrulCertificate.name);
            formData.append(`complect_${complectId}_egrul_certificate_file`, complect.egrulCertificate, complect.egrulCertificate.name);
        } else {
            console.log(`DEBUG: Файл ЕГРЮЛ для набора ${complectId} отсутствует`);
        }
    }
    
    // Отладка: вывести все ключи FormData
    console.log('DEBUG: Ключи FormData перед отправкой:');
    for (const [key, value] of formData.entries()) {
        if (value instanceof File) {
            console.log(`  ${key}: File(${value.name}, ${value.size} bytes)`);
        } else {
            console.log(`  ${key}: ${value}`);
        }
    }
    
    formData.append('complects_count', Object.keys(appState.complects).length.toString());
    
    showSpinner('Ваш запрос обрабатывается, пожалуйста, подождите, обработка одного набора занимает в среднем 2 минуты');
    
    try {
        const result = await parseDocuments(formData);
        appState.formData.result = result;
        appState.formData.pathToSave = result.path_to_save;
        appState.formData.flags.step1Complete = true;
        saveState();
        
        showStep(2);
        initializeContracts();
        initializeClaimsInfo();
        populateDefendantFields();
        showSuccess('Файлы успешно обработаны!');
    } catch (error) {
        showError('Ошибка при отправке запроса', error.message);
    } finally {
        hideSpinner();
    }
}

/**
 * Инициализация данных о договорах
 */
function initializeContracts() {
    if (!appState.formData.result || !appState.formData.result.table_parser_result) {
        return;
    }
    
    appState.contracts = {};
    
    for (const contractInfo of appState.formData.result.table_parser_result) {
        const contractNumber = contractInfo[1];
        const overdueDateInfo = contractInfo[2];
        const serviceTypeInfo = contractInfo[3];
        
        appState.contracts[contractNumber] = {
            serviceType: serviceTypeInfo,
            overdueDate: overdueDateInfo,
            dayOfPenalty: 18,
            contractPoint: '5.5'
        };
    }
    
    renderContracts();
    saveState();
}

/**
 * Отрисовка форм для договоров
 */
function renderContracts() {
    const container = document.getElementById('contracts-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    for (const [contractNumber, contractData] of Object.entries(appState.contracts)) {
        const contractHTML = createContractFormHTML(contractNumber, contractData);
        container.insertAdjacentHTML('beforeend', contractHTML);
    }
}

/**
 * Инициализация данных о претензиях
 */
function initializeClaimsInfo() {
    if (!appState.formData.result || !appState.formData.result.table_parser_result) {
        return;
    }
    
    // Собираем все претензии из всех договоров
    const allClaims = [];
    
    for (const contractInfo of appState.formData.result.table_parser_result) {
        const contractNumber = contractInfo[1];
        const claimInfo = contractInfo[4];
        
        if (claimInfo && typeof claimInfo === 'object' && !Array.isArray(claimInfo)) {
            // claimInfo это объект вида { claim_date: "01.01.2000", claim_number: "123456" }
            if (claimInfo.claim_number && claimInfo.claim_date) {
                allClaims.push({
                    contractNumber: contractNumber,
                    claimNumber: claimInfo.claim_number,
                    claimDate: claimInfo.claim_date
                });
            }
        } else if (claimInfo && Array.isArray(claimInfo)) {
            // Поддержка старого формата (массив претензий)
            for (const claimItem of claimInfo) {
                if (claimItem && claimItem.claim_number && claimItem.claim_date) {
                    allClaims.push({
                        contractNumber: contractNumber,
                        claimNumber: claimItem.claim_number,
                        claimDate: claimItem.claim_date
                    });
                }
            }
        }
    }
    
    // Сохраняем в состояние для дальнейшего использования
    if (!appState.claimsInfo) {
        appState.claimsInfo = [];
    }
    appState.claimsInfo = allClaims;
    
    renderClaimsInfo();
    saveState();
}

/**
 * Отрисовка информации о претензиях
 */
function renderClaimsInfo() {
    const container = document.getElementById('claims-info-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!appState.claimsInfo || appState.claimsInfo.length === 0) {
        container.innerHTML = `
            <div class="info-message">
                <p>Претензии не найдены в загруженных документах.</p>
            </div>
        `;
        return;
    }
    
    appState.claimsInfo.forEach((claim, index) => {
        const claimHTML = createClaimInfoHTML(claim, index);
        container.insertAdjacentHTML('beforeend', claimHTML);
    });
}

/**
 * Создание HTML блока для информации о претензии
 */
function createClaimInfoHTML(claimData, index) {
    return `
        <div class="claim-info-form" data-claim-index="${index}">
            <h4>Претензия #${index + 1}</h4>
            <div class="info-display">
                <p><strong>Номер претензии:</strong></p>
                <p class="info-text">${escapeHtml(claimData.claimNumber || 'Не указано')}</p>
            </div>
            <div class="info-display">
                <p><strong>Дата претензии:</strong></p>
                <p class="info-text">${escapeHtml(claimData.claimDate || 'Не указано')}</p>
            </div>
            <div class="info-display">
                <p><strong>Договор:</strong></p>
                <p class="info-text">${escapeHtml(claimData.contractNumber || 'Не указано')}</p>
            </div>
        </div>
    `;
}

/**
 * Создание HTML формы для договора
 */
function createContractFormHTML(contractNumber, contractData) {
    return `
        <div class="contract-form" data-contract-number="${escapeHtml(contractNumber)}">
            <h4>Информация из договора ${escapeHtml(contractNumber)}</h4>
            <div class="info-display">
                <p><strong>Информация по дню начала просрочки:</strong></p>
                <p class="info-text">${escapeHtml(contractData.overdueDate || 'Не указано')}</p>
            </div>
            <div class="info-display">
                <p><strong>Информация о предмете договора:</strong></p>
                <p class="info-text">${escapeHtml(contractData.serviceType || 'Не указано')}</p>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Выберите число месяца, которое является последним днём оплаты счёта</label>
                    <input type="number" 
                           class="form-control contract-day-penalty"
                           data-contract-number="${escapeHtml(contractNumber)}"
                           min="1" 
                           max="31" 
                           value="${contractData.dayOfPenalty || 18}"
                           onchange="handleContractDayChange(event, '${escapeHtml(contractNumber)}')">
                </div>
                <div class="form-group">
                    <label>Напишите номер пункта договора, в котором говорится о дне начала просрочки</label>
                    <input type="text" 
                           class="form-control contract-point"
                           data-contract-number="${escapeHtml(contractNumber)}"
                           value="${escapeHtml(contractData.contractPoint || '5.5')}"
                           onchange="handleContractPointChange(event, '${escapeHtml(contractNumber)}')">
                </div>
            </div>
        </div>
    `;
}

/**
 * Обработка изменения дня оплаты договора
 */
function handleContractDayChange(event, contractNumber) {
    if (appState.contracts[contractNumber]) {
        appState.contracts[contractNumber].dayOfPenalty = parseInt(event.target.value);
        onFormChange();
    }
}

/**
 * Обработка изменения пункта договора
 */
function handleContractPointChange(event, contractNumber) {
    if (appState.contracts[contractNumber]) {
        appState.contracts[contractNumber].contractPoint = event.target.value;
        onFormChange();
    }
}

/**
 * Заполнение полей ответчика
 */
function populateDefendantFields() {
    if (!appState.formData.result || !appState.formData.result.results_of_name_parser) {
        return;
    }
    
    const defendantInfo = appState.formData.result.results_of_name_parser.defendant_info;
    
    const fullNameInput = document.getElementById('defendant-full-name');
    const shortNameInput = document.getElementById('defendant-short-name');
    const addressInput = document.getElementById('defendant-address');
    const innInput = document.getElementById('defendant-inn');
    const ogrnInput = document.getElementById('defendant-ogrn');
    
    if (fullNameInput && defendantInfo.full_name) {
        fullNameInput.value = defendantInfo.full_name.toUpperCase();
    }
    if (shortNameInput && defendantInfo.short_name) {
        shortNameInput.value = defendantInfo.short_name;
    }
    if (addressInput && defendantInfo.address) {
        addressInput.value = defendantInfo.address;
    }
    if (innInput && defendantInfo.inn) {
        innInput.value = defendantInfo.inn;
    }
    if (ogrnInput && defendantInfo.ogrn) {
        ogrnInput.value = defendantInfo.ogrn;
    }
    
    // Сохранить в состояние
    appState.formData.defendantInfo = {
        full_name: defendantInfo.full_name || '',
        short_name: defendantInfo.short_name || '',
        addres: defendantInfo.address || '',
        inn: defendantInfo.inn || '',
        ogrn: defendantInfo.ogrn || ''
    };
    saveState();
}

/**
 * Обработка изменения ИНН истца
 */
async function handlePlaintiffINNChange(event) {
    const inn = event.target.value;
    if (!inn || inn.length < 10) {
        return;
    }
    
    try {
        const data = await fetchPlaintiffData(inn);
        if (data && !data.error) {
            populatePlaintiffFields(data);
        }
    } catch (error) {
        // Ошибка будет показана в fetchPlaintiffData
    }
}

/**
 * Заполнение полей истца
 */
function populatePlaintiffFields(data) {
    const fullNameInput = document.getElementById('plaintiff-full-name');
    const shortNameInput = document.getElementById('plaintiff-short-name');
    const addressInput = document.getElementById('plaintiff-address');
    const ogrnInput = document.getElementById('plaintiff-ogrn');
    
    if (fullNameInput && data.full_name) {
        fullNameInput.value = data.full_name.toUpperCase();
    }
    if (shortNameInput && data.short_name) {
        shortNameInput.value = data.short_name;
    }
    if (addressInput && data.address) {
        addressInput.value = data.address;
    }
    if (ogrnInput && data.ogrn) {
        ogrnInput.value = data.ogrn;
    }
    
    // Сохранить в состояние
    appState.formData.plaintiffInfo = {
        inn: document.getElementById('plaintiff-inn').value,
        full_name: data.full_name || '',
        short_name: data.short_name || '',
        addres: data.address || '',
        correspondency_addres: document.getElementById('plaintiff-correspondency-address').value,
        ogrn: data.ogrn || ''
    };
    saveState();
}

/**
 * Обновление данных об истце
 */
async function updatePlaintiffData() {
    const inn = document.getElementById('plaintiff-inn').value;
    if (!inn) {
        showError('Ошибка', 'Введите ИНН истца');
        return;
    }
    
    showSpinner('Получение данных об истце...');
    
    try {
        const data = await fetchPlaintiffData(inn);
        if (data && !data.error) {
            populatePlaintiffFields(data);
            showSuccess('Данные об истце успешно обновлены');
        } else {
            showError('Ошибка', data?.error || 'Не удалось получить данные по ИНН');
        }
    } catch (error) {
        showError('Ошибка', error.message);
    } finally {
        hideSpinner();
    }
}

/**
 * Расчёт пени
 */
async function calculatePenalty() {
    if (!appState.formData.result || !appState.formData.result.table_parser_result) {
        showError('Ошибка', 'Сначала необходимо обработать документы');
        return;
    }
    
    // Собрать данные о суде
    const courtName = document.getElementById('court-name');
    const courtAddress = document.getElementById('court-address');
    appState.formData.courtInfo = {
        name: courtName ? courtName.value : '',
        addres: courtAddress ? courtAddress.value : ''
    };
    
    // Собрать данные об истце
    appState.formData.plaintiffInfo = {
        inn: document.getElementById('plaintiff-inn').value,
        full_name: document.getElementById('plaintiff-full-name').value,
        short_name: document.getElementById('plaintiff-short-name').value,
        addres: document.getElementById('plaintiff-address').value,
        correspondency_addres: document.getElementById('plaintiff-correspondency-address').value,
        ogrn: document.getElementById('plaintiff-ogrn').value
    };
    
    const requestData = {
        company_type: appState.formData.companyType,
        end_date: formatDate(appState.formData.endDate),
        parsing_results: []
    };
    
    // Сбор данных о договорах
    for (const contractInfo of appState.formData.result.table_parser_result) {
        const contractNumber = contractInfo[1];
        const contract = appState.contracts[contractNumber];
        
        if (contract) {
            requestData.parsing_results.push({
                parsed_info: contractInfo[0],
                contract_point: contract.contractPoint,
                day_of_penalty: contract.dayOfPenalty,
                contract_number: contractNumber
            });
        }
    }
    
    showSpinner('Ваш запрос обрабатывается, пожалуйста, подождите');
    
    try {
        const result = await calculatePenaltyAPI(requestData);
        appState.formData.result2 = result;
        appState.formData.flags.step2Complete = true;
        saveState();
        
        showStep(3);
        populateLawsuitFields();
        showSuccess('Расчёты успешно произведены!');
    } catch (error) {
        showError('Ошибка при расчёте пени', error.message);
    } finally {
        hideSpinner();
    }
}

/**
 * Заполнение полей данных об иске
 */
function populateLawsuitFields() {
    if (!appState.formData.result2 || !appState.formData.result2.claim_data) {
        return;
    }
    
    const costInput = document.getElementById('lawsuit-cost');
    const taxInput = document.getElementById('lawsuit-tax');
    
    const cost = appState.formData.result2.claim_data.table_info?.cost_of_lawsuit;
    if (costInput && cost) {
        costInput.value = cost;
    }
    
    // Расчёт госпошлины
    if (cost && taxInput) {
        calculateDuty(cost).then(duty => {
            if (duty) {
                taxInput.value = duty;
            }
        }).catch(error => {
            console.error('Ошибка расчёта госпошлины:', error);
        });
    }
    
    // Заполнение претензий
    renderClaims();
}

/**
 * Отрисовка полей для претензий
 */
function renderClaims() {
    const container = document.getElementById('claims-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!appState.formData.result || !appState.formData.result.table_parser_result) {
        console.warn('Нет данных result для отрисовки претензий');
        return;
    }
    
    const claims = [];
    for (const contractInfo of appState.formData.result.table_parser_result) {
        const claimInfo = contractInfo[4];
        if (claimInfo && typeof claimInfo === 'object' && !Array.isArray(claimInfo)) {
            // claimInfo это объект вида { claim_date: "01.01.2000", claim_number: "123456" }
            if (claimInfo.claim_number && claimInfo.claim_date) {
                claims.push(`№ ${claimInfo.claim_number} от ${claimInfo.claim_date}`);
            }
        } else if (claimInfo && Array.isArray(claimInfo)) {
            // Поддержка старого формата (массив претензий)
            for (const claimItem of claimInfo) {
                if (claimItem && claimItem.claim_number && claimItem.claim_date) {
                    claims.push(`№ ${claimItem.claim_number} от ${claimItem.claim_date}`);
                }
            }
        }
    }
    
    // Если претензии не найдены, показываем предупреждение
    if (claims.length === 0) {
        console.warn('Не найдено ни одной претензии в результатах парсинга');
        container.innerHTML = `
            <div class="warning">
                <p><strong>Внимание:</strong> Не найдено ни одной претензии в загруженных документах.</p>
                <p>Пожалуйста, добавьте претензии вручную:</p>
            </div>
            <div class="form-group">
                <label for="claim-0">Претензия #1</label>
                <input type="text" 
                       id="claim-0" 
                       class="form-control"
                       placeholder="Например: № 123456 от 01.01.2024"
                       onchange="handleClaimChange(event, 0)">
            </div>
        `;
        appState.formData.lawsuitInfo.claims = [];
        return;
    }
    
    appState.formData.lawsuitInfo.claims = claims;
    
    console.log('Отрисовано претензий:', claims.length, claims);
    
    claims.forEach((claim, index) => {
        const claimHTML = `
            <div class="form-group">
                <label for="claim-${index}">Претензия #${index + 1}</label>
                <input type="text" 
                       id="claim-${index}" 
                       class="form-control"
                       value="${escapeHtml(claim)}"
                       onchange="handleClaimChange(event, ${index})">
            </div>
        `;
        container.insertAdjacentHTML('beforeend', claimHTML);
    });
}

/**
 * Обработка изменения претензии
 */
function handleClaimChange(event, index) {
    if (!appState.formData.lawsuitInfo.claims) {
        appState.formData.lawsuitInfo.claims = [];
    }
    appState.formData.lawsuitInfo.claims[index] = event.target.value;
    onFormChange();
}

/**
 * Обработка изменения цены иска
 */
async function handleLawsuitCostChange(event) {
    const cost = event.target.value;
    const taxInput = document.getElementById('lawsuit-tax');
    
    if (cost && taxInput) {
        try {
            const duty = await calculateDuty(cost);
            if (duty) {
                taxInput.value = duty;
            }
        } catch (error) {
            console.error('Ошибка расчёта госпошлины:', error);
        }
    }
    onFormChange();
}

/**
 * Генерация документов
 */
async function generateDocuments() {
    // Собрать все данные
    appState.formData.lawsuitInfo.cost = document.getElementById('lawsuit-cost').value;
    appState.formData.lawsuitInfo.tax = document.getElementById('lawsuit-tax').value;
    appState.formData.lawsuitInfo.service_type = document.getElementById('lawsuit-service-type').value;
    
    // Собрать претензии из полей формы
    const claims = [];
    const claimsContainer = document.getElementById('claims-container');
    if (claimsContainer) {
        const claimInputs = claimsContainer.querySelectorAll('input[type="text"]');
        claimInputs.forEach(input => {
            if (input.value && input.value.trim()) {
                claims.push(input.value.trim());
            }
        });
    }
    
    // Если претензии не были собраны из полей, попробуем взять из состояния
    if (claims.length === 0 && appState.formData.lawsuitInfo.claims) {
        claims.push(...appState.formData.lawsuitInfo.claims.filter(c => c && c.trim()));
    }
    
    // Проверка наличия претензий
    if (claims.length === 0) {
        showError('Ошибка валидации', 'Необходимо указать хотя бы одну претензию. Пожалуйста, заполните поля претензий.');
        return;
    }
    
    // Обновить список претензий в состоянии
    appState.formData.lawsuitInfo.claims = claims;
    
    const docCreatorData = {
        claim_data: {
            ...appState.formData.result2.claim_data,
            plaintiff_info: appState.formData.plaintiffInfo,
            defendant_info: appState.formData.defendantInfo,
            lawsuit_info: {
                ...appState.formData.lawsuitInfo,
                claims: claims
            }
        },
        calculator_list: appState.formData.result2.calculator_list,
        path_to_save: appState.formData.pathToSave
    };
    
    // Логирование для отладки
    console.log('Отправляемые данные о претензиях:', {
        claims: claims,
        claimsCount: claims.length,
        lawsuitInfo: docCreatorData.claim_data.lawsuit_info
    });
    
    appState.formData.flags.formsChanged = false;
    saveState();
    
    showSpinner('Создание документов...');
    
    try {
        // Создание иска
        const lawsuitBlob = await createDoc(docCreatorData);
        appState.formData.lawsuitBlob = lawsuitBlob;
        
        // Создание расчёта
        const tableBlob = await createCalculatingTable(docCreatorData);
        appState.formData.lawsuitTableBlob = tableBlob;
        
        appState.formData.flags.step3Complete = true;
        saveState();
        
        showStep(4);
        setupDownloadLinks();
        showSuccess('Документы успешно созданы!');
    } catch (error) {
        console.error('Ошибка при создании документов:', error);
        showError('Ошибка при создании документов', error.message);
    } finally {
        hideSpinner();
    }
}

/**
 * Настройка ссылок для скачивания
 */
function setupDownloadLinks() {
    if (appState.formData.lawsuitBlob) {
        const url = URL.createObjectURL(appState.formData.lawsuitBlob);
        const link = document.getElementById('download-lawsuit');
        if (link) {
            link.href = url;
        }
    }
    
    if (appState.formData.lawsuitTableBlob) {
        const url = URL.createObjectURL(appState.formData.lawsuitTableBlob);
        const link = document.getElementById('download-calculation');
        if (link) {
            link.href = url;
        }
    }
}

