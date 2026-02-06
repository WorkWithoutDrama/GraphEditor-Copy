#!/bin/bash

echo "🧹 Очистка портов Graph Editor"
echo "==============================="
echo ""

# Проверяем процессы на портах
echo "🔍 Поиск процессов на портах 3000 и 5001..."

PROCESSES_3000=$(lsof -ti:3000 2>/dev/null)
PROCESSES_5001=$(lsof -ti:5001 2>/dev/null)

# Также проверяем процессы Ollama (порт 11434)
OLLAMA_PROCESSES=$(pgrep -f "ollama serve" 2>/dev/null)

if [ -n "$PROCESSES_3000" ] || [ -n "$PROCESSES_5001" ] || [ -n "$OLLAMA_PROCESSES" ]; then
    echo "📋 Найдены процессы:"
    
    if [ -n "$PROCESSES_3000" ]; then
        echo "   Порт 3000:"
        for pid in $PROCESSES_3000; do
            echo "   • PID $pid: $(ps -p $pid -o comm= 2>/dev/null || echo 'неизвестный процесс')"
        done
    fi
    
    if [ -n "$PROCESSES_5001" ]; then
        echo "   Порт 5001:"
        for pid in $PROCESSES_5001; do
            echo "   • PID $pid: $(ps -p $pid -o comm= 2>/dev/null || echo 'неизвестный процесс')"
        done
    fi

    if [ -n "$OLLAMA_PROCESSES" ]; then
        echo "   Ollama сервер:"
        for pid in $OLLAMA_PROCESSES; do
            echo "   • PID $pid: Ollama serve"
        done
    fi

    echo ""
    read -p "❓ Остановить все процессы? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Останавливаем процессы
        echo "🛑 Останавливаю процессы..."
        
        if [ -n "$PROCESSES_3000" ]; then
            kill -9 $PROCESSES_3000 2>/dev/null
            echo "   ✅ Порт 3000 очищен"
        fi
        
        if [ -n "$PROCESSES_5001" ]; then
            kill -9 $PROCESSES_5001 2>/dev/null
            echo "   ✅ Порт 5001 очищен"
        fi

        if [ -n "$OLLAMA_PROCESSES" ]; then
            kill -9 $OLLAMA_PROCESSES 2>/dev/null
            echo "   ✅ Ollama сервер остановлен"
        fi

        sleep 1

        # Проверяем еще раз
        REMAINING_3000=$(lsof -ti:3000 2>/dev/null)
        REMAINING_5001=$(lsof -ti:5001 2>/dev/null)
        REMAINING_OLLAMA=$(pgrep -f "ollama serve" 2>/dev/null)

        if [ -z "$REMAINING_3000" ] && [ -z "$REMAINING_5001" ] && [ -z "$REMAINING_OLLAMA" ]; then
            echo ""
            echo "✅ Все порты свободны!"
            echo "Теперь можно запустить: ./launch.command"
        else
            echo ""
            echo "⚠️  Некоторые процессы не остановились:"
            if [ -n "$REMAINING_3000" ]; then
                echo "   Порт 3000: $(echo $REMAINING_3000 | wc -w) процессов"
            fi
            if [ -n "$REMAINING_5001" ]; then
                echo "   Порт 5001: $(echo $REMAINING_5001 | wc -w) процессов"
            fi
            if [ -n "$REMAINING_OLLAMA" ]; then
                echo "   Ollama: $(echo $REMAINING_OLLAMA | wc -w) процессов"
            fi
        fi
    else
        echo "ℹ️  Процессы не остановлены"
    fi
else
    echo "✅ Порта 3000 и 5001 свободны"
    echo "Можно запускать: ./RUN.command"
fi

echo ""