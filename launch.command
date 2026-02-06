#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "   🚀 GRAPH EDITOR - УПРОЩЕННЫЙ ЗАПУСК"
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

# Проверяем Ollama (для LLM функциональности)
echo "🤖 Проверка Ollama..."
if command -v ollama > /dev/null 2>&1; then
    echo "✅ Ollama установлен"

    # Проверяем, запущен ли сервер Ollama
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "   🚀 Запуск сервера Ollama..."
        # Запускаем Ollama в фоновом режиме
        ollama serve > /dev/null 2>&1 &
        OLLAMA_PID=$!
        echo "   ✅ Ollama запущен (PID: $OLLAMA_PID)"

        # Ждем запуска сервера
        echo "   ⏳ Ожидание запуска сервера..."
        sleep 5

        # Проверяем, что сервер запустился
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "   ✅ Сервер Ollama готов"
        else
            echo "   ⚠️  Не удалось запустить сервер Ollama. LLM функции могут не работать."
        fi
    else
        echo "   ✅ Сервер Ollama уже запущен"
    fi

    # Проверяем наличие модели llama3.2
    echo "   🔍 Проверка модели llama3.2..."
    if curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
        echo "   ✅ Модель llama3.2 найдена"
    else
        echo "   ⬇️  Модель llama3.2 не найдена. Загрузка..."
        ollama pull llama3.2 > /dev/null 2>&1 &
        echo "   ✅ Модель загружается в фоновом режиме"
    fi
else
    echo "   ⚠️  Ollama не установлен. LLM функции не будут доступны."
    echo "   Установите Ollama: https://ollama.ai/"
    echo "   Или используйте DeepSeek через настройки интерфейса."
fi

echo ""

# Останавливаем старые процессы
echo "🧹 Останавливаю старые процессы..."
pkill -f "python api.py" 2>/dev/null || true
pkill -f "node proxy-server" 2>/dev/null || true
pkill -f "node proxy-server-fixed" 2>/dev/null || true
# Останавливаем наш собственный запущенный Ollama, если он есть
if [ ! -z "$OLLAMA_PID" ] && kill -0 $OLLAMA_PID 2>/dev/null; then
    kill $OLLAMA_PID 2>/dev/null || true
    echo "   Остановлен Ollama (PID: $OLLAMA_PID)"
fi
sleep 2

# Запускаем API с ГАРАНТИРОВАННЫМ выводом логов
echo "🔧 Запуск AI API..."
echo "   Использую api_test_logs.py с гарантированным выводом логов"
echo ""
echo "🚀 ЗАПУСК API (логи БУДУТ ВИДНЫ ниже):"
echo "======================================="

# Запускаем тестовый API, который точно выводит логи
python3 api_test_logs.py 2>&1 | while read -r line; do
    echo "📢 $line"
done &
API_PID=$!

# Даем время на запуск
echo "⏳ Запуск API... (5 секунд)"
sleep 5

# Проверяем порт API (пробуем несколько раз)
API_PORT=""
for i in {1..5}; do
    if [ -f "api_port.txt" ]; then
        API_PORT=$(cat api_port.txt)
        echo "   ✅ API запущен на порту $API_PORT"
        break
    fi
    sleep 1
    echo "   ⏳ Ожидание запуска API (попытка $i/5)..."
done

if [ -z "$API_PORT" ]; then
    echo "   ⚠️  API порт не определен, использую порт по умолчанию 5009"
    API_PORT=5009

    # Проверяем, работает ли API
    if curl -s http://localhost:$API_PORT/api/health > /dev/null 2>&1; then
        echo "   ✅ API работает на порту $API_PORT"
    else
        echo "   ❌ API не запустился"
        echo "   Пробую альтернативный способ..."
        echo "   Откройте новый терминал и запустите:"
        echo "   cd '$PWD' && python3 api_simple_with_cors.py"
        echo "   Затем в этом окне нажмите Enter..."
        read
    fi
fi

# Запускаем прокси
echo "🔧 Запуск прокси..."
$NODE_CMD proxy-server.js &
PROXY_PID=$!
sleep 3  # Даем время на запуск

# Проверяем прокси (пробуем несколько раз)
PROXY_OK=false
for i in {1..5}; do
    if kill -0 $PROXY_PID 2>/dev/null; then
        # Проверяем, слушает ли прокси порт
        if curl -s http://localhost:3000 > /dev/null 2>&1 || netstat -an | grep -q "\.3000.*LISTEN"; then
            echo "   ✅ Прокси запущен на порту 3000"
            PROXY_OK=true
            break
        fi
    fi
    sleep 1
    echo "   ⏳ Ожидание запуска прокси (попытка $i/5)..."
done

if [ "$PROXY_OK" = false ]; then
    echo "   ❌ Прокси не запустился"
    echo "   Пробую альтернативный способ..."
    echo "   Откройте новый терминал и запустите:"
echo "   cd '$PWD' && $NODE_CMD proxy-server.js"
    echo "   Затем в этом окне нажмите Enter..."
    read
fi

echo ""
echo "🌐 Открываю Graph Editor..."
open "http://localhost:3000/proxy-index.html"

echo ""

# Проверяем статус LLM
LLM_STATUS="❌ Недоступен"
if command -v ollama > /dev/null 2>&1; then
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        LLM_STATUS="✅ Ollama (llama3.2)"
    else
        LLM_STATUS="⚠️  Ollama (сервер не запущен)"
    fi
fi

echo "✅ СИСТЕМА ЗАПУЩЕНА!"
echo ""
echo "📊 СЕРВЕРЫ:"
echo "   • AI API:    http://localhost:$API_PORT/api/health"
echo "   • Прокси:    http://localhost:3000"
echo "   • Редактор:  http://localhost:3000/proxy-index.html"
echo "   • LLM:       $LLM_STATUS"
echo ""
echo "📝 ЛОГИ В РЕАЛЬНОМ ВРЕМЕНИ:"
echo "   • Логи API отображаются выше с префиксом '📝'"
echo "   • JSON модели будет виден после генерации"
echo "   • Подробные логи также в файле: api.log"
echo ""
echo "🔍 ДЛЯ ПРОВЕРКИ:"
echo "   API здоровье: curl http://localhost:$API_PORT/api/health"
echo "   Прокси работает: curl http://localhost:3000/api/health"
echo ""

# Показываем текущие логи API
echo "🔄 Текущие логи API:"
echo "====================="
# Даем время на вывод начальных логов
sleep 2
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
echo "   • Перезапустите скрипт: ./launch.command"
echo "   • Подробная документация: README.md"
echo ""
echo "🛑 ДЛЯ ОСТАНОВКИ:"
echo "   Закройте это окно или нажмите Ctrl+C"
echo ""

# Функция очистки при завершении
cleanup() {
    echo ""
    echo "🧹 Остановка системы..."

    # Останавливаем API
    if [ ! -z "$API_PID" ] && kill -0 $API_PID 2>/dev/null; then
        kill $API_PID 2>/dev/null || true
        echo "   Остановлен AI API"
    fi

    # Останавливаем прокси
    if [ ! -z "$PROXY_PID" ] && kill -0 $PROXY_PID 2>/dev/null; then
        kill $PROXY_PID 2>/dev/null || true
        echo "   Остановлен прокси"
    fi

    # Останавливаем отображение логов и удаляем канал
    if [ ! -z "$LOG_DISPLAY_PID" ] && kill -0 $LOG_DISPLAY_PID 2>/dev/null; then
        kill $LOG_DISPLAY_PID 2>/dev/null || true
    fi

    # Удаляем именованный канал
    if [ -p "$LOG_PIPE" ]; then
        rm -f "$LOG_PIPE" 2>/dev/null || true
    fi

    # Останавливаем наш собственный запущенный Ollama
    if [ ! -z "$OLLAMA_PID" ] && kill -0 $OLLAMA_PID 2>/dev/null; then
        kill $OLLAMA_PID 2>/dev/null || true
        echo "   Остановлен Ollama"
    fi

    echo "✅ Система остановлена"
    exit 0
}

# Устанавливаем обработчик сигналов
trap cleanup SIGINT SIGTERM

echo "🛑 ДЛЯ ОСТАНОВКИ: нажмите Ctrl+C"
echo ""

# Ждем
wait

# Если скрипт завершился нормально, тоже вызываем cleanup
cleanup
