#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "   🚀 GRAPH EDITOR - ЗАПУСК С ЛОГАМИ"
echo "========================================"
echo ""

# Проверяем Node.js (проверяем несколько вариантов)
NODE_CMD=""
if command -v node > /dev/null 2>&1; then
    NODE_CMD="node"
elif command -v nodejs > /dev/null 2>&1; then
    NODE_CMD="nodejs"
elif [ -f "/usr/local/bin/node" ]; then
    NODE_CMD="/usr/local/bin/node"
elif [ -f "/opt/homebrew/bin/node" ]; then
    NODE_CMD="/opt/homebrew/bin/node"
fi

if [ -z "$NODE_CMD" ]; then
    echo "❌ Node.js не установлен"
    echo "Установите Node.js: https://nodejs.org/"
    open "https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js: $($NODE_CMD --version)"

# Проверяем Python
if ! command -v python3 > /dev/null 2>&1; then
    echo "❌ Python 3 не установлен"
    echo "Установите Python 3: https://www.python.org/"
    open "https://www.python.org/"
    exit 1
fi

echo "✅ Python: $(python3 --version)"

# Останавливаем старые процессы
echo "🛑 Останавливаю старые процессы..."
pkill -f "python.*api_simple_with_cors" 2>/dev/null || true
pkill -f "node proxy-server" 2>/dev/null || true
pkill -f "node proxy-server-fixed" 2>/dev/null || true
sleep 2

# Запускаем API с выводом в терминал
echo ""
echo "🚀 ЗАПУСК AI API С ВЫВОДОМ ЛОГОВ..."
echo "========================================"

# Создаем именованный канал (FIFO) для передачи логов
LOG_PIPE=$(mktemp -u /tmp/api_log_pipe.XXXXXX)
mkfifo "$LOG_PIPE"

# Функция для обработки логов API
process_api_logs() {
    echo "📡 API ЛОГИ:"
    echo "================"
    while read -r line; do
        echo "🔹 $line"
    done < "$LOG_PIPE"
}

# Запускаем обработку логов в фоновом режиме
process_api_logs &
LOG_PROCESS=$!

# Запускаем API, перенаправляя вывод в канал
python3 api_simple_with_cors.py 2>&1 | tee "$LOG_PIPE" &
API_PID=$!

# Ждем запуска API
sleep 5

# Проверяем порт API
API_PORT=""
for i in {1..10}; do
    if [ -f "api_port.txt" ]; then
        API_PORT=$(cat api_port.txt)
        echo "✅ API запущен на порту $API_PORT"
        break
    fi
    sleep 1
    echo "   ⏳ Ожидание запуска API ($i/10)..."
done

if [ -z "$API_PORT" ]; then
    echo "   ⚠️  API порт не определен, проверяю порт по умолчанию 5001"
    API_PORT=5001
fi

# Запускаем прокси
echo ""
echo "🔧 Запуск прокси..."
$NODE_CMD proxy-server.js 2>&1 | while read -r line; do
    echo "🌐 $line"
done &
PROXY_PID=$!

sleep 3

# Проверяем прокси
PROXY_OK=false
for i in {1..5}; do
    if kill -0 $PROXY_PID 2>/dev/null; then
        if curl -s http://localhost:3000 > /dev/null 2>&1 || netstat -an | grep -q "\.3000.*LISTEN"; then
            echo "   ✅ Прокси запущен на порту 3000"
            PROXY_OK=true
            break
        fi
    fi
    sleep 1
    echo "   ⏳ Ожидание запуска прокси ($i/5)..."
done

if [ "$PROXY_OK" = false ]; then
    echo "   ❌ Прокси не запустился"
    echo "   Пробую альтернативный способ..."
    echo "   Откройте новый терминал и запустите:"
    echo "   cd '$PWD' && $NODE_CMD proxy-server.js"
    echo "   Затем в этом окне нажмите Enter..."
    read
fi

# Проверяем Ollama (для LLM функциональности)
echo ""
echo "🤖 Проверка Ollama..."
LLM_STATUS="❌ Недоступен"
if command -v ollama > /dev/null 2>&1; then
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        LLM_STATUS="✅ Ollama (llama3.2)"
    else
        LLM_STATUS="⚠️  Ollama (сервер не запущен)"
    fi
fi

echo ""
echo "🎉 СИСТЕМА ЗАПУЩЕНА!"
echo "====================="
echo ""
echo "📊 СЕРВЕРЫ:"
echo "   • AI API:    http://localhost:$API_PORT/api/health"
echo "   • Прокси:    http://localhost:3000"
echo "   • Редактор:  http://localhost:3000/proxy-index.html"
echo "   • LLM:       $LLM_STATUS"
echo ""
echo "📝 ЛОГИ В РЕАЛЬНОМ ВРЕМЕНИ:"
echo "   • API логи выводятся выше в этом окне"
echo "   • JSON модели будет виден после генерации"
echo ""
echo "🎯 ЧТО ДЕЛАТЬ ДАЛЬШЕ:"
echo "   1. Браузер должен открыться автоматически"
echo "   2. Если нет, откройте: http://localhost:3000/proxy-index.html"
echo "   3. Нажмите кнопку 'Graph Manager' (в правом верхнем углу графа)"
echo "   4. Загрузите файл (.txt, .md, .pdf) или введите текст ТЗ"
echo "   5. Нажмите 'Отправить' для генерации модели"
echo ""
echo "🔧 ЕСЛИ ВОЗНИКЛИ ПРОБЛЕМЫ:"
echo "   • Проверьте, что порты 3000 и $API_PORT свободны"
echo "   • Перезапустите скрипт: ./launch_with_logs.command"
echo ""
echo "🛑 ДЛЯ ОСТАНОВКИ:"
echo "   Нажмите Ctrl+C в этом окне"

# Очистка при завершении
cleanup() {
    echo ""
    echo "🛑 Остановка системы..."
    kill $API_PID 2>/dev/null || true
    kill $PROXY_PID 2>/dev/null || true
    kill $LOG_PROCESS 2>/dev/null || true
    rm -f "$LOG_PIPE" 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

# Открываем браузер
echo ""
echo "🌐 Открываю браузер..."
open "http://localhost:3000/proxy-index.html" 2>/dev/null || true

# Ждем завершения
wait