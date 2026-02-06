#!/bin/bash

echo "🤖 ПРОВЕРКА НАСТРОЙКИ LLM ДЛЯ GRAPH EDITOR"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Проверка основных зависимостей
echo "1. 🔍 Проверка основных зависимостей:"
echo "   ---------------------------------"

if command -v node > /dev/null 2>&1; then
    echo "   ✅ Node.js: $(node --version)"
else
    echo "   ❌ Node.js не установлен"
fi

if command -v python3 > /dev/null 2>&1; then
    echo "   ✅ Python: $(python3 --version)"
else
    echo "   ❌ Python 3 не установлен"
fi

echo ""

# Проверка Ollama
echo "2. 🔍 Проверка Ollama:"
echo "   -----------------"

if command -v ollama > /dev/null 2>&1; then
    echo "   ✅ Ollama установлен: $(ollama --version | head -1)"
    
    # Проверка сервера Ollama
    echo "   📡 Проверка сервера Ollama..."
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "   ✅ Сервер Ollama запущен"
        
        # Проверка моделей
        echo "   🔍 Проверка моделей..."
        if curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
            echo "   ✅ Модель llama3.2 найдена"
        else
            echo "   ⚠️  Модель llama3.2 не найдена"
            echo "   💡 Загрузите: ollama pull llama3.2"
        fi
    else
        echo "   ⚠️  Сервер Ollama не запущен"
        echo "   💡 Запустите: ollama serve"
    fi
else
    echo "   ⚠️  Ollama не установлен"
    echo "   💡 Установите: https://ollama.ai/"
    echo "   или используйте DeepSeek с API ключом"
fi

echo ""

# Проверка DeepSeek API ключа
echo "3. 🔍 Проверка DeepSeek API ключа:"
echo "   -----------------------------"

if [ -n "$DEEPSEEK_API_KEY" ]; then
    echo "   ✅ DeepSeek API ключ установлен"
    echo "   💡 Длина ключа: ${#DEEPSEEK_API_KEY} символов"
else
    echo "   ⚠️  DeepSeek API ключ не установлен"
    echo "   💡 Установите: export DEEPSEEK_API_KEY=\"ваш_ключ\""
    echo "   или получите ключ: https://platform.deepseek.com/"
fi

echo ""

# Проверка портов
echo "4. 🔍 Проверка портов:"
echo "   -----------------"

echo "   📊 Проверка занятости портов:"
PORTS=(3000 5001 11434)
for port in "${PORTS[@]}"; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "   ⚠️  Порт $port занят"
    else
        echo "   ✅ Порт $port свободен"
    fi
done

echo ""

# Рекомендации
echo "5. 📋 РЕКОМЕНДАЦИИ:"
echo "   ---------------"

if command -v ollama > /dev/null 2>&1 && curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
    echo "   ✅ Ваша система готова для использования LLM!"
    echo "   💡 Запустите: ./launch.command"
elif [ -n "$DEEPSEEK_API_KEY" ]; then
    echo "   ✅ Можете использовать DeepSeek LLM"
    echo "   💡 Запустите: ./launch.command"
    echo "   💡 В интерфейсе выберите DeepSeek провайдер"
else
    echo "   ⚠️  LLM функции недоступны"
    echo "   💡 Установите Ollama или настройте DeepSeek"
    echo "   💡 Система будет работать в резервном режиме"
fi

echo ""
echo "=========================================="
echo "Для запуска системы: ./launch.command"
echo "Для очистки портов: ./cleanup.command"
echo ""