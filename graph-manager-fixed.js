// Исправленная версия graph-manager.js с правильным определением порта

// ... (остальной код остается таким же) ...

async checkAPIStatus() {
    try {
        // Пробуем разные порты API напрямую
        const portsToTry = [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010];
        
        let apiUrl = null;
        let foundPort = null;
        
        for (const port of portsToTry) {
            const testUrl = `http://localhost:${port}/api/health`;
            console.log(`🔍 Проверяю: ${testUrl}`);
            
            try {
                const response = await fetch(testUrl, {
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-cache',
                    signal: AbortSignal.timeout(2000)
                });
                
                if (response.ok) {
                    apiUrl = testUrl;
                    foundPort = port;
                    console.log(`✅ Найден работающий API: ${testUrl}`);
                    
                    // ОБНОВЛЯЕМ apiBaseUrl сразу после нахождения порта
                    this.apiBaseUrl = `http://localhost:${port}`;
                    console.log(`🔧 Обновлен apiBaseUrl: ${this.apiBaseUrl}`);
                    break;
                }
            } catch (e) {
                // Порт не отвечает, пробуем следующий
                console.log(`   ❌ ${testUrl} не отвечает`);
            }
        }
        
        if (!apiUrl) {
            throw new Error('Не найден работающий API сервер');
        }
        
        // Проверяем прокси
        console.log(`🔍 Проверяю прокси: ${apiUrl}`);
        
        const response = await fetch(apiUrl, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            signal: AbortSignal.timeout(5000)
        });
        
        if (response.ok) {
            this.apiAvailable = true;
            console.log(`✅ Прокси и API доступны! Использую порт: ${foundPort}`);
            
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

// ... (остальной код остается таким же) ...

async generateModelFromText(text) {
    if (!this.apiAvailable) {
        throw new Error('API недоступен');
    }
    
    try {
        // ИСПОЛЬЗУЕМ ТЕКУЩИЙ apiBaseUrl (уже обновленный)
        const apiUrl = `${this.apiBaseUrl}/api/generate-model`;
        console.log(`📤 Отправляю запрос к API: ${apiUrl} (Провайдер: ${this.llmProvider})`);
        console.log(`🔧 Текущий apiBaseUrl: ${this.apiBaseUrl}`);
        
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