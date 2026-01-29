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
            let apiPort = 5001;
            try {
                if (fs.existsSync('api_port.txt')) {
                    apiPort = parseInt(fs.readFileSync('api_port.txt', 'utf8').trim());
                    console.log(`📡 Проксирую к порту: ${apiPort}`);
                } else {
                    console.log('⚠️ Файл api_port.txt не найден, использую порт 5001');
                }
            } catch (e) {
                console.log('❌ Не удалось прочитать порт API:', e.message);
                apiPort = 5001;
            }

            const apiUrl = `http://localhost:${apiPort}${url}`;
        
        const options = {
            hostname: 'localhost',
            port: apiPort,
            path: url,
            method: req.method,
            headers: req.headers
        };
        
        const proxyReq = http.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
        });
        
        proxyReq.on('error', (err) => {
            console.error('Proxy error:', err);
            res.writeHead(500);
            res.end(JSON.stringify({ error: 'Proxy error' }));
        });
        
        req.pipe(proxyReq);
        
    } else if (url === '/' || url === '') {
        // Главная страница - тестовая
        const fs = require('fs');

        try {
            const testPage = fs.readFileSync('test-page.html', 'utf8');
            res.writeHead(200, {
                'Content-Type': 'text/html; charset=UTF-8',
                'Content-Length': Buffer.byteLength(testPage, 'utf8')
            });
            res.end(testPage);
        } catch (e) {
            // Если файла нет, показываем простую страницу
            const html = `<!DOCTYPE html>
            <html>
            <head>
                <title>Graph Editor</title>
                <meta charset="UTF-8">
                <style>
                    body {
                        font-family: -apple-system, sans-serif;
                        padding: 40px;
                        text-align: center;
                        background: #f5f5f5;
                    }
                    .container {
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    h1 { color: #007bff; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚀 Graph Editor</h1>
                    <p>Система запущена!</p>
                    <p>Откройте:</p>
                    <p><a href="/proxy-index.html">Graph Editor</a></p>
                    <p><a href="/test-page.html">Тестовая страница</a></p>
                </div>
            </body>
            </html>`;

            res.writeHead(200, {
                'Content-Type': 'text/html; charset=UTF-8',
                'Content-Length': Buffer.byteLength(html, 'utf8')
            });
            res.end(html);
        }

    } else if (url === '/get-port') {
        // Endpoint для получения порта API
        let apiPort = 5001;
        try {
            if (fs.existsSync('api_port.txt')) {
                apiPort = parseInt(fs.readFileSync('api_port.txt', 'utf8').trim());
            }
        } catch (e) {
            console.log('Ошибка чтения порта:', e.message);
        }

        res.writeHead(200, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        });
        res.end(JSON.stringify({ port: apiPort }));

    } else {
        // Статические файлы
        const filePath = '.' + url;

        fs.readFile(filePath, (err, data) => {
            if (err) {
                res.writeHead(404);
                res.end('Файл не найден: ' + url);
                return;
            }

            let contentType = 'text/html';
            if (filePath.endsWith('.css')) contentType = 'text/css';
            if (filePath.endsWith('.js')) contentType = 'application/javascript';

            res.writeHead(200, { 'Content-Type': contentType });
            res.end(data);
        });
    }
});

server.listen(PORT, () => {
    console.log(`🚀 Прокси сервер запущен на http://localhost:${PORT}`);
    console.log(`📡 Проксирует к http://localhost:5001`);
});