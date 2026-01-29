#!/bin/bash

echo "🔍 Проверка зависимостей Graph Editor"
echo "======================================"

# Проверяем Node.js
echo -n "Node.js: "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ $NODE_VERSION"
else
    echo "❌ НЕ УСТАНОВЛЕН"
    echo "   Скачайте: https://nodejs.org/"
    open "https://nodejs.org/"
fi

# Проверяем npm
echo -n "npm: "
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✅ $NPM_VERSION"
else
    echo "⚠️  НЕ УСТАНОВЛЕН (обычно идет с Node.js)"
fi

# Проверяем Python 3
echo -n "Python 3: "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "✅ $PYTHON_VERSION"
else
    echo "❌ НЕ УСТАНОВЛЕН"
    echo "   Скачайте: https://www.python.org/"
    open "https://www.python.org/"
fi

# Проверяем Python
echo -n "Python (python): "
if command -v python &> /dev/null; then
    PYTHON2_VERSION=$(python --version 2>&1)
    echo "✅ $PYTHON2_VERSION"
else
    echo "⚠️  python команда не найдена (используется python3)"
fi

echo ""
echo "📋 Файлы проекта:"

# Проверяем необходимые файлы
REQUIRED_FILES=("api.py" "proxy-server.js" "proxy-index.html" "graph-manager.js" "script.js")
for file in "${REQUIRED_FILES[@]}"; do
    echo -n "   $file: "
    if [ -f "$file" ]; then
        echo "✅"
    else
        echo "❌ ОТСУТСТВУЕТ"
    fi
done

echo ""
echo "🎯 Для запуска выполните:"
echo "   ./start.command"
echo ""
echo "📝 Или дважды кликните start.command"