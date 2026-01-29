#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "   🚀 GRAPH EDITOR - ЗАПУСК"
echo "========================================"
echo ""

# Очистка
echo "🧹 Очистка..."
pkill -f "python api.py" 2>/dev/null
pkill -f "node proxy" 2>/dev/null
rm -f api_port.txt
sleep 1

# Проверяем Node.js
if ! command -v node > /dev/null; then
    echo "❌ Установите Node.js: https://nodejs.org/"
    open "https://nodejs.org/"
    exit 1
fi

# Проверяем Python
if ! command -v python3 > /dev/null; then
    echo "❌ Установите Python 3: https://python.org/"
    open "https://python.org/"
    exit 1
fi

echo "✅ Зависимости установлены"
echo ""

# Запускаем API
echo "🔧 Запуск AI API..."
python3 api.py &
API_PID=$!

# Ждем 5 секунд
sleep 5

# Проверяем API
if [ -f "api_port.txt" ]; then
    API_PORT=$(cat api_port.txt)
    echo "   ✅ API запущен на порту $API_PORT"
else
    echo "   ❌ API не запустился"
    echo "   Пробую альтернативный способ..."
    # Просто показываем что делать
    echo "   Откройте новый терминал и запустите:"
    echo "   python3 api.py"
    echo "   Затем обновите эту страницу"
    API_PORT="?"
fi

# Запускаем простой прокси
echo "🔧 Запуск простого прокси..."
node -e "
const http = require('http');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    const url = req.url === '/' ? '/proxy-index.html' : req.url;
    const filePath = '.' + url;
    
    fs.readFile(filePath, (err, data) => {
        if (err) {
            // Если файл не найден, показываем индекс
            if (req.url === '/') {
                res.writeHead(200, {'Content-Type': 'text/html'});
                res.end('<h1>Graph Editor</h1><p><a href=\"/proxy-index.html\">Открыть</a></p>');
            } else {
                res.writeHead(404);
                res.end('Not found: ' + url);
            }
        } else {
            let contentType = 'text/html';
            if (filePath.endsWith('.css')) contentType = 'text/css';
            if (filePath.endsWith('.js')) contentType = 'application/javascript';
            if (filePath.endsWith('.png')) contentType = 'image/png';
            
            res.writeHead(200, {'Content-Type': contentType});
            res.end(data);
        }
    });
});

server.listen(3000, () => {
    console.log('✅ Прокси запущен на http://localhost:3000');
    console.log('📂 Откройте Graph Editor в браузере');
});
" &
PROXY_PID=$!

sleep 2

# Открываем браузер
echo "🌐 Открываю Graph Editor..."
open "http://localhost:3000"

echo ""
echo "✅ ГОТОВО!"
echo ""
echo "📊 Серверы:"
[ -f "api_port.txt" ] && echo "   • AI API:    порт $(cat api_port.txt)"
echo "   • Прокси:    порт 3000"
echo ""
echo "🎯 Откройте Graph Editor в браузере"
echo "   и нажмите 'Graph Manager'"
echo ""
echo "🛑 Для остановки: Ctrl+C"
echo ""

# Очистка
cleanup() {
    echo ""
    echo "🛑 Остановка..."
    kill $API_PID $PROXY_PID 2>/dev/null
    rm -f api_port.txt
    echo "✅ Готово"
    exit 0
}
trap cleanup INT TERM

# Ждем
wait