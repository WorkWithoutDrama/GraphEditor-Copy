#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "   🚀 GRAPH EDITOR - УПРОЩЕННЫЙ ЗАПУСК"
echo "========================================"
echo ""

# Проверяем Node.js
if ! command -v node > /dev/null 2>&1; then
    echo "❌ Node.js не установлен"
    echo "Установите Node.js: https://nodejs.org/"
    open "https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js: $(node --version)"

# Проверяем Python
if ! command -v python3 > /dev/null 2>&1; then
    echo "❌ Python 3 не установлен"
    echo "Установите Python 3: https://www.python.org/"
    open "https://www.python.org/"
    exit 1
fi

echo "✅ Python: $(python3 --version)"
echo ""

# Останавливаем старые процессы
echo "🧹 Останавливаю старые процессы..."
pkill -f "python api.py" 2>/dev/null || true
pkill -f "node simple-proxy" 2>/dev/null || true
sleep 2

# Запускаем API
echo "🔧 Запуск AI API..."
python3 api.py &
API_PID=$!
sleep 3

# Проверяем порт API
if [ -f "api_port.txt" ]; then
    API_PORT=$(cat api_port.txt)
    echo "   ✅ API запущен на порту $API_PORT"
else
    echo "   ❌ API не запустился"
    echo "   Пробую альтернативный способ..."
    # Запускаем вручную
    echo "   Откройте новый терминал и запустите:"
    echo "   cd '$PWD' && python3 api.py"
    echo "   Затем в этом окне нажмите Enter..."
    read
fi

# Запускаем прокси
echo "🔧 Запуск прокси..."
node simple-proxy.js &
PROXY_PID=$!
sleep 2

# Проверяем прокси
if kill -0 $PROXY_PID 2>/dev/null; then
    echo "   ✅ Прокси запущен на порту 3000"
else
    echo "   ❌ Прокси не запустился"
    echo "   Пробую альтернативный способ..."
    echo "   Откройте новый терминал и запустите:"
    echo "   cd '$PWD' && node simple-proxy.js"
    echo "   Затем в этом окне нажмите Enter..."
    read
fi

echo ""
echo "🌐 Открываю Graph Editor..."
open "http://localhost:3000/proxy-index.html"

echo ""
echo "✅ СИСТЕМА ЗАПУЩЕНА!"
echo ""
echo "📊 СЕРВЕРЫ:"
echo "   • AI API:    http://localhost:$API_PORT/api/health"
echo "   • Прокси:    http://localhost:3000"
echo "   • Редактор:  http://localhost:3000/proxy-index.html"
echo ""
echo "🎯 ДЕЙСТВИЯ:"
echo "   1. Откройте Graph Editor в браузере"
echo "   2. Нажмите кнопку 'Graph Manager'"
echo "   3. Загрузите файл или введите текст"
echo ""
echo "🛑 ДЛЯ ОСТАНОВКИ:"
echo "   Закройте это окно или нажмите Ctrl+C"
echo ""
echo "🔧 ДЛЯ ПРОВЕРКИ:"
echo "   API здоровье: curl http://localhost:$API_PORT/api/health"
echo "   Прокси работает: curl http://localhost:3000/api/health"
echo ""

# Ждем
wait