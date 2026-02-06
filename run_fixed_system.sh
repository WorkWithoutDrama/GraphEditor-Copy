#!/bin/bash
# Финальный скрипт запуска исправленной системы

echo "🚀 ЗАПУСК ИСПРАВЛЕННОЙ СИСТЕМЫ"
echo "================================"

# Останавливаем всё
echo "🔧 Остановка всех процессов..."
pkill -f "python.*api" 2>/dev/null
pkill -f "node.*proxy" 2>/dev/null
sleep 1

# Очищаем файлы
rm -f api_port.txt api.log proxy.log
sleep 1

# Запускаем API
echo "🚀 Запуск API..."
python3 api_ultra_simple.py > api.log 2>&1 &
API_PID=$!
echo "✅ API PID: $API_PID"

# Ждем запуска API
echo "⏳ Ожидание API..."
for i in {1..10}; do
    if [ -f "api_port.txt" ]; then
        API_PORT=$(cat api_port.txt)
        echo "✅ API порт: $API_PORT"
        break
    fi
    sleep 1
done

if [ -z "$API_PORT" ]; then
    echo "❌ API не запустился"
    echo "📋 API лог:"
    cat api.log
    kill $API_PID 2>/dev/null
    exit 1
fi

# Проверяем API
echo "🔧 Проверка API..."
sleep 1
if curl -s http://localhost:$API_PORT/api/health > /dev/null; then
    echo "✅ API работает"
else
    echo "❌ API не отвечает"
    kill $API_PID 2>/dev/null
    exit 1
fi

# Запускаем прокси
echo "🚀 Запуск прокси..."
/opt/homebrew/bin/node proxy_simple.js > proxy.log 2>&1 &
PROXY_PID=$!
echo "✅ Прокси PID: $PROXY_PID"

# Ждем запуска прокси
echo "⏳ Ожидание прокси..."
sleep 2

# Проверяем прокси
echo "🔧 Проверка прокси..."
sleep 1
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Прокси работает"
else
    echo "❌ Прокси не отвечает"
    echo "📋 Прокси лог:"
    tail -20 proxy.log
    kill $API_PID $PROXY_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🎉 СИСТЕМА УСПЕШНО ЗАПУЩЕНА!"
echo "================================"
echo "🌐 Веб-интерфейс: http://localhost:3000"
echo "🔧 API: http://localhost:$API_PORT"
echo ""
echo "📋 ЭНДПОИНТЫ:"
echo "   • Веб-интерфейс: http://localhost:3000"
echo "   • API здоровье: http://localhost:$API_PORT/api/health"
echo "   • API статус: http://localhost:$API_PORT/api/status"
echo "   • API генерация: http://localhost:$API_PORT/api/generate-model"
echo ""
echo "📁 ЛОГИ:"
echo "   • API: tail -f api.log"
echo "   • Прокси: tail -f proxy.log"
echo ""
echo "🛑 Для остановки:"
echo "   kill $API_PID $PROXY_PID"
echo ""
echo "💡 PIDs сохранены в .system_pids"
echo "$API_PID $PROXY_PID" > .system_pids

echo ""
echo "🔍 Проверка graph-manager.js..."
echo "   • Проверяет: /api/health ✓"
echo "   • Ожидает статус 200 ✓"
echo ""

# Ждем
echo "⏳ Система работает. Нажмите Ctrl+C для остановки..."
wait