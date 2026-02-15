class GraphManager {
    constructor() {
        // Получаем элементы DOM
        this.chatContainer = document.getElementById('chatContainer');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.graphManagerButton = document.getElementById('graphManagerButton');
        this.closeChatBtn = document.getElementById('closeChatBtn');
        this.sendMessageBtn = document.getElementById('sendMessageBtn');
        this.uploadFileBtn = document.getElementById('uploadFileBtn');
        this.fileUpload = document.getElementById('fileUpload');
        this.resizer = document.getElementById('resizer');
        this.clearChatBtn = document.getElementById('clearChatBtn');
        this.llmProviderBtn = document.getElementById('llmProviderBtn');

        // Инициализация состояния
        this.isChatVisible = false;
        this.conversationHistory = [];
        this.isResizing = false;
        this.apiAvailable = false;
        this.apiBaseUrl = 'http://localhost:3000'; // Подключение через прокси
        this.llmProvider = 'ollama';
        this.currentModel = null; // Текущая модель, полученная от API

        // Настройка методов с правильным контекстом
        // Временно убираем bind для неопределенных методов
        // this.handleFileUpload = this.handleFileUpload.bind(this);
        // this.handleMouseMove = this.handleMouseMove.bind(this);
        // this.stopResizing = this.stopResizing.bind(this);
        
        // Настройка
        this.initializeEventListeners();
        this.initializeResizer();
        
        // Проверка API
        this.checkAPIStatus();
    }

    initializeEventListeners() {
        // Основные кнопки
        if (this.graphManagerButton) {
            this.graphManagerButton.addEventListener('click', () => this.toggleChat());
        }
        
        if (this.closeChatBtn) {
            this.closeChatBtn.addEventListener('click', () => this.hideChat());
        }
        
        if (this.sendMessageBtn) {
            this.sendMessageBtn.addEventListener('click', () => this.sendMessage());
        }
        
        if (this.uploadFileBtn) {
            this.uploadFileBtn.addEventListener('click', () => this.fileUpload.click());
        }
        
        if (this.clearChatBtn) {
            this.clearChatBtn.addEventListener('click', () => this.clearChat());
        }

        if (this.llmProviderBtn) {
            this.llmProviderBtn.addEventListener('click', () => this.toggleLLMProvider());
        }

        // Обработка файла
        if (this.fileUpload) {
            this.fileUpload.addEventListener('change', (e) => {
                if (e.target.files[0]) {
                    this.handleFileUpload(e.target.files[0]);
                }
            });
        }
        
        // Отправка по Enter
        if (this.chatInput) {
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // Обработка изменения размера окна
        window.addEventListener('resize', () => {
            if (this.isChatVisible && window.cy && window.cy.layout) {
                setTimeout(() => {
                    window.cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
                }, 100);
            }
        });
    }

    initializeResizer() {
        if (this.resizer) {
            this.resizer.addEventListener('mousedown', (e) => this.startResizing(e));
            this.resizer.addEventListener('dblclick', () => this.resetChatWidth());
        }
        
        if (this.chatContainer) {
            this.chatContainer.addEventListener('mousedown', (e) => {
                // Prevent resizing when clicking inside the chat
                if (e.target === this.chatContainer || this.chatContainer.contains(e.target)) {
                    this.stopResizing();
                }
            });
        }
    }

    toggleChat() {
        console.log('toggleChat called');
        this.isChatVisible = !this.isChatVisible;
        
        if (this.chatContainer) {
            if (this.isChatVisible) {
                this.chatContainer.style.display = 'block';
                this.addMessage('👋 Добро пожаловать в Graph Manager!', 'bot');
                this.addMessage('Вы можете:', 'bot');
                this.addMessage('• Загрузить файл (.txt, .md, .pdf)', 'bot');
                this.addMessage('• Ввести описание системы в чат', 'bot');
                this.addMessage('• Нажать "Отправить" для генерации модели', 'bot');
                console.log('✅ Chat shown');
            } else {
                this.chatContainer.style.display = 'none';
                console.log('✅ Chat hidden');
            }
        } else {
            console.error('❌ Chat container not found');
        }
    }

    hideChat() {
        this.isChatVisible = false;
        if (this.chatContainer) {
            this.chatContainer.style.display = 'none';
        }
    }

    async promptForModelName() {
        return new Promise((resolve) => {
            // Создаем имя модели по умолчанию с датой и временем
            const now = new Date();
            const dateStr = now.toISOString()
                .replace(/T/, '_')
                .replace(/\..+/, '')
                .replace(/:/g, '-');
            const defaultName = `my_model_${dateStr}`;

            const modelName = prompt('📝 Введите имя для модели:', defaultName);
            resolve(modelName);
        });
    }

    // Базовые методы
    async handleFileUpload(file) {
        console.log('handleFileUpload called for:', file.name);
        this.addMessage(`📁 Загружаю файл: ${file.name}`, 'user');

        if (!this.apiAvailable) {
            this.addMessage("❌ API недоступен. Запустите серверы согласно инструкции выше.", 'bot');
            return;
        }

        if (!file) return;

        this.addMessage(`📁 Загружаю файл: ${file.name}`, 'user');

        try {
            const text = await this.readFileAsText(file);

            this.addMessage(`✅ Файл загружен (${text.length} символов)`, 'bot');
            this.addMessage("⏳ Анализирую содержимое...", 'bot');

            // Запрашиваем имя модели у пользователя
            const modelName = await this.promptForModelName();
            if (!modelName) {
                this.addMessage("❌ Отменено: не указано имя модели", 'bot');
                return;
            }

            this.addMessage(`📝 Имя модели: ${modelName}`, 'bot');

            // Разбиваем текст на чанки по 1000 символов
            const chunks = this._splitTextIntoChunks(text, 1000);
            this.addMessage(`📋 Файл разбит на ${chunks.length} частей`, 'bot');

            let allActions = [];
            let allObjects = [];
            let allConnections = [];
            let failedChunks = []; // Массив для необработанных чанков

            // Обрабатываем каждый чанк
            for (let i = 0; i < chunks.length; i++) {
                this.addMessage(`⏳ Обрабатываю часть ${i + 1}/${chunks.length}...`, 'bot');

                const response = await this.generateModelFromText(chunks[i], `${modelName}_part${i + 1}`);

                if (response.success && response.model) {
                    // Собираем результаты из всех чанков
                    if (response.model.model_actions) {
                        allActions = allActions.concat(response.model.model_actions);
                    }
                    if (response.model.model_objects) {
                        allObjects = allObjects.concat(response.model.model_objects);
                    }
                    if (response.model.model_connections) {
                        allConnections = allConnections.concat(response.model.model_connections);
                    }
                    this.addMessage(`✅ Часть ${i + 1} обработана (${response.model.model_actions?.length || 0} действий)`, 'bot');
                } else {
                    this.addMessage(`⚠️ Не удалось обработать часть ${i + 1}`, 'bot');
                    // Сохраняем необработанный чанк
                    failedChunks.push({
                        part: i + 1,
                        content: chunks[i],
                        error: 'API вернул success: false'
                    });
                }
            }

                // Создаем объединенную модель
                if (allActions.length > 0) {
                    const combinedModel = {
                        model_actions: allActions,
                        model_objects: allObjects,
                        model_connections: allConnections
                    };

                    this.addMessage("✅ Все части файла проанализированы! Создаю графовую модель...", 'bot');
                    this.processGraphResponse({ success: true, model: combinedModel });

                    // Сохраняем необработанные чанки в файл
                    if (failedChunks.length > 0) {
                        this.saveFailedChunks(failedChunks, modelName);
                        this.addMessage(`📝 ${failedChunks.length} необработанных частей сохранены в файл ${modelName}_failed_chunks.txt`, 'bot');
                    }

                    this.addMessage(`🎯 Модель "${modelName}" создана! (${allActions.length} действий, ${allObjects.length} объектов, ${allConnections.length} связей, ${failedChunks.length} необработанных частей)`, 'bot');
                } else {
                    this.addMessage("⚠️ Не удалось создать модель из файла.", 'bot');

                    // Сохраняем необработанные чанки в файл
                    if (failedChunks.length > 0) {
                        this.saveFailedChunks(failedChunks, modelName);
                        this.addMessage(`📝 ${failedChunks.length} необработанных частей сохранены в файл ${modelName}_failed_chunks.txt`, 'bot');
                    }
                }

            } catch (error) {
                let errorMessage = error.message;

                // Улучшенные сообщения об ошибках
                if (errorMessage.includes('JSON')) {
                    errorMessage = 'Ошибка формата данных от сервера. Пропускаю эту часть...';
                } else if (errorMessage.includes('Network') || errorMessage.includes('fetch')) {
                    errorMessage = 'Проблема с сетью. Пропускаю эту часть...';
                } else if (errorMessage.includes('API недоступен')) {
                    errorMessage = 'API сервер недоступен. Пропускаю эту часть...';
                } else if (errorMessage.includes('timed out')) {
                    errorMessage = 'Таймаут LLM. Пропускаю эту часть...';
                }

                this.addMessage(`⚠️ ${errorMessage}`, 'bot');
                console.error(`Часть ${i + 1} ошибка:`, error);
                // Продолжаем обработку остальных частей
            }
    }

    handleMouseMove(e) {
        // Базовая реализация
        console.log('handleMouseMove');
    }

    stopResizing() {
        // Базовая реализация
        console.log('stopResizing');
    }

    startResizing(e) {
        console.log('startResizing');
    }

    resetChatWidth() {
        console.log('resetChatWidth');
    }

    sendMessage() {
        const text = this.chatInput ? this.chatInput.value.trim() : '';
        if (text) {
            this.addMessage(text, 'user');
            if (this.chatInput) this.chatInput.value = '';
            this.addMessage('⏳ Обрабатываю запрос...', 'bot');
        }
    }

    clearChat() {
        if (this.chatMessages) {
            this.chatMessages.innerHTML = '';
        }
    }

    toggleLLMProvider() {
        console.log('toggleLLMProvider');
    }

    async generateModelFromText(text, modelName = 'my_model') {
        if (!this.apiAvailable) {
            throw new Error('API недоступен');
        }

        try {
            const apiUrl = `${this.apiBaseUrl}/api/generate-model`;
            console.log(`📤 Отправляю запрос к API: ${apiUrl}`);
            console.log(`📄 Длина текста: ${text.length} символов`);
            console.log(`📝 Текст (первые 200 символов): ${text.substring(0, 200)}...`);
            console.log(`🏷️  Имя модели: ${modelName}`);

            console.log(`⏳ Отправляю запрос к API...`);
            const startTime = Date.now();

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    model_name: modelName
                }),
                mode: 'cors'
            });

            const endTime = Date.now();
            console.log(`✅ Ответ получен за ${endTime - startTime}ms`);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ HTTP ошибка: ${response.status}`, errorText);
                throw new Error(`HTTP error: ${response.status} - ${errorText}`);
            }

            // Проверяем Content-Type
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const errorText = await response.text();
                console.error(`❌ API вернул не JSON: ${errorText.substring(0, 100)}`);
                throw new Error(`API returned non-JSON: ${errorText.substring(0, 100)}`);
            }

            const result = await response.json();

            if (result.success === false) {
                console.error(`❌ Ошибка в ответе API:`, result.error);
                throw new Error(`API error: ${result.error}`);
            }

            console.log(`🎯 Модель получена успешно!`);
            console.log(`📊 Статистика:`);
            console.log(`   • Действий: ${result.model?.model_actions?.length || 0}`);
            console.log(`   • Объектов: ${result.model?.model_objects?.length || 0}`);
            console.log(`   • Связей: ${result.model?.model_connections?.length || 0}`);

            return result;

        } catch (error) {
            console.error('❌ Ошибка при генерации модели:', error);
            throw error;
        }
    }

    _splitTextIntoChunks(text, maxChunkSize = 1000) {
        // Простая реализация для начала
        const chunks = [];

        if (text.length <= maxChunkSize) {
            return [text];
        }

        let start = 0;

        while (start < text.length) {
            let end = start + maxChunkSize;

            if (end >= text.length) {
                chunks.push(text.substring(start));
                break;
            }

            // Ищем хорошее место для разрыва
            let breakPoint = end;

            // Пробуем найти конец предложения или абзаца
            const sentenceEnd = Math.max(
                text.lastIndexOf('. ', end),
                text.lastIndexOf('! ', end),
                text.lastIndexOf('? ', end),
                text.lastIndexOf('\n\n', end),
                text.lastIndexOf('\n', end)
            );

            if (sentenceEnd > start && sentenceEnd > end - 200) {
                if (text.lastIndexOf('\n\n', end) === sentenceEnd) {
                    breakPoint = sentenceEnd + 2;
                } else {
                    breakPoint = sentenceEnd + 1;
                }
            }

            // Если не нашли, разрываем по границе слова
            if (breakPoint === end) {
                const lastSpace = text.lastIndexOf(' ', end);
                if (lastSpace > start && lastSpace > end - 50) {
                    breakPoint = lastSpace + 1;
                }
            }

            const chunk = text.substring(start, breakPoint).trim();
            if (chunk) {
                chunks.push(chunk);
            }

            start = breakPoint;
        }

        console.log(`📋 Разбил текст на ${chunks.length} чанков`);
        return chunks;
    }

    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('Не удалось прочитать файл'));
            reader.readAsText(file);
        });
    }

    addMessage(text, sender = 'user') {
        if (!this.chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.textContent = text;
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    checkAPIStatus() {
        console.log('🔍 Проверяю прокси: http://localhost:3000/api/health');
        fetch('http://localhost:3000/api/health')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok' || data.status === 'healthy') {
                    this.apiAvailable = true;
                    console.log('✅ Прокси доступен! Использую порт: 3000');
                    this.addMessage('✅ API доступен', 'bot');
                } else {
                    console.error('❌ Прокси недоступен (неверный статус)');
                }
            })
            .catch(error => {
                console.error('❌ Ошибка проверки API:', error);
            });
    }

    processGraphResponse(response) {
        try {
            if (!response || typeof response !== 'object') {
                throw new Error('Некорректный ответ от сервера');
            }

            if (response.error) {
                throw new Error(response.error);
            }

            if (!response.success) {
                throw new Error(response.error || 'Ошибка генерации модели');
            }

            if (!response.model || typeof response.model !== 'object') {
                throw new Error('Модель не сгенерирована или имеет некорректный формат');
            }

            const model = response.model;

            // Простая проверка
            if (model.model_actions && model.model_actions.length === 0) {
                this.addMessage('📝 Модель не содержит действий или объектов.', 'info');
                console.log('📝 Модель пустая');
                return;
            }

            console.log('🎯 Модель обработана:');
            console.log(`   Действий: ${model.model_actions?.length || 0}`);
            console.log(`   Объектов: ${model.model_objects?.length || 0}`);
            console.log(`   Связей: ${model.model_connections?.length || 0}`);

            this.addMessage(`✅ Модель успешно обработана! (${model.model_actions?.length || 0} действий)`, 'success');

            // Создаем граф, если функция renderGraph доступна
            if (typeof window.renderGraph === 'function') {
                try {
                    // Преобразуем модель в формат для cytoscape
                    const nodes = [];
                    const edges = [];
                    const nodeIds = new Set();

                    // Добавляем действия как узлы
                    if (model.model_actions) {
                        model.model_actions.forEach(action => {
                            if (action.action_id && action.action_name) {
                                const nodeId = action.action_id;
                                if (!nodeIds.has(nodeId)) {
                                    nodes.push({
                                        data: {
                                            id: nodeId,
                                            label: action.action_name,
                                            type: 'action'
                                        }
                                    });
                                    nodeIds.add(nodeId);
                                }
                            }
                        });
                    }

                    // Добавляем связи
                    if (model.model_connections) {
                        model.model_connections.forEach(conn => {
                            if (conn.connection_out && conn.connection_in) {
                                edges.push({
                                    data: {
                                        id: `${conn.connection_out}->${conn.connection_in}`,
                                        source: conn.connection_out,
                                        target: conn.connection_in
                                    }
                                });
                            }
                        });
                    }

                    // Отображаем граф
                    if (nodes.length > 0) {
                        window.renderGraph({ nodes, edges });
                        console.log('✅ Граф отображен');
                    } else {
                        console.warn('⚠️ Нет узлов для отображения графа');
                    }
                } catch (graphError) {
                    console.error('❌ Ошибка при создании графа:', graphError);
                }
            } else {
                console.warn('⚠️ Функция renderGraph не найдена');
            }

        } catch (error) {
            console.error('❌ Ошибка обработки ответа:', error);
            this.addMessage(`Ошибка обработки модели: ${error.message}`, 'error');
        }
    }

    saveFailedChunks(failedChunks, modelName) {
        if (!failedChunks || failedChunks.length === 0) return;

        // Создаем текстовый файл с необработанными чанками
        let txtContent = `Необработанные части модели: ${modelName}\n`;
        txtContent += `Всего частей: ${failedChunks.length}\n\n`;

        failedChunks.forEach(chunk => {
            txtContent += `=== Часть ${chunk.part} ===\n`;
            txtContent += `Ошибка: ${chunk.error}\n`;
            txtContent += `Содержимое (${chunk.content.length} символов):\n`;
            txtContent += `${chunk.content}\n\n`;
        });

        // Создаем blob и ссылку для скачивания
        const blob = new Blob([txtContent], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${modelName}_failed_chunks.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        console.log(`💾 Сохранены необработанные чанки: ${failedChunks.length} частей`);
    }
}

// Экспорт
window.GraphManager = GraphManager;
