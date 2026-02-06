#!/bin/bash

echo "🔧 ФИНАЛЬНАЯ ПРОВЕРКА НАСТРОЙКИ"
echo "================================"

# 1. Проверка файлов
echo ""
echo "1. Проверка необходимых файлов:"
required_files=("api.py" "proxy-server.js" "proxy-index.html" "graph-manager.js" "script.js" "test-fix.html")
all_ok=true

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file - ОТСУТСТВУЕТ"
        all_ok=false
    fi
done

if [ "$all_ok" = false ]; then
    echo ""
    echo "❌ Отсутствуют необходимые файлы!"
    exit 1
fi

# 2. Проверка API
echo ""
echo "2. Проверка API сервера:"
if curl -s http://localhost:5009/api/health > /dev/null 2>&1; then
    echo "   ✅ API сервер работает на порту 5009"
    API_WORKING=true
else
    echo "   ⚠️  API сервер не запущен"
    echo "   Запустите: python api.py"
    API_WORKING=false
fi

# 3. Проверка порта 3000
echo ""
echo "3. Проверка порта 3000:"
if lsof -i :3000 > /dev/null 2>&1; then
    echo "   ⚠️  Порт 3000 занят"
    echo "   Остановите текущий прокси: pkill -f 'node proxy-server'"
else
    echo "   ✅ Порт 3000 свободен"
fi

# 4. Инструкция
echo ""
echo "================================"
echo "🎯 ИНСТРУКЦИЯ ПО ЗАПУСКУ:"
echo ""
if [ "$API_WORKING" = true ]; then
    echo "1. API сервер уже работает ✅"
else
    echo "1. Запустите API сервер:"
    echo "   python api.py"
fi
echo ""
echo "2. Запустите прокси-сервер:"
echo "   node proxy-server.js"
echo ""
echo "3. Откройте в браузере:"
echo "   http://localhost:3000/proxy-index.html"
echo ""
echo "4. Альтернативно, запустите всё одной командой:"
echo "   ./launch.command"
echo ""
echo "📝 ПРИМЕЧАНИЕ:"
echo "Если Node.js не найден, установите его: https://nodejs.org/"
echo "Или используйте уже установленный:"
echo "   /usr/local/bin/node proxy-server.js"
echo "   /opt/homebrew/bin/node proxy-server.js"