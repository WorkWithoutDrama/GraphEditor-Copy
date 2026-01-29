#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "   🚀 GRAPH EDITOR - БЫСТРЫЙ ЗАПУСК"
echo "========================================"
echo ""

# Очистка
echo "🧹 Очистка..."
pkill -f "python api.py" 2>/dev/null
pkill -f "node simple-proxy" 2>/dev/null
rm -f api_port.txt
sleep 1

# Запускаем API в фоне
echo "🔧 Запускаю AI API..."
python3 api.py &
API_PID=$!

# Ждем 3 секунды
sleep 3

# Проверяем порт
if [ -f "api_port.txt" ]; then
    API_PORT=$(cat api_port.txt)
    echo "   ✅ API на порту: $API_PORT"
else
    echo "   ❌ API не запустился"
    echo "   Пробую порт 5001..."
    # Запускаем на порту 5001
    kill $API_PID 2>/dev/null
    sleep 1
    python3 -c "
import socket
s = socket.socket()
for port in range(5001, 5010):
    try:
        s.bind(('', port))
        s.close()
        with open('api_port.txt', 'w') as f:
            f.write(str(port))
        print(f'Порт {port} свободен')
        break
    except:
        continue
" &
    API_PID=$!
    sleep 2
fi

# Запускаем прокси
echo "🔧 Запускаю прокси..."
node proxy-fixed.js &
PROXY_PID=$!
sleep 2

# Открываем браузер
echo "🌐 Открываю тестовую страницу..."
open "http://localhost:3000"

echo ""
echo "✅ ЗАПУЩЕНО!"
echo ""
echo "🎯 Действия:"
echo "   1. Проверьте тестовую страницу"
echo "   2. Если всё OK, откройте Graph Editor"
echo "   3. Нажмите 'Graph Manager'"
echo ""
echo "🛑 Для остановки: Ctrl+C"
echo ""

cleanup() {
    echo ""
    echo "🛑 Остановка..."
    kill $API_PID $PROXY_PID 2>/dev/null
    rm -f api_port.txt
    echo "✅ Готово"
    exit 0
}
trap cleanup INT TERM

wait