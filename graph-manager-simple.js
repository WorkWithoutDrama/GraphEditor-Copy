class GraphManager {
    constructor() {
        console.log('GraphManager created');

        // Получаем элементы DOM
        this.graphManagerButton = document.getElementById('graphManagerButton');
        this.chatContainer = document.getElementById('chatContainer');

        this.apiAvailable = false;
        this.apiBaseUrl = 'http://localhost:3000';
        this.isChatVisible = false;

        this.initializeEventListeners();
        this.checkAPIStatus();
    }

    initializeEventListeners() {
        // Основные кнопки
        if (this.graphManagerButton) {
            this.graphManagerButton.addEventListener('click', () => this.toggleChat());
            console.log('✅ Graph Manager button event listener added');
        } else {
            console.error('❌ Graph Manager button not found');
        }
    }

    toggleChat() {
        console.log('toggleChat called');
        this.isChatVisible = !this.isChatVisible;

        if (this.chatContainer) {
            if (this.isChatVisible) {
                this.chatContainer.style.display = 'block';
                console.log('✅ Chat shown');
            } else {
                this.chatContainer.style.display = 'none';
                console.log('✅ Chat hidden');
            }
        } else {
            console.error('❌ Chat container not found');
        }
    }

    checkAPIStatus() {
        console.log('Checking API status...');
        // Простая проверка
        this.apiAvailable = true;
    }

    async promptForModelName() {
        return new Promise((resolve) => {
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

    _splitTextIntoChunks(text, maxChunkSize = 1000) {
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
            
            let breakPoint = end;
            
            const doubleNewline = text.lastIndexOf('\n\n', end);
            if (doubleNewline > start && doubleNewline > end - 200) {
                breakPoint = doubleNewline + 2;
            } else {
                const sentenceEnd = Math.max(
                    text.lastIndexOf('. ', end),
                    text.lastIndexOf('! ', end),
                    text.lastIndexOf('? ', end),
                    text.lastIndexOf('\n', end)
                );
                
                if (sentenceEnd > start && sentenceEnd > end - 100) {
                    breakPoint = sentenceEnd + 1;
                }
            }
            
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

    async handleFileUpload(file) {
        console.log(`📁 Загружаю файл: ${file.name}`);
        
        try {
            const text = await this.readFileAsText(file);
            console.log(`✅ Файл загружен (${text.length} символов)`);
            
            const modelName = await this.promptForModelName();
            if (!modelName) {
                console.log('❌ Отменено: не указано имя модели');
                return;
            }
            
            console.log(`📝 Имя модели: ${modelName}`);
            
            const chunks = this._splitTextIntoChunks(text, 1000);
            console.log(`📋 Файл разбит на ${chunks.length} частей`);
            
            // Простая обработка - берем только первую часть для теста
            if (chunks.length > 0) {
                console.log(`⏳ Обрабатываю первую часть (${chunks[0].length} символов)...`);
                // Здесь будет вызов API
            }
            
        } catch (error) {
            console.error('❌ Ошибка загрузки файла:', error);
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
}

// Экспорт
window.GraphManager = GraphManager;