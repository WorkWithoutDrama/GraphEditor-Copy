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
const API_PORT = 5009;
const API_HOST = 'localhost';

// Создаем прокси-сервер
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
    console.log(`🔗 Прокси API: ${clientReq.method} ${url} → ${API_HOST}:${API_PORT}${url}`);
    
    const options = {
        hostname: API_HOST,
        port: API_PORT,
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