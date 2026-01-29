#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "   🚀 GRAPH EDITOR - ЗАПУСК"
echo "========================================"
echo ""

# Удаляем старый файл порта
rm -f api_port.txt

# Убиваем наши старые процессы
echo "🧹 Очистка старых процессов..."
pkill -f "python api.py" 2>/dev/null
pkill -f "node simple-proxy" 2>/dev/null
pkill -f "node proxy-server" 2>/dev/null
sleep 1

# Запускаем API
echo "🔧 Запуск AI API..."
python3 api.py &
API_PID=$!

# Ждем создания файла api_port.txt
echo -n "   ⏳ Ожидаю запуска API"
for i in {1..10}; do
    if [ -f "api_port.txt" ]; then
        API_PORT=$(cat api_port.txt 2>/dev/null)
        if [ -n "$API_PORT" ]; then
            echo ""
            echo "   ✅ API запущен на порту $API_PORT"
            break
        fi
    fi
    sleep 1
    echo -n "."
done
echo ""

if [ ! -f "api_port.txt" ]; then
    echo "❌ API не запустился"
    echo "   Порт может быть занят"
    echo "   Попробуйте: ./cleanup.command"
    kill $API_PID 2>/dev/null
    exit 1
fi

API_PORT=$(cat api_port.txt)

# Запускаем прокси
echo "🔧 Запуск прокси..."
node simple-proxy.js &
PROXY_PID=$!
sleep 2

echo "   📡 Проксирует к порту: $API_PORT"

# Открываем браузер
echo "🌐 Открываю Graph Editor..."
open "http://localhost:3000"

echo ""
echo "✅ ГОТОВО!"
echo ""
echo "📊 СЕРВЕРЫ:"
echo "   • AI API:    http://localhost:$API_PORT"
echo "   • Прокси:    http://localhost:3000"
echo "   • Редактор:  http://localhost:3000"
echo ""
echo "🎯 ИСПОЛЬЗОВАНИЕ:"
echo "   1. Откройте Graph Manager в редакторе"
echo "   2. Отправьте описание системы"
echo "   3. AI создаст графовую модель"
echo ""
echo "🛑 ДЛЯ ОСТАНОВКИ: Нажмите Ctrl+C"
echo ""

# Очистка при выходе
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