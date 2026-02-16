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
        fetch(`${this.apiBaseUrl}/health`)
            .then(response => {
                this.apiAvailable = response.ok;
                if (this.apiAvailable) {
                    console.log('✅ Test Manager API доступен');
                } else {
                    console.error('❌ Test Manager API недоступен');
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
        
        // Здесь будет вызов API для получения всех тестов
        // Пока что используем заглушку
        setTimeout(() => {
            this.displayAllTests();
        }, 1000);
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

    displayAllTests() {
        // Заглушка для демонстрации
        this.addTestMessage('✅ Получен список всех тестов:', 'bot');
        
        const testExamples = [
            { id: 'test_001', name: 'Тест проверки соединения', description: 'Проверяет установку соединения с API' },
            { id: 'test_002', name: 'Тест загрузки графа', description: 'Проверяет корректность загрузки структуры графа' },
            { id: 'test_003', name: 'Тест валидации действий', description: 'Проверяет валидность действий в графе' },
            { id: 'test_004', name: 'Тест целостности данных', description: 'Проверяет целостность данных модели' }
        ];
        
        let resultsHTML = '<div class="test-results-list"><h4>Доступные тесты:</h4><ul>';
        
        testExamples.forEach(test => {
            resultsHTML += `
                <li>
                    <strong>${test.name}</strong> (ID: ${test.id})<br>
                    ${test.description}
                </li>
            `;
        });
        
        resultsHTML += '</ul></div>';
        
        this.testResults.innerHTML = resultsHTML;
        this.addTestMessage('📊 Результаты отображены ниже', 'bot');
    }

    getTestsForAction(actionId) {
        this.addTestMessage(`🔍 Поиск тестов для действия "${actionId}"...`, 'bot');
        
        // Заглушка для демонстрации
        setTimeout(() => {
            const actionTests = [
                { id: 'action_test_001', name: 'Тест выполнения действия', description: `Проверяет выполнение действия ${actionId}` },
                { id: 'action_test_002', name: 'Тест валидации параметров', description: `Проверяет параметры действия ${actionId}` },
                { id: 'action_test_003', name: 'Тест результата действия', description: `Проверяет результат выполнения действия ${actionId}` }
            ];
            
            let resultsHTML = `<div class="test-results-list"><h4>Тесты для действия "${actionId}":</h4><ul>`;
            
            actionTests.forEach(test => {
                resultsHTML += `
                    <li>
                        <strong>${test.name}</strong> (ID: ${test.id})<br>
                        ${test.description}
                    </li>
                `;
            });
            
            resultsHTML += '</ul></div>';
            
            this.testResults.innerHTML = resultsHTML;
            this.addTestMessage(`✅ Найдено ${actionTests.length} тестов для действия "${actionId}"`, 'bot');
        }, 1500);
    }
}

// Инициализация Test Manager при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.TestManager = new TestManager();
    console.log('✅ Test Manager инициализирован');
});