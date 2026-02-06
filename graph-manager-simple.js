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
        this.apiBaseUrl = 'http://localhost:3000';
        this.llmProvider = 'ollama';

        // Настройка методов с правильным контекстом
        this.handleFileUpload = this.handleFileUpload.bind(this);
        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.stopResizing = this.stopResizing.bind(this);
        
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
                if (e.offsetX > this.chatContainer.offsetWidth - 10) {
                    this.startResizing(e);
                }
            });
            
            this.chatContainer.addEventListener('dblclick', (e) => {
                if (e.offsetX > this.chatContainer.offsetWidth - 10) {
                    this.resetChatWidth();
                }
            });
        }
    }

    async checkAPIStatus() {
        try {
            const proxyUrl = 'http://localhost:3000/api/health';
            
            console.log(`🔍 Проверяю прокси: ${proxyUrl}`);
            
            const response = await fetch(proxyUrl, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache',
                signal: AbortSignal.timeout(5000)
            });
            
            if (response.ok) {
                this.apiAvailable = true;
                console.log('✅ Прокси и API доступны!');
                
                // Показываем приветственное сообщение
                this.showWelcomeMessage();
                
                return true;
            } else {
                throw new Error(`Прокси отвечает с ошибкой: ${response.status}`);
            }
            
        } catch (error) {
            console.log('❌ Прокси недоступен:', error.message);
            
            // Показываем ошибку подключения
            this.showConnectionError();
            
            this.apiAvailable = false;
            return false;
        }
    }
    
    showConnectionError() {
        if (!this.chatMessages) return;
        
        // Очищаем чат и показываем инструкцию
        this.chatMessages.innerHTML = '';
        
        const errorMessage = "❌ Graph Manager не может подключиться к AI API\n\n📋 **Требуется запуск серверов:**\n\n1. **Запустите AI API сервер**\n   ```bash\n   python api.py\n   ```\n\n2. **Запустите прокси сервер**\n   ```bash\n   node proxy-server.js\n   ```\n\n3. **Обновите страницу** после запуска серверов\n\n🔗 **Или используйте скрипт запуска:**\n   ```bash\n   ./start-full.sh  # macOS/Linux\n   start-full.bat   # Windows\n   ```\n\n📁 **Файлы находятся в:** " + window.location.pathname;
        
        this.addMessage(errorMessage, 'bot');
        
        // Делаем сообщение более заметным
        const lastMessage = this.chatMessages.lastElementChild;
        if (lastMessage) {
            lastMessage.style.backgroundColor = '#fff3cd';
            lastMessage.style.borderLeft = '4px solid #ffc107';
            lastMessage.style.padding = '15px';
            lastMessage.style.fontFamily = 'monospace';
            lastMessage.style.whiteSpace = 'pre-wrap';
        }
        
        // Отключаем кнопки
        if (this.sendMessageBtn) this.sendMessageBtn.disabled = true;
        if (this.uploadFileBtn) this.uploadFileBtn.disabled = true;
        if (this.chatInput) this.chatInput.disabled = true;
    }
    
    showWelcomeMessage() {
        if (!this.chatMessages) return;
        
        const welcomeMessage = "👋 Graph Manager готов к работе!\n\n📝 **Отправьте мне:**\n• Техническое задание\n• Описание системы  \n• Текстовый файл (.txt, .md, .pdf)\n\n💡 **Совет:** Чем детальнее описание, тем точнее будет модель!";
        
        this.addMessage(welcomeMessage, 'bot');
    }

    addMessage(text, sender = 'user') {
        if (!this.chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.textContent = text;
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        this.conversationHistory.push({ sender, text, timestamp: new Date() });
    }

    showChat() {
        if (!this.chatContainer || !this.resizer) return;
        
        // Если API недоступен, показываем ошибку
        if (!this.apiAvailable) {
            this.showConnectionError();
            return;
        }
        
        this.chatContainer.style.display = 'flex';
        this.resizer.style.display = 'block';
        this.isChatVisible = true;
        
        if (this.chatInput) {
            this.chatInput.focus();
        }
        
        // Обновляем layout графа если он есть
        if (window.cy && window.cy.layout) {
            setTimeout(() => {
                window.cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
            }, 100);
        }
    }

    hideChat() {
        if (!this.chatContainer || !this.resizer) return;
        
        this.chatContainer.style.display = 'none';
        this.resizer.style.display = 'none';
        this.isChatVisible = false;
        
        // Обновляем layout графа если он есть
        if (window.cy && window.cy.layout) {
            setTimeout(() => {
                window.cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
            }, 100);
        }
    }

    toggleChat() {
        if (this.isChatVisible) {
            this.hideChat();
        } else {
            this.showChat();
        }
    }

    async sendMessage() {
        // Проверяем доступность API
        if (!this.apiAvailable) {
            this.addMessage("❌ API недоступен. Запустите серверы согласно инструкции выше.", 'bot');
            return;
        }
        
        const text = this.chatInput ? this.chatInput.value.trim() : '';
        if (!text) return;

        this.addMessage(text, 'user');
        if (this.chatInput) {
            this.chatInput.value = '';
        }

        try {
            // Показываем индикатор обработки
            this.addMessage("⏳ Обрабатываю запрос...", 'bot');
            
            const response = await this.generateModelFromText(text);
            
            if (response.success) {
                this.addMessage("✅ Запрос обработан! Создаю графовую модель...", 'bot');
                this.processGraphResponse(response);
                this.addMessage("🎯 Модель создана! Граф загружен в редактор.", 'bot');
            } else {
                this.addMessage(`⚠️ Ошибка: ${response.error || 'Не удалось обработать запрос'}`, 'bot');
            }
            
        } catch (error) {
            this.addMessage(`❌ Ошибка API: ${error.message}`, 'bot');
            console.error('API error:', error);
        }
    }

    async handleFileUpload(file) {
        // Проверяем доступность API
        if (!this.apiAvailable) {
            this.addMessage("❌ API недоступен. Запустите серверы согласно инструкции выше.", 'bot');
            return;
        }
        
        if (!file) return;

        this.addMessage(`📁 Загружаю файл: ${file.name}`, 'user');

        try {
            const text = await this.readFileAsText(file);
            
            this.addMessage(`✅ Файл загружен (${file.size} байт)`, 'bot');
            this.addMessage("⏳ Анализирую содержимое...", 'bot');
            
            const response = await this.generateModelFromText(text.substring(0, 1000));
            
            if (response.success) {
                this.addMessage("✅ Файл проанализирован! Создаю графовую модель...", 'bot');
                this.processGraphResponse(response);
                this.addMessage("🎯 Модель создана! Граф загружен в редактор.", 'bot');
            } else {
                this.addMessage("⚠️ Не удалось создать модель из файла.", 'bot');
            }
            
        } catch (error) {
            let errorMessage = error.message;

            // Улучшенные сообщения об ошибках
            if (errorMessage.includes('JSON')) {
                errorMessage = 'Ошибка формата данных от сервера. Попробуйте еще раз.';
            } else if (errorMessage.includes('Network') || errorMessage.includes('fetch')) {
                errorMessage = 'Проблема с сетью или сервер недоступен.';
            } else if (errorMessage.includes('API недоступен')) {
                errorMessage = 'API сервер недоступен. Убедитесь, что сервер запущен.';
            }

            this.addMessage(`❌ ${errorMessage}`, 'bot');
            console.error('File upload error:', error);
            
            // Показываем подробную ошибку
            this.showMessage(`Подробности ошибки: ${error.message}`, 'error');
            
            // Очищаем граф
            if (window.renderGraph) {
                window.renderGraph({ nodes: [], edges: [] });
            }
        }
    }

    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('Не удалось прочитать файл'));
            reader.readAsText(file);
        });
    }

    async generateModelFromText(text) {
        if (!this.apiAvailable) {
            throw new Error('API недоступен');
        }
        
        try {
            const apiUrl = `${this.apiBaseUrl}/api/generate-model`;
            console.log(`📤 Отправляю запрос к API: ${apiUrl} (Провайдер: ${this.llmProvider})`);
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
                mode: 'cors'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('❌ Ошибка API:', error);
            throw error;
        }
    }

    showMessage(message, type = 'info') {
        if (!this.chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message bot-message ${type}-message`;
        
        let icon = '💡';
        if (type === 'error') icon = '❌';
        if (type === 'warning') icon = '⚠️';
        if (type === 'success') icon = '✅';
        
        messageDiv.textContent = `${icon} ${message}`;
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        if (type === 'error') {
            messageDiv.style.backgroundColor = '#f8d7da';
            messageDiv.style.borderLeft = '4px solid #dc3545';
            messageDiv.style.padding = '12px';
            messageDiv.style.margin = '10px 0';
        } else if (type === 'warning') {
            messageDiv.style.backgroundColor = '#fff3cd';
            messageDiv.style.borderLeft = '4px solid #ffc107';
            messageDiv.style.padding = '12px';
            messageDiv.style.margin = '10px 0';
        }
    }

    processGraphResponse(response) {
        try {
            if (!response || typeof response !== 'object') {
                throw new Error('Некорректный ответ от сервера');
            }

            if (!response.success) {
                throw new Error(response.error || 'Ошибка генерации модели');
            }

            if (!response.model || typeof response.model !== 'object') {
                throw new Error('Модель не сгенерирована или имеет некорректный формат');
            }

            if (!window.renderGraph) {
                console.warn('renderGraph не доступен');
                this.showMessage('Ошибка рендеринга графа: renderGraph не доступен', 'error');
                return;
            }

            const nodes = [];
            const edges = [];
            const ids = new Set();
            
            const addNode = (id, type) => {
                if (!ids.has(id)) {
                    nodes.push({ data: { id, label: id, type } });
                    ids.add(id);
                }
            };
            
            for (const [action, data] of Object.entries(response.model)) {
                addNode(action, 'action');
                
                (data.init_states || []).forEach(state => {
                    addNode(state, 'state');
                    edges.push({ data: { id: `${state}->${action}`, source: state, target: action } });
                });
                
                (data.final_states || []).forEach(state => {
                    addNode(state, 'state');
                    edges.push({ data: { id: `${action}->${state}`, source: action, target: state } });
                });
            }
            
            if (nodes.length === 0) {
                throw new Error('Модель не содержит узлов');
            }
            
            window.renderGraph({ nodes, edges });
            this.showMessage(`✅ Успешно создана модель с ${nodes.length} узлами и ${edges.length} связями`, 'success');

        } catch (error) {
            console.error('❌ Ошибка обработки ответа:', error);
            this.showMessage(`Ошибка обработки модели: ${error.message}`, 'error');
            
            // Не показываем демо-граф, а показываем ошибку
            this.showMessage('Модель не загружена. Пожалуйста, проверьте:\n1. Корректность запроса к LLM\n2. Что LLM возвращает правильный формат модели\n3. Что API сервер работает корректно', 'warning');
            
            // Очищаем граф
            if (window.renderGraph) {
                window.renderGraph({ nodes: [], edges: [] });
            }
        }
    }

    // Остальные методы (resize, clear chat, etc.)
    startResizing(e) {
        this.isResizing = true;
        document.addEventListener('mousemove', this.handleMouseMove);
        document.addEventListener('mouseup', this.stopResizing);
        e.preventDefault();
    }

    handleMouseMove = (e) => {
        if (!this.isResizing || !this.chatContainer) return;
        
        const containerRect = this.chatContainer.getBoundingClientRect();
        const mainContainer = document.querySelector('.main-container');
        if (!mainContainer) return;
        
        const mainRect = mainContainer.getBoundingClientRect();
        let newWidth = mainRect.right - e.clientX;
        newWidth = Math.max(300, Math.min(newWidth, mainRect.width * 0.7));
        this.chatContainer.style.width = newWidth + 'px';
        
        // Обновляем layout графа
        if (window.cy && window.cy.layout) {
            window.cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
        }
    }

    stopResizing = () => {
        this.isResizing = false;
        document.removeEventListener('mousemove', this.handleMouseMove);
        document.removeEventListener('mouseup', this.stopResizing);
    }

    resetChatWidth() {
        if (this.chatContainer) {
            this.chatContainer.style.width = '400px';
        }
        if (window.cy && window.cy.layout) {
            window.cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
        }
    }

    clearChat() {
        if (this.chatMessages && confirm('Очистить историю чата?')) {
            this.chatMessages.innerHTML = '';
            this.conversationHistory = [];
            
            // Если API доступен, показываем приветствие
            if (this.apiAvailable) {
                this.showWelcomeMessage();
            } else {
                this.showConnectionError();
            }
        }
    }

    toggleLLMProvider() {
        // Переключаем между Ollama и DeepSeek
        if (this.llmProvider === 'ollama') {
            this.llmProvider = 'deepseek';
            if (this.llmProviderBtn) {
                this.llmProviderBtn.textContent = '🤖 DeepSeek';
                this.llmProviderBtn.title = 'Текущий провайдер: DeepSeek. Нажмите для переключения на Ollama';
            }
            this.addMessage('Провайдер LLM изменен на DeepSeek', 'bot');
        } else {
            this.llmProvider = 'ollama';
            if (this.llmProviderBtn) {
                this.llmProviderBtn.textContent = '🤖 Ollama';
                this.llmProviderBtn.title = 'Текущий провайдер: Ollama. Нажмите для переключения на DeepSeek';
            }
            this.addMessage('Провайдер LLM изменен на Ollama', 'bot');
        }
    }
}

// Экспорт
window.GraphManager = GraphManager;