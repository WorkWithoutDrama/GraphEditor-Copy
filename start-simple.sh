#!/bin/bash

echo "🚀 Запуск Graph Editor (ТОЛЬКО полный режим)"
echo "=============================================="

# Проверяем Node.js
if ! command -v node &> /dev/null; then
    echo "❌ ТРЕБУЕТСЯ: Node.js не установлен"
    echo "   Установите: https://nodejs.org/"
    exit 1
fi

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ ТРЕБУЕТСЯ: Python 3 не установлен"
    exit 1
fi

echo ""
echo "📋 ИНСТРУКЦИЯ:"
echo "1. Запустите AI API сервер в ТЕРМИНАЛЕ 1:"
echo "   python api.py"
echo ""
echo "2. Запустите прокси сервер в ТЕРМИНАЛЕ 2:"
echo "   node proxy-server.js"
echo ""
echo "3. Откройте в браузере:"
echo "   http://localhost:3000/proxy-index.html"
echo ""
echo "🔗 ИЛИ используйте автоматический запуск:"
echo "   ./start-full.sh"
echo ""
echo "⏳ Ожидаю запуска серверов..."
echo "   (проверяю каждые 5 секунд)"

# Проверяем доступность серверов
while true; do
    echo -n "."
    
    # Проверяем прокси
    if curl -s http://localhost:3000 > /dev/null; then
        echo ""
        echo ""
        echo "✅ Прокси сервер запущен!"
        
        # Проверяем API
        if curl -s http://localhost:5000/api/health > /dev/null; then
            echo "✅ AI API сервер запущен!"
            echo ""
            echo "🌐 ОТКРОЙТЕ В БРАУЗЕРЕ:"
            echo "   http://localhost:3000/proxy-index.html"
            echo ""
            
            # Открываем браузер
            if [[ "$OSTYPE" == "darwin"* ]]; then
                open "http://localhost:3000/proxy-index.html"
            elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
                xdg-open "http://localhost:3000/proxy-index.html"
            fi
            
            exit 0
        fi
    fi
    
    sleep 5
done