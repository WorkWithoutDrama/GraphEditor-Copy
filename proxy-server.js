const http = require('http');
const https = require('https');
const url = require('url');
const { StringDecoder } = require('string_decoder');

const PORT = 3000;

// Создаем HTTP сервер
const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const path = parsedUrl.pathname;
    const trimmedPath = path.replace(/^\/+|\/+$/g, '');
    
    // CORS заголовки
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    
    // Обработка OPTIONS запроса (preflight)
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    // Проксируем запросы к API
    if (trimmedPath === 'api/generate-model' || trimmedPath === 'api/health') {
        const targetUrl = `http://localhost:5000/${trimmedPath}`;
        
        // Собираем тело запроса
        const decoder = new StringDecoder('utf-8');
        let buffer = '';
        
        req.on('data', (data) => {
            buffer += decoder.write(data);
        });
        
        req.on('end', () => {
            buffer += decoder.end();
            
            // Опции для прокси запроса
            const options = {
                hostname: 'localhost',
                port: 5000,
                path: `/${trimmedPath}`,
                method: req.method,
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(buffer)
                }
            };
            
            // Выполняем прокси запрос
            const proxyReq = http.request(options, (proxyRes) => {
                res.writeHead(proxyRes.statusCode, proxyRes.headers);
                proxyRes.pipe(res);
            });
            
            proxyReq.on('error', (err) => {
                console.error('Proxy error:', err);
                res.writeHead(500);
                res.end(JSON.stringify({ error: 'Proxy error', message: err.message }));
            });
            
            // Отправляем тело запроса
            proxyReq.write(buffer);
            proxyReq.end();
        });
        
    } else {
        // Статические файлы
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Graph Editor Proxy</title>
                <style>
                    body { font-family: sans-serif; padding: 20px; }
                    .success { color: green; }
                </style>
            </head>
            <body>
                <h1>📡 Proxy Server Running</h1>
                <p class="success">✅ Proxy server is running on port ${PORT}</p>
                <p>API endpoints:</p>
                <ul>
                    <li><code>GET /api/health</code> - Health check</li>
                    <li><code>POST /api/generate-model</code> - Generate model</li>
                </ul>
                <p>Open <a href="http://localhost:${PORT}/editor">Graph Editor</a></p>
            </body>
            </html>
        `);
    }
});

// Запускаем сервер
server.listen(PORT, () => {
    console.log(`🚀 Proxy server running on http://localhost:${PORT}`);
    console.log(`🔗 Open http://localhost:${PORT}/editor to use Graph Editor`);
    console.log(`📡 Proxying API requests to http://localhost:5000`);
});