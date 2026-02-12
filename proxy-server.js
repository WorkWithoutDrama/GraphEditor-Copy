#!/usr/bin/env node

/**
 * Улучшенный прокси-сервер:
 * - Обслуживает статические файлы локально
 * - Проксирует только API запросы на API сервер
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PROXY_PORT = 3000;
const API_HOST = '127.0.0.1';

// Читаем порт API из файла с повторными попытками
let API_PORT = null;
let retryCount = 0;
const maxRetries = 10;

function readApiPort() {
    try {
        if (fs.existsSync('api_port.txt')) {
            const apiPortData = fs.readFileSync('api_port.txt', 'utf8');
            const port = parseInt(apiPortData.trim());

            if (port && port > 0 && port < 65536) {
                API_PORT = port;
                console.log(`📡 Прочитан порт API из файла: ${API_PORT}`);
                return true;
            } else {
                console.log(`⚠️  Неверный порт в файле: ${apiPortData}`);
            }
        } else {
            console.log(`📝 Файл api_port.txt не найден, жду... (попытка ${retryCount + 1}/${maxRetries})`);
        }
    } catch (err) {
        console.log(`⚠️  Ошибка чтения api_port.txt: ${err.message}`);
    }

    retryCount++;
    return false;
}

// Пытаемся прочитать порт несколько раз
while (!API_PORT && retryCount < maxRetries) {
    if (readApiPort()) {
        break;
    }
    if (retryCount < maxRetries) {
        require('child_process').execSync('sleep 1');
    }
}

// Если не удалось прочитать, используем умный поиск порта
if (!API_PORT) {
    console.log('🔍 Ищу API на стандартных портах...');
    const portsToTry = [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009];

    for (const port of portsToTry) {
        try {
            require('child_process').execSync(`curl -s http://localhost:${port}/api/health > /dev/null`);
            API_PORT = port;
            console.log(`✅ Найден API на порту: ${API_PORT}`);
            break;
        } catch (err) {
            // Порт не отвечает, пробуем следующий
        }
    }
}

// Если все еще не нашли, используем порт по умолчанию
if (!API_PORT) {
    API_PORT = 5005;
    console.log(`⚠️  Не удалось определить порт API, использую: ${API_PORT}`);
}

console.log(`✅ Прокси сервер запущен на порту ${PROXY_PORT}`);
console.log(`📡 Проксирую API к порту: ${API_PORT}`);

// Создаем прокси-сервер
// Выводим информацию при запуске
console.log(`✅ Прокси сервер запущен на порту ${PROXY_PORT}`);
console.log(`📡 Проксирую API к порту: ${API_PORT}`);
console.log(`🌐 Статические файлы: http://localhost:${PROXY_PORT}/`);
console.log(`🎯 Основной интерфейс: http://localhost:${PROXY_PORT}/proxy-index.html`);
console.log(`🧪 Тестовый интерфейс: http://localhost:${PROXY_PORT}/test-fix.html`);

const server = http.createServer((clientReq, clientRes) => {
    // Настройка CORS
    clientRes.setHeader('Access-Control-Allow-Origin', '*');
    clientRes.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    clientRes.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    
    // Обработка preflight запросов
    if (clientReq.method === 'OPTIONS') {
        clientRes.writeHead(200);
        clientRes.end();
        return;
    }
    
    // Определяем тип запроса
    const url = clientReq.url;
    const isApiRequest = url.startsWith('/api/');
    
    if (isApiRequest) {
        // API запрос - проксируем на API сервер
        proxyToApi(clientReq, clientRes, url);
    } else {
        // Статический файл - обслуживаем локально
        serveStaticFile(clientReq, clientRes, url);
    }
});

/**
 * Проксирует запрос на API сервер
 */
function proxyToApi(clientReq, clientRes, url) {
    // Динамически читаем порт API на каждый запрос
    let currentApiPort = API_PORT;
    try {
        const apiPortData = fs.readFileSync('api_port.txt', 'utf8');
        currentApiPort = parseInt(apiPortData.trim());
    } catch (err) {
        // Используем текущий порт
    }

    console.log(`🔗 Прокси API: ${clientReq.method} ${url} → ${API_HOST}:${currentApiPort}${url}`);

    const options = {
        hostname: API_HOST,
        port: currentApiPort,
        path: url,
        method: clientReq.method,
        headers: clientReq.headers
    };
    
    const proxyReq = http.request(options, (proxyRes) => {
        clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(clientRes, { end: true });
    });
    
    proxyReq.on('error', (err) => {
        console.error(`❌ Ошибка прокси API: ${err.message}`);
        clientRes.writeHead(502, { 'Content-Type': 'text/plain' });
        clientRes.end('Ошибка проксирования API запроса');
    });
    
    clientReq.pipe(proxyReq, { end: true });
}

/**
 * Обслуживает статический файл
 */
function serveStaticFile(clientReq, clientRes, url) {
    // Определяем путь к файлу
    let filePath = '.' + url;
    if (filePath === './' || filePath === './index.html') {
        filePath = './proxy-index.html';
    }
    
    // Проверяем существование файла
    fs.access(filePath, fs.constants.F_OK, (err) => {
        if (err) {
            // Файл не найден
            console.log(`❌ Файл не найден: ${filePath}`);
            
            // Пробуем index.html
            if (url === '/' || url === '/index.html') {
                console.log(`   Пробую proxy-index.html...`);
                serveStaticFile(clientReq, clientRes, '/proxy-index.html');
                return;
            }
            
            clientRes.writeHead(404, { 'Content-Type': 'text/html' });
            clientRes.end(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>404 Not Found</title>
                    <style>
                        body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                        h1 { color: #d32f2f; }
                        a { color: #1976d2; text-decoration: none; }
                        a:hover { text-decoration: underline; }
                    </style>
                </head>
                <body>
                    <h1>404 Not Found</h1>
                    <p>Файл <code>${url}</code> не найден</p>
                    <p><a href="/">Вернуться на главную</a></p>
                </body>
                </html>
            `);
            return;
        }
        
        // Определяем MIME тип
        const ext = path.extname(filePath).toLowerCase();
        let contentType = 'text/html';
        
        const mimeTypes = {
            '.html': 'text/html',
            '.htm': 'text/html',
            '.js': 'text/javascript',
            '.css': 'text/css',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.txt': 'text/plain',
            '.pdf': 'application/pdf'
        };
        
        contentType = mimeTypes[ext] || 'application/octet-stream';
        
        console.log(`📄 Статический файл: ${url} → ${filePath} (${contentType})`);
        
        // Читаем и отправляем файл
        fs.readFile(filePath, (err, content) => {
            if (err) {
                console.error(`❌ Ошибка чтения файла: ${err.message}`);
                clientRes.writeHead(500, { 'Content-Type': 'text/html' });
                clientRes.end('<h1>500 Internal Server Error</h1>');
            } else {
                clientRes.writeHead(200, {
                    'Content-Type': contentType,
                    'Cache-Control': 'no-cache'
                });
                clientRes.end(content, 'utf-8');
            }
        });
    });
}

// Запускаем сервер
server.listen(PROXY_PORT, () => {
    console.log(`✅ Прокси сервер запущен на порту ${PROXY_PORT}`);
    console.log(`📡 Проксирую API к порту: ${API_PORT}`);
    console.log(`🌐 Статические файлы: http://localhost:${PROXY_PORT}/`);
    console.log(`🎯 Основной интерфейс: http://localhost:${PROXY_PORT}/proxy-index.html`);
    console.log(`🧪 Тестовый интерфейс: http://localhost:${PROXY_PORT}/test-fix.html`);
});

// Обработка закрытия
process.on('SIGINT', () => {
    console.log('\n🛑 Останавливаю прокси сервер...');
    server.close();
    process.exit(0);
});

// Обработка ошибок сервера
server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`❌ Порт ${PROXY_PORT} уже занят!`);
        console.log('   Попробуйте другой порт или завершите процесс:');
        console.log(`   lsof -i :${PROXY_PORT} | grep LISTEN`);
        console.log(`   kill -9 <PID>`);
    } else {
        console.error(`❌ Ошибка сервера: ${err.message}`);
    }
    process.exit(1);
});