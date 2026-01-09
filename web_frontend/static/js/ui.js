/**
 * UI компоненты и утилиты
 */

/**
 * Показать спиннер загрузки
 */
function showSpinner(message = 'Загрузка...') {
    const overlay = document.getElementById('spinner-overlay');
    const messageEl = document.getElementById('spinner-message');
    if (overlay && messageEl) {
        messageEl.textContent = message;
        overlay.style.display = 'flex';
    }
}

/**
 * Скрыть спиннер загрузки
 */
function hideSpinner() {
    const overlay = document.getElementById('spinner-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Показать сообщение об ошибке
 */
function showError(title, message) {
    const errorContainer = document.getElementById('error-container');
    if (!errorContainer) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(message)}</p>
        <button onclick="this.parentElement.remove()" style="margin-top: 10px; padding: 5px 10px; background: #991b1b; color: white; border: none; border-radius: 4px; cursor: pointer;">Закрыть</button>
    `;
    
    errorContainer.appendChild(errorDiv);
    
    // Автоматически удалить через 10 секунд
    setTimeout(() => {
        if (errorDiv.parentElement) {
            errorDiv.remove();
        }
    }, 10000);
}

/**
 * Показать сообщение об успехе
 */
function showSuccess(message) {
    const errorContainer = document.getElementById('error-container');
    if (!errorContainer) return;

    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.innerHTML = `
        <p>${escapeHtml(message)}</p>
        <button onclick="this.parentElement.remove()" style="margin-top: 10px; padding: 5px 10px; background: #065f46; color: white; border: none; border-radius: 4px; cursor: pointer;">Закрыть</button>
    `;
    
    errorContainer.appendChild(successDiv);
    
    // Автоматически удалить через 5 секунд
    setTimeout(() => {
        if (successDiv.parentElement) {
            successDiv.remove();
        }
    }, 5000);
}

/**
 * Экранирование HTML для защиты от XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Форматирование даты в формат DD.MM.YYYY
 */
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}.${month}.${year}`;
}

/**
 * Показать этап
 */
function showStep(stepNumber) {
    // Скрыть все этапы
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`step${i}`);
        if (step) {
            step.style.display = 'none';
        }
    }
    
    // Показать нужный этап
    const targetStep = document.getElementById(`step${stepNumber}`);
    if (targetStep) {
        targetStep.style.display = 'block';
        targetStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Обновить отображение имени файла
 */
function updateFileDisplay(input, displayElement) {
    if (input.files && input.files.length > 0) {
        if (input.multiple) {
            const fileNames = Array.from(input.files).map(f => f.name).join(', ');
            displayElement.textContent = `Выбрано файлов: ${input.files.length} - ${fileNames}`;
        } else {
            displayElement.textContent = `Выбран файл: ${input.files[0].name}`;
        }
    } else {
        displayElement.textContent = '';
    }
}

