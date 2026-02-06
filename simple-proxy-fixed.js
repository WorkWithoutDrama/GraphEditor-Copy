const http = require('http');
const PORT = 3000;
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
    // CORS заголовки
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    // OPTIONS запрос (preflight)
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    const url = req.url;
    
    // Проксируем к API
    if (url.startsWith('/api/')) {
        // Читаем порт API из файла
        let apiPort = 5009; // Значение по умолчанию
        try {
            if (fs.existsSync('api_port.txt')) {
                apiPort = parseInt(fs.readFileSync('api_port.txt', 'utf8').trim());
                console.log(`📡 Проксирую к порту: ${apiPort}`);
            } else {
                console.log('⚠️ Файл api_port.txt не найден, использую порт 5009');
            }
        } catch (e) {
            console.log('❌ Не удалось прочитать порт API:', e.message);
            apiPort = 5009;
        }

        const options = {
            hostname: 'localhost',
            port: apiPort,
            path: url,
            method: req.method,
            headers: req.headers
        };
        
        console.log(`🔗 Прокси: ${req.method} ${url} → localhost:${apiPort}${url}`);
        
        const proxyReq = http.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
        });
        
        proxyReq.on('error', (err) => {
            console.error('❌ Ошибка прокси:', err.message);
            res.writeHead(502);
            res.end('Bad Gateway');
        });
        
        req.pipe(proxyReq);
        
    } else {
        // Статичные файлы
        let filePath = '.' + url;
        if (filePath === './') {
            filePath = './proxy-index.html';
        }
        
        const extname = path.extname(filePath);
        let contentType = 'text/html';
        
        switch (extname) {
            case '.js':
                contentType = 'text/javascript';
                break;
            case '.css':
                contentType = 'text/css';
                break;
            case '.json':
                contentType = 'application/json';
                break;
            case '.png':
                contentType = 'image/png';
                break;
            case '.jpg':
                contentType = 'image/jpg';
                break;
        }
        
        fs.readFile(filePath, (error, content) => {
            if (error) {
                if (error.code === 'ENOENT') {
                    res.writeHead(404);
                    res.end('File not found');
                } else {
                    res.writeHead(500);
                    res.end('Server error: ' + error.code);
                }
            } else {
                res.writeHead(200, { 'Content-Type': contentType });
                res.end(content, 'utf-8');
            }
        });
    }
});

server.listen(PORT, () => {
    console.log(`🚀 Прокси сервер запущен на http://localhost:${PORT}`);
    console.log('📡 Ожидание подключения API...');
});