#!/bin/bash

# Останавливаем текущий API
echo "🛑 Останавливаю текущий API..."
pkill -f "api_simple_with_logging.py" 2>/dev/null
pkill -f "api-fixed-new-structure.py" 2>/dev/null
pkill -f "api.py" 2>/dev/null

# Ждем остановки
sleep 2

# Запускаем API с выводом в терминал
echo "🚀 Запускаю api_simple_with_logging.py с выводом логов..."
echo "============================================================"
python3 api_simple_with_logging.py