#!/bin/bash
# Финальный скрипт запуска системы

echo "🚀 ЗАПУСК СИСТЕМЫ GRAPH EDITOR"
echo "================================"

# Останавливаем старые процессы
echo "🔧 Остановка старых процессов..."
pkill -f "python.*api" 2>/dev/null
pkill -f "node.*proxy" 2>/dev/null
sleep 1

# Удаляем старый файл порта
rm -f api_port.txt

# Запускаем API
echo "🚀 Запуск API..."
python3 api_simple_final.py > api.log 2>&1 &
API_PID=$!
echo "✅ API запущен (PID: $API_PID)"

# Ждем, пока API создаст файл с портом
echo "⏳ Ожидание запуска API..."
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
    echo "📋 Лог API:"
    cat api.log
    kill $API_PID 2>/dev/null
    exit 1
fi

# Проверяем, что API отвечает
echo "🔧 Проверка API..."
if curl -s http://localhost:$API_PORT/api/health > /dev/null; then
    echo "✅ API работает"
else
    echo "❌ API не отвечает"
    kill $API_PID 2>/dev/null
    exit 1
fi

# Запускаем прокси
echo "🚀 Запуск прокси..."

# Находим node
NODE_PATH=""
if [ -x "/opt/homebrew/bin/node" ]; then
    NODE_PATH="/opt/homebrew/bin/node"
elif [ -x "/usr/local/bin/node" ]; then
    NODE_PATH="/usr/local/bin/node"
else
    NODE_PATH="node"
fi

echo "🔧 Использую Node.js: $NODE_PATH"

$NODE_PATH proxy-server.js > proxy.log 2>&1 &
PROXY_PID=$!
echo "✅ Прокси запущен (PID: $PROXY_PID)"

# Ждем запуска прокси
echo "⏳ Ожидание запуска прокси..."
sleep 2

# Проверяем прокси
echo "🔧 Проверка прокси..."
sleep 1

# Определяем порт прокси из лога
PROXY_PORT="3000"
if [ -f "proxy.log" ]; then
    PORT_LINE=$(grep "Прокси сервер запущен на порту" proxy.log | head -1)
    if [[ $PORT_LINE =~ порту[[:space:]]+([0-9]+) ]]; then
        PROXY_PORT="${BASH_REMATCH[1]}"
    fi
fi

echo "✅ Прокси порт: $PROXY_PORT"

echo ""
echo "🎉 СИСТЕМА ЗАПУЩЕНА!"
echo "================================"
echo "🌐 Веб-интерфейс: http://localhost:$PROXY_PORT"
echo "🔧 API: http://localhost:$API_PORT"
echo ""
echo "📋 ЭНДПОИНТЫ:"
echo "   • Веб-интерфейс: http://localhost:$PROXY_PORT"
echo "   • API здоровье: http://localhost:$API_PORT/api/health"
echo "   • API генерация: http://localhost:$API_PORT/api/generate-model"
echo ""
echo "📁 ЛОГИ:"
echo "   • API: tail -f api.log"
echo "   • Прокси: tail -f proxy.log"
echo ""
echo "🛑 Для остановки выполните:"
echo "   kill $API_PID $PROXY_PID"
echo ""
echo "💡 PIDs сохранены в .system_pids"
echo "$API_PID $PROXY_PID" > .system_pids

# Ждем завершения
wait