/**
 * API взаимодействие с бэкендом
 */

const API_BASE = '';

/**
 * Получение данных по ИНН
 */
async function fetchPlaintiffData(inn) {
    try {
        const response = await fetch(`${API_BASE}/api/parse-inn/${inn}`);
        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Не удалось получить данные по ИНН');
        }
    } catch (error) {
        console.error('Ошибка получения данных по ИНН:', error);
        throw error;
    }
}

/**
 * Расчёт госпошлины
 */
async function calculateDuty(cost) {
    try {
        const response = await fetch(`${API_BASE}/api/calculate-duty`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ cost: cost })
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.duty;
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Ошибка расчёта госпошлины');
        }
    } catch (error) {
        console.error('Ошибка расчёта госпошлины:', error);
        throw error;
    }
}

/**
 * Отправка документов на парсинг
 */
async function parseDocuments(formData) {
    try {
        const response = await fetch(`${API_BASE}/api/proxy/parse`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            const errorText = await response.text();
            throw new Error(`Ошибка парсинга: ${response.status} - ${errorText}`);
        }
    } catch (error) {
        console.error('Ошибка парсинга документов:', error);
        throw error;
    }
}

/**
 * Расчёт пени
 */
async function calculatePenaltyAPI(requestData) {
    try {
        const response = await fetch(`${API_BASE}/api/proxy/calculate-penalty`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            const errorText = await response.text();
            throw new Error(`Ошибка расчёта пени: ${response.status} - ${errorText}`);
        }
    } catch (error) {
        console.error('Ошибка расчёта пени:', error);
        throw error;
    }
}

/**
 * Создание иска
 */
async function createDoc(docCreatorData) {
    try {
        const response = await fetch(`${API_BASE}/api/proxy/create-doc`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(docCreatorData)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            return blob;
        } else {
            const errorText = await response.text();
            throw new Error(`Ошибка создания иска: ${response.status} - ${errorText}`);
        }
    } catch (error) {
        console.error('Ошибка создания иска:', error);
        throw error;
    }
}

/**
 * Создание расчёта к иску
 */
async function createCalculatingTable(docCreatorData) {
    try {
        const response = await fetch(`${API_BASE}/api/proxy/create-calculating-table`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(docCreatorData)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            return blob;
        } else {
            const errorText = await response.text();
            throw new Error(`Ошибка создания расчёта: ${response.status} - ${errorText}`);
        }
    } catch (error) {
        console.error('Ошибка создания расчёта:', error);
        throw error;
    }
}

