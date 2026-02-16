class TestManager {
    constructor() {
        // Получаем элементы DOM
        this.testManagerContainer = document.getElementById('testManagerContainer');
        this.testManagerButton = document.getElementById('testManagerButton');
        this.testMessages = document.getElementById('testMessages');
        this.closeTestChatBtn = document.getElementById('closeTestChatBtn');
        this.clearTestChatBtn = document.getElementById('clearTestChatBtn');
        this.allTestsBtn = document.getElementById('allTestsBtn');
        this.actionTestsBtn = document.getElementById('actionTestsBtn');
        this.testResults = document.getElementById('testResults');
        this.resizer = document.getElementById('resizer');

        // Инициализация состояния
        this.isTestManagerVisible = false;
        this.testHistory = [];
        this.apiBaseUrl = 'http://localhost:3000';
        this.apiAvailable = false;

        // Настройка
        this.initializeEventListeners();
        
        // Проверка API
        this.checkAPIStatus();
    }

    initializeEventListeners() {
        // Основные кнопки
        if (this.testManagerButton) {
            this.testManagerButton.addEventListener('click', () => this.toggleTestManager());
        }
        
        if (this.closeTestChatBtn) {
            this.closeTestChatBtn.addEventListener('click', () => this.hideTestManager());
        }
        
        if (this.clearTestChatBtn) {
            this.clearTestChatBtn.addEventListener('click', () => this.clearTestChat());
        }
        
        if (this.allTestsBtn) {
            this.allTestsBtn.addEventListener('click', () => this.showAllTests());
        }
        
        if (this.actionTestsBtn) {
            this.actionTestsBtn.addEventListener('click', () => this.showActionTests());
        }
    }

    checkAPIStatus() {
        fetch(`${this.apiBaseUrl}/api/health`)
            .then(response => {
                this.apiAvailable = response.ok;
                if (this.apiAvailable) {
                    console.log('✅ Test Manager API доступен');
                } else {
                    console.error('❌ Test Manager API недоступен (статус: ' + response.status + ')');
                }
            })
            .catch(error => {
                console.error('❌ Ошибка подключения к Test Manager API:', error);
                this.apiAvailable = false;
            });
    }

    toggleTestManager() {
        if (this.isTestManagerVisible) {
            this.hideTestManager();
        } else {
            this.showTestManager();
        }
    }

    showTestManager() {
        if (this.testManagerContainer) {
            this.testManagerContainer.style.display = 'block';
            this.isTestManagerVisible = true;
            
            // Показываем приветственное сообщение
            this.addTestMessage('👋 Добро пожаловать в Test Manager!', 'bot');
            this.addTestMessage('Выберите опцию:', 'bot');
            this.addTestMessage('- <b>Все тесты</b> - получить все доступные тесты из модели', 'bot');
            this.addTestMessage('- <b>Тесты для действия</b> - получить тесты для конкретного действия', 'bot');
            
            console.log('✅ Test Manager открыт');
        }
    }

    hideTestManager() {
        if (this.testManagerContainer) {
            this.testManagerContainer.style.display = 'none';
            this.isTestManagerVisible = false;
            console.log('✅ Test Manager закрыт');
        }
    }

    clearTestChat() {
        if (this.testMessages) {
            this.testMessages.innerHTML = '';
            this.testHistory = [];
            this.testResults.innerHTML = '';
            this.addTestMessage('💬 История тестов очищена', 'bot');
            console.log('✅ История тестов очищена');
        }
    }

    addTestMessage(text, sender = 'user') {
        if (!this.testMessages) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}-message`;
        messageElement.innerHTML = text;
        
        this.testMessages.appendChild(messageElement);
        this.testMessages.scrollTop = this.testMessages.scrollHeight;
        
        // Сохраняем в историю
        this.testHistory.push({
            text,
            sender,
            timestamp: new Date().toISOString()
        });
    }

    showAllTests() {
        this.addTestMessage('📋 Запрос всех тестов из модели...', 'user');
        this.addTestMessage('⏳ Получаю список всех тестов...', 'bot');
        
        // Вызов API для получения всех тестов
        fetch(`${this.apiBaseUrl}/api/test-manager/tests`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.displayAllTests(data);
            })
            .catch(error => {
                console.error('❌ Ошибка получения тестов:', error);
                this.addTestMessage(`❌ Ошибка получения тестов: ${error.message}`, 'bot');
                // Показываем демо-данные в случае ошибки
                this.displayDemoTests();
            });
    }

    showActionTests() {
        this.addTestMessage('🎯 Запрос тестов для конкретного действия...', 'user');
        this.addTestMessage('📝 Пожалуйста, укажите ID действия:', 'bot');
        
        // Создаем поле ввода для ID действия
        const inputElement = document.createElement('div');
        inputElement.className = 'action-input';
        inputElement.innerHTML = `
            <input type="text" id="actionIdInput" placeholder="Введите ID действия">
            <button id="submitActionIdBtn" class="primary">Получить тесты</button>
        `;
        
        this.testMessages.appendChild(inputElement);
        
        // Обработчик для кнопки
        document.getElementById('submitActionIdBtn')?.addEventListener('click', () => {
            const actionId = document.getElementById('actionIdInput')?.value;
            if (actionId) {
                this.getTestsForAction(actionId);
            } else {
                this.addTestMessage('⚠️ Пожалуйста, введите ID действия', 'bot');
            }
        });
    }

    displayAllTests(data) {
        if (!data || !data.tests || data.tests.length === 0) {
            this.addTestMessage('⚠️ Не получено данных о тестах', 'bot');
            this.displayDemoTests();
            return;
        }

        this.addTestMessage(`✅ Получено ${data.total} тестов:`, 'bot');

        let resultsHTML = '<div class="test-results-list"><h4>Доступные тесты:</h4><ul>';

        data.tests.forEach(test => {
            const priorityBadge = this.getPriorityBadge(test.priority);
            const typeBadge = this.getTypeBadge(test.type);

            resultsHTML += `
                <li>
                    <strong>${test.name}</strong> (ID: ${test.id})<br>
                    ${priorityBadge} ${typeBadge}<br>
                    ${test.description}
                </li>
            `;
        });

        resultsHTML += '</ul></div>';

        this.testResults.innerHTML = resultsHTML;
        this.addTestMessage('📊 Результаты отображены ниже', 'bot');
    }

    displayDemoTests() {
        const testExamples = [
            {
                id: 'test_001',
                name: 'Тест проверки соединения',
                description: 'Проверяет установку соединения с API',
                type: 'integration',
                priority: 'high'
            },
            {
                id: 'test_002',
                name: 'Тест загрузки графа',
                description: 'Проверяет корректность загрузки структуры графа',
                type: 'functional',
                priority: 'medium'
            },
            {
                id: 'test_003',
                name: 'Тест валидации действий',
                description: 'Проверяет валидность действий в графе',
                type: 'validation',
                priority: 'high'
            }
        ];

        this.displayAllTests({ tests: testExamples, total: testExamples.length });
        this.addTestMessage('📊 Используются демо-данные', 'bot');
    }

    getPriorityBadge(priority) {
        const badges = {
            'high': '<span class="priority-badge high">🚨 Высокий</span>',
            'medium': '<span class="priority-badge medium">⚠️ Средний</span>',
            'low': '<span class="priority-badge low">ℹ️ Низкий</span>'
        };
        return badges[priority] || '<span class="priority-badge">ℹ️ Не указан</span>';
    }

    getTypeBadge(type) {
        const badges = {
            'functional': '<span class="type-badge functional">🛠️ Функциональный</span>',
            'integration': '<span class="type-badge integration">🔗 Интеграционный</span>',
            'validation': '<span class="type-badge validation">✅ Валидация</span>',
            'data': '<span class="type-badge data">📊 Данные</span>'
        };
        return badges[type] || '<span class="type-badge">❓ Неизвестно</span>';
    }

    getTestsForAction(actionId) {
        this.addTestMessage(`🔍 Поиск тестов для действия "${actionId}"...`, 'bot');
        
        // Вызов API для получения тестов для действия
        fetch(`${this.apiBaseUrl}/api/test-manager/tests/${actionId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.displayActionTests(actionId, data);
            })
            .catch(error => {
                console.error(`❌ Ошибка получения тестов для действия ${actionId}:`, error);
                this.addTestMessage(`❌ Ошибка получения тестов для действия: ${error.message}`, 'bot');
                // Показываем демо-данные в случае ошибки
                this.displayDemoActionTests(actionId);
            });
    }

    displayActionTests(actionId, data) {
        if (!data || !data.tests || data.tests.length === 0) {
            this.addTestMessage(`⚠️ Не найдено тестов для действия "${actionId}"`, 'bot');
            this.displayDemoActionTests(actionId);
            return;
        }

        this.addTestMessage(`✅ Найдено ${data.total} тестов для действия "${actionId}":`, 'bot');

        let resultsHTML = `<div class="test-results-list"><h4>Тесты для действия "${data.action_name || actionId}":</h4><ul>`;

        data.tests.forEach(test => {
            const priorityBadge = this.getPriorityBadge(test.priority);
            const typeBadge = this.getTypeBadge(test.type);

            resultsHTML += `
                <li>
                    <strong>${test.name}</strong> (ID: ${test.id})<br>
                    ${priorityBadge} ${typeBadge}<br>
                    ${test.description}
                </li>
            `;
        });

        resultsHTML += '</ul></div>';

        this.testResults.innerHTML = resultsHTML;
    }

    displayDemoActionTests(actionId) {
        const actionTests = [
            {
                id: `action_test_001_${actionId}`,
                name: 'Тест выполнения действия',
                description: `Проверяет выполнение действия ${actionId}`,
                type: 'functional',
                priority: 'high'
            },
            {
                id: `action_test_002_${actionId}`,
                name: 'Тест валидации параметров',
                description: `Проверяет параметры действия ${actionId}`,
                type: 'validation',
                priority: 'medium'
            }
        ];

        this.displayActionTests(actionId, {
            tests: actionTests,
            total: actionTests.length,
            action_id: actionId,
            action_name: `Действие ${actionId}`
        });
        this.addTestMessage('📊 Используются демо-данные', 'bot');
    }
}

// Инициализация Test Manager при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.TestManager = new TestManager();
    console.log('✅ Test Manager инициализирован');
});