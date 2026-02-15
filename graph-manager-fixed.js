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

    // Базовые методы
    handleFileUpload(file) {
        console.log('handleFileUpload called for:', file.name);
        this.addMessage(`📁 Загружаю файл: ${file.name}`, 'user');
        // Базовая реализация
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
                if (data.status === 'ok') {
                    this.apiAvailable = true;
                    console.log('✅ Прокси доступен! Использую порт: 3000');
                    this.addMessage('✅ API доступен', 'bot');
                } else {
                    console.error('❌ Прокси недоступен');
                }
            })
            .catch(error => {
                console.error('❌ Ошибка проверки API:', error);
            });
    }
}

// Экспорт
window.GraphManager = GraphManager;