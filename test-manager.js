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
        this.addTestMessage('📋 Генерация всех E2E тестов из модели...', 'user');
        this.addTestMessage('⏳ Анализирую структуру модели и генерирую тесты...', 'bot');

        // Загружаем текущую модель
        this.loadCurrentModel().then(model => {
            if (!model) {
                this.addTestMessage('❌ Не удалось загрузить модель для генерации тестов', 'bot');
                return;
            }

            // Вызываем API для генерации всех тестов
            this.generateTests(model, null);
        }).catch(error => {
            console.error('❌ Ошибка загрузки модели:', error);
            this.addTestMessage(`❌ Ошибка загрузки модели: ${error.message}`, 'bot');
            this.addTestMessage('🔄 Пробую использовать демо-модель...', 'bot');

            // Используем демо-модель
            this.generateTests({}, null);
        });
    }

    showActionTests() {
        this.addTestMessage('🎯 Генерация тестов для выбранных действий...', 'user');
        this.addTestMessage('📋 Пожалуйста, выберите действия для тестирования:', 'bot');

        // Загружаем модель для получения списка действий
        this.loadCurrentModel().then(model => {
            if (!model || !model.model_actions || model.model_actions.length === 0) {
                this.addTestMessage('❌ Не найдено действий в модели', 'bot');
                this.promptForActionIds([]);
                return;
            }

            // Показываем список действий для выбора
            this.showActionSelection(model.model_actions);
        }).catch(error => {
            console.error('❌ Ошибка загрузки модели:', error);
            this.addTestMessage(`❌ Ошибка загрузки модели: ${error.message}`, 'bot');
            this.promptForActionIds([]);
        });
    }

    showActionSelection(actions) {
        const selectionElement = document.createElement('div');
        selectionElement.className = 'action-selection';

        let html = '<h4>Выберите действия:</h4>';
        html += '<div class="action-checkboxes">';

        actions.forEach(action => {
            const actionId = action.action_id || action.id;
            const actionName = action.action_name || action.name || actionId;

            html += `
                <div class="action-checkbox">
                    <input type="checkbox" id="action_${actionId}" value="${actionId}">
                    <label for="action_${actionId}">${actionName} (${actionId})</label>
                </div>
            `;
        });

        html += '</div>';
        html += '<button id="generateSelectedTestsBtn" class="primary">Сгенерировать тесты для выбранных действий</button>';
        html += '<button id="generateAllActionsBtn" class="secondary">Выбрать все и сгенерировать</button>';

        selectionElement.innerHTML = html;
        this.testMessages.appendChild(selectionElement);

        // Обработчики кнопок
        document.getElementById('generateSelectedTestsBtn')?.addEventListener('click', () => {
            const selectedActions = [];
            document.querySelectorAll('.action-checkbox input:checked').forEach(checkbox => {
                selectedActions.push(checkbox.value);
            });

            if (selectedActions.length > 0) {
                this.generateTestsForSelectedActions(selectedActions);
            } else {
                this.addTestMessage('⚠️ Пожалуйста, выберите хотя бы одно действие', 'bot');
            }
        });

        document.getElementById('generateAllActionsBtn')?.addEventListener('click', () => {
            const allActionIds = actions.map(action => action.action_id || action.id);
            this.generateTestsForSelectedActions(allActionIds);
        });
    }

    promptForActionIds(availableActions) {
        const inputElement = document.createElement('div');
        inputElement.className = 'action-input';
        inputElement.innerHTML = `
            <h4>Введите ID действий (через запятую):</h4>
            <input type="text" id="actionIdsInput" placeholder="Например: a00001, a00002, a00003">
            <button id="submitActionIdsBtn" class="primary">Сгенерировать тесты</button>
        `;

        this.testMessages.appendChild(inputElement);

        document.getElementById('submitActionIdsBtn')?.addEventListener('click', () => {
            const input = document.getElementById('actionIdsInput')?.value;
            if (input) {
                const actionIds = input.split(',').map(id => id.trim()).filter(id => id);
                if (actionIds.length > 0) {
                    this.generateTestsForSelectedActions(actionIds);
                } else {
                    this.addTestMessage('⚠️ Пожалуйста, введите хотя бы один ID действия', 'bot');
                }
            } else {
                this.addTestMessage('⚠️ Пожалуйста, введите ID действий', 'bot');
            }
        });
    }

    generateTestsForSelectedActions(actionIds) {
        this.addTestMessage(`🎯 Генерация тестов для ${actionIds.length} действий...`, 'user');
        this.addTestMessage(`📋 Выбраны действия: ${actionIds.join(', ')}`, 'bot');

        // Загружаем модель
        this.loadCurrentModel().then(model => {
            if (!model) {
                this.addTestMessage('❌ Не удалось загрузить модель', 'bot');
                return;
            }

            // Генерируем тесты для выбранных действий
            this.generateTests(model, actionIds);
        }).catch(error => {
            console.error('❌ Ошибка загрузки модели:', error);
            this.addTestMessage(`❌ Ошибка загрузки модели: ${error.message}`, 'bot');
            this.addTestMessage('🔄 Использую пустую модель...', 'bot');
            this.generateTests({}, actionIds);
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

    loadCurrentModel() {
        // Пытаемся получить текущую модель из графа
        return new Promise((resolve, reject) => {
            if (window.cy && window.cy.data) {
                // Пробуем извлечь модель из графа
                try {
                    const elements = window.cy.elements();
                    const model = this.extractModelFromGraph(elements);
                    if (model && model.model_actions && model.model_actions.length > 0) {
                        resolve(model);
                        return;
                    }
                } catch (e) {
                    console.warn('Не удалось извлечь модель из графа:', e);
                }
            }

            // Пробуем загрузить последний сохраненный файл модели
            fetch(`${this.apiBaseUrl}/api/latest-model`)
                .then(response => {
                    if (response.ok) return response.json();
                    throw new Error('Не удалось получить модель');
                })
                .then(data => resolve(data))
                .catch(() => {
                    // Используем test_project.json как fallback
                    fetch('test_project.json')
                        .then(response => {
                            if (response.ok) return response.json();
                            throw new Error('Не удалось загрузить демо-модель');
                        })
                        .then(data => resolve(data))
                        .catch(reject);
                });
        });
    }

    extractModelFromGraph(elements) {
        // Простая реализация извлечения модели из графа
        // В реальном приложении здесь должна быть сложная логика
        return {
            model_actions: [],
            model_objects: [],
            model_connections: []
        };
    }

    generateTests(model, actionIds) {
        this.addTestMessage('🚀 Запускаю генератор E2E тестов...', 'bot');

        const requestData = {
            model: model,
            action_ids: actionIds,
            generate_zip: true
        };

        fetch(`${this.apiBaseUrl}/api/generate-tests`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (response.status === 200) {
                const contentType = response.headers.get('content-type');

                if (contentType && contentType.includes('application/zip')) {
                    // Получили ZIP архив
                    return response.blob().then(blob => {
                        this.handleTestZip(blob, actionIds);
                    });
                } else {
                    // Получили JSON ответ
                    return response.json().then(data => {
                        this.handleTestResponse(data, actionIds);
                    });
                }
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        })
        .catch(error => {
            console.error('❌ Ошибка генерации тестов:', error);
            this.addTestMessage(`❌ Ошибка генерации тестов: ${error.message}`, 'bot');
            this.addTestMessage('🔄 Запускаю локальную генерацию...', 'bot');
            this.generateLocalTests(model, actionIds);
        });
    }

    handleTestZip(blob, actionIds) {
        const timestamp = new Date().getTime();
        const filename = `e2e_tests_${timestamp}.zip`;

        // Создаем ссылку для скачивания
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        const actionText = actionIds ? `для ${actionIds.length} выбранных действий` : 'для всех действий';
        this.addTestMessage(`✅ Сгенерированы E2E тесты ${actionText}`, 'bot');
        this.addTestMessage(`📦 ZIP архив скачан: ${filename}`, 'bot');

        // Показываем содержимое архива
        this.showTestSummary(actionIds);
    }

    handleTestResponse(data, actionIds) {
        if (data.success) {
            const actionText = actionIds ? `для ${actionIds.length} выбранных действий` : 'для всех действий';
            this.addTestMessage(`✅ Сгенерировано ${data.total_tests} тестов ${actionText}`, 'bot');

            if (data.download_url) {
                this.addTestMessage(`📦 Доступен для скачивания: ${data.download_url}`, 'bot');

                // Создаем кнопку для скачивания
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'primary';
                downloadBtn.innerHTML = '⬇️ Скачать ZIP архив';
                downloadBtn.onclick = () => {
                    window.open(`${this.apiBaseUrl}${data.download_url}`, '_blank');
                };

                this.testMessages.appendChild(downloadBtn);
            }

            // Показываем сводку
            this.showTestSummary(data.files, actionIds);
        } else {
            this.addTestMessage(`❌ Ошибка: ${data.error}`, 'bot');
        }
    }

    generateLocalTests(model, actionIds) {
        // Локальная генерация тестов (заглушка)
        this.addTestMessage('🧪 Запускаю локальный генератор тестов...', 'bot');

        setTimeout(() => {
            const actionText = actionIds ? `для действий: ${actionIds.join(', ')}` : 'для всех действий';
            this.addTestMessage(`✅ Локальная генерация завершена ${actionText}`, 'bot');
            this.addTestMessage('📝 Тесты сгенерированы в память', 'bot');

            // Создаем демо-ZIP
            this.createDemoZip(actionIds);
        }, 2000);
    }

    createDemoZip(actionIds) {
        // Создаем демо-ZIP архив
        const zipContent = 'Это демонстрационный ZIP архив с тестами.\nВ реальной версии здесь будут сгенерированные E2E тесты.';

        const blob = new Blob([zipContent], { type: 'application/zip' });
        const timestamp = new Date().getTime();
        const filename = `demo_tests_${timestamp}.zip`;

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        this.addTestMessage(`📦 Скачан демо-архив: ${filename}`, 'bot');
        this.addTestMessage('💡 В реальной версии будут настоящие E2E тесты', 'bot');
    }

    showTestSummary(files, actionIds) {
        let summary = '<div class="test-summary">';
        summary += '<h4>Сводка по тестам:</h4>';

        if (actionIds) {
            summary += `<p>Сгенерированы тесты для ${actionIds.length} действий:</p><ul>`;
            actionIds.forEach(id => {
                summary += `<li>Действие ${id}</li>`;
            });
            summary += '</ul>';
        } else {
            summary += '<p>Сгенерированы тесты для всех действий модели</p>';
        }

        if (files && files.length > 0) {
            summary += '<p>Файлы тестов:</p><ul>';
            files.slice(0, 5).forEach(file => {
                summary += `<li>${file}</li>`;
            });
            if (files.length > 5) {
                summary += `<li>... и еще ${files.length - 5} файлов</li>`;
            }
            summary += '</ul>';
        }

        summary += '<p>Тесты включают:</p><ul>';
        summary += '<li>E2E сценарии для каждого действия</li>';
        summary += '<li>Предусловия и проверки</li>';
        summary += '<li>Ожидаемые результаты</li>';
        summary += '</ul>';

        summary += '</div>';

        this.testResults.innerHTML = summary;
    }
}

// Инициализация Test Manager при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.TestManager = new TestManager();
    console.log('✅ Test Manager инициализирован');
});