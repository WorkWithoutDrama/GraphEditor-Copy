#!/usr/bin/env node

/**
 * Простой прокси-сервер без внешних зависимостей
 * Проксирует запросы к AI API серверу
 */

const http = require('http');
const https = require('https');
const url = require('url');

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
    
    console.log(`🔗 Прокси: ${clientReq.method} ${clientReq.url} → ${API_HOST}:${API_PORT}${clientReq.url}`);
    
    // Параметры для запроса к API
    const options = {
        hostname: API_HOST,
        port: API_PORT,
        path: clientReq.url,
        method: clientReq.method,
        headers: clientReq.headers
    };
    
    // Создаем запрос к API
    const proxyReq = http.request(options, (proxyRes) => {
        // Передаем статус и заголовки
        clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
        
        // Передаем данные
        proxyRes.pipe(clientRes, {
            end: true
        });
    });
    
    // Обработка ошибок
    proxyReq.on('error', (err) => {
        console.error(`❌ Ошибка прокси: ${err.message}`);
        clientRes.writeHead(502, { 'Content-Type': 'text/plain' });
        clientRes.end('Ошибка проксирования запроса');
    });
    
    // Передаем тело запроса
    clientReq.pipe(proxyReq, {
        end: true
    });
});

// Запускаем сервер
server.listen(PROXY_PORT, () => {
    console.log(`✅ Прокси сервер запущен на порту ${PROXY_PORT}`);
    console.log(`📡 Проксирую к порту: ${API_PORT}`);
    console.log(`🌐 Откройте: http://localhost:${PROXY_PORT}/proxy-index.html`);
    console.log(`   или: http://localhost:${PROXY_PORT}/test-fix.html`);
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