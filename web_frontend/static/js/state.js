/**
 * Управление состоянием приложения
 */

// Глобальное состояние приложения
const appState = {
    formData: {
        courtInfo: {},
        plaintiffInfo: {},
        defendantInfo: {},
        lawsuitInfo: {},
        result: null,
        result2: null,
        pathToSave: null,
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
    contracts: {},
    claimsInfo: []
};

/**
 * Сохранение состояния в LocalStorage
 */
function saveState() {
    try {
        // Сохраняем только необходимые данные (не файлы)
        const stateToSave = {
            formData: {
                ...appState.formData,
                result: appState.formData.result,
                result2: appState.formData.result2,
                lawsuitBlob: null, // Не сохраняем blob
                lawsuitTableBlob: null // Не сохраняем blob
            },
            complects: {}, // Не сохраняем файлы
            contracts: appState.contracts
        };
        localStorage.setItem('legalDocInspectorState', JSON.stringify(stateToSave));
    } catch (error) {
        console.error('Ошибка сохранения состояния:', error);
    }
}

/**
 * Загрузка состояния из LocalStorage
 */
function loadState() {
    try {
        const savedState = localStorage.getItem('legalDocInspectorState');
        if (savedState) {
            const parsed = JSON.parse(savedState);
            // Восстанавливаем только не-файловые данные
            if (parsed.formData) {
                appState.formData = {
                    ...appState.formData,
                    ...parsed.formData,
                    result: parsed.formData.result || null,
                    result2: parsed.formData.result2 || null
                };
            }
            if (parsed.contracts) {
                appState.contracts = parsed.contracts;
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки состояния:', error);
    }
}

/**
 * Очистка состояния
 */
function clearState() {
    appState.formData = {
        courtInfo: {},
        plaintiffInfo: {},
        defendantInfo: {},
        lawsuitInfo: {},
        result: null,
        result2: null,
        pathToSave: null,
        flags: {
            step1Complete: false,
            step2Complete: false,
            step3Complete: false,
            formsChanged: false
        },
        numComplects: 1,
        companyType: 'Прочие',
        endDate: null
    };
    appState.complects = {};
    appState.contracts = {};
    appState.claimsInfo = [];
    localStorage.removeItem('legalDocInspectorState');
}

/**
 * Обработчик изменений формы
 */
function onFormChange() {
    appState.formData.flags.formsChanged = true;
    saveState();
}

