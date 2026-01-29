#!/bin/bash

# Переходим в директорию скрипта
cd "$(dirname "$0")"

echo "🚀 Запуск Graph Editor"
echo "======================"

# Очистка при выходе
cleanup() {
    echo ""
    echo "🛑 Останавливаю серверы..."
    kill $API_PID $PROXY_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# Запускаем API
echo "🔧 Запускаю AI API..."
python3 api.py &
API_PID=$!
echo "   PID: $API_PID"

# Ждем
sleep 2

# Запускаем прокси
echo "🔧 Запускаю прокси..."
node proxy-server.js &
PROXY_PID=$!
echo "   PID: $PROXY_PID"

# Ждем
sleep 2

# Открываем браузер
echo "🌐 Открываю редактор..."
open "http://localhost:3000/proxy-index.html"

echo ""
echo "✅ Готово!"
echo "📊 Серверы:"
echo "   • AI API:    http://localhost:5000"
echo "   • Прокси:    http://localhost:3000"
echo "   • Редактор:  http://localhost:3000/proxy-index.html"
echo ""
echo "🛑 Для остановки нажмите Ctrl+C"

# Ожидание
wait