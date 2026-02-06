#!/usr/bin/env node
/**
 * Упрощенный прокси сервер
 */

const http = require('http');
const fs = require('fs');

// Читаем порт API
let API_PORT = 5005;
try {
    const portData = fs.readFileSync('api_port.txt', 'utf8');
    API_PORT = parseInt(portData.trim());
    console.log(`📡 Прочитан порт API: ${API_PORT}`);
} catch (err) {
    console.log(`⚠️  Использую порт по умолчанию: ${API_PORT}`);
}

const PROXY_PORT = 3000;

const server = http.createServer((clientReq, clientRes) => {
    // CORS заголовки
    clientRes.setHeader('Access-Control-Allow-Origin', '*');
    clientRes.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    clientRes.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    // OPTIONS запросы
    if (clientReq.method === 'OPTIONS') {
        clientRes.writeHead(200);
        clientRes.end();
        return;
    }
    
    const url = clientReq.url;
    
    // API запросы проксируем
    if (url.startsWith('/api/')) {
        console.log(`🔗 Прокси API: ${clientReq.method} ${url} → localhost:${API_PORT}${url}`);
        
        const options = {
            hostname: 'localhost',
            port: API_PORT,
            path: url,
            method: clientReq.method,
            headers: clientReq.headers
        };
        
        const proxyReq = http.request(options, (proxyRes) => {
            clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(clientRes);
        });
        
        proxyReq.on('error', (err) => {
            console.error(`❌ Ошибка прокси: ${err.message}`);
            clientRes.writeHead(502, { 'Content-Type': 'text/plain' });
            clientRes.end('Proxy error');
        });
        
        clientReq.pipe(proxyReq);
    } else {
        // Статические файлы
        let filePath = '.' + url;
        if (filePath === './' || filePath === './index.html') {
            filePath = './proxy-index.html';
        }
        
        fs.readFile(filePath, (err, data) => {
            if (err) {
                // Если файл не найден, возвращаем index.html
                fs.readFile('./proxy-index.html', (err2, data2) => {
                    if (err2) {
                        clientRes.writeHead(404);
                        clientRes.end('File not found');
                    } else {
                        clientRes.writeHead(200, { 'Content-Type': 'text/html' });
                        clientRes.end(data2);
                    }
                });
            } else {
                let contentType = 'text/html';
                if (filePath.endsWith('.js')) contentType = 'text/javascript';
                if (filePath.endsWith('.css')) contentType = 'text/css';
                if (filePath.endsWith('.json')) contentType = 'application/json';
                
                clientRes.writeHead(200, { 'Content-Type': contentType });
                clientRes.end(data);
            }
        });
    }
});

server.listen(PROXY_PORT, () => {
    console.log(`✅ Прокси сервер запущен на порту ${PROXY_PORT}`);
    console.log(`📡 Проксирую API к порту: ${API_PORT}`);
    console.log(`🌐 Веб-интерфейс: http://localhost:${PROXY_PORT}`);
});