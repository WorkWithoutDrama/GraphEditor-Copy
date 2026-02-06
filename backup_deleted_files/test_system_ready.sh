#!/bin/bash

echo "🎯 ТЕСТИРОВАНИЕ ЗАПУЩЕННОЙ СИСТЕМЫ"
echo "=================================="

# Проверяем, что компоненты работают
echo ""
echo "1. Проверка API сервера:"
API_RESPONSE=$(curl -s http://localhost:5009/api/health 2>/dev/null)
if echo "$API_RESPONSE" | grep -q "status.*ok"; then
    echo "   ✅ API сервер работает"
    echo "   Ответ: $API_RESPONSE"
else
    echo "   ❌ API сервер не отвечает"
fi

echo ""
echo "2. Проверка прокси сервера:"
PROXY_RESPONSE=$(curl -s http://localhost:3000/api/health 2>/dev/null)
if echo "$PROXY_RESPONSE" | grep -q "status.*ok"; then
    echo "   ✅ Прокси сервер работает"
    echo "   Ответ: $PROXY_RESPONSE"
else
    echo "   ⚠️  Прокси не проксирует API запросы"
fi

echo ""
echo "3. Проверка статических файлов:"
STATIC_FILES=("/" "/proxy-index.html" "/test-fix.html" "/styles.css")
for file in "${STATIC_FILES[@]}"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000$file 2>/dev/null)
    if [[ "$STATUS" == "200" ]]; then
        echo "   ✅ $file - доступен (код: $STATUS)"
    else
        echo "   ❌ $file - не доступен (код: $STATUS)"
    fi
done

echo ""
echo "4. Проверка Graph Manager:"
if curl -s http://localhost:3000/proxy-index.html | grep -q "Graph Manager"; then
    echo "   ✅ Graph Manager присутствует на странице"
else
    echo "   ⚠️  Graph Manager не найден на странице"
fi

echo ""
echo "=================================="
echo "📊 ИТОГ:"
echo ""
echo "Если все проверки пройдены ✅, то:"
echo "1. Откройте браузер: http://localhost:3000/proxy-index.html"
echo "2. Должен загрузиться Graph Editor"
echo "3. Нажмите кнопку 'Graph Manager' (в правом верхнем углу)"
echo "4. Введите текст ТЗ или загрузите файл"
echo "5. Нажмите 'Отправить'"
echo ""
echo "🔧 Для тестирования модели откройте:"
echo "   http://localhost:3000/test-fix.html"
echo ""
echo "🛑 Для остановки системы:"
echo "   Нажмите Ctrl+C в терминале с launch.command"
echo "   Или закройте окно терминала"