#!/bin/bash

echo "🚀 Запуск Graph Editor в полном режиме"

# Проверяем Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js не установлен"
    echo "Установите Node.js: https://nodejs.org/"
    exit 1
fi

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен"
    exit 1
fi

# Запускаем API сервер
echo "🔧 Запуск AI API сервера..."
python3 api.py &
API_PID=$!
echo "✅ AI API сервер запущен (PID: $API_PID)"

# Даем время API серверу запуститься
sleep 2

# Запускаем прокси сервер
echo "🔧 Запуск прокси сервера..."
node proxy-server.js &
PROXY_PID=$!
echo "✅ Прокси сервер запущен (PID: $PROXY_PID)"

# Даем время прокси запуститься
sleep 2

# Открываем браузер
echo "🌐 Открываю Graph Editor..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "http://localhost:3000/proxy-index.html"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "http://localhost:3000/proxy-index.html"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    start "http://localhost:3000/proxy-index.html"
else
    echo "📋 Откройте в браузере: http://localhost:3000/proxy-index.html"
fi

echo ""
echo "✅ Система запущена!"
echo "📊 Состояние:"
echo "   AI API:    http://localhost:5000/api/health"
echo "   Прокси:    http://localhost:3000"
echo "   Редактор:  http://localhost:3000/proxy-index.html"
echo ""
echo "🛑 Для остановки нажмите Ctrl+C"

# Ожидаем Ctrl+C
trap "echo ''; echo '👋 Остановка системы...'; kill $API_PID $PROXY_PID 2>/dev/null; exit 0" INT

# Бесконечное ожидание
while true; do
    sleep 1
done