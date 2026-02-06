#!/bin/bash

echo "========================================"
echo "   🧪 ПРОСТЕЙШИЙ ТЕСТ API"
echo "========================================"
echo ""

# Останавливаем все
echo "🛑 Останавливаю все процессы..."
pkill -f "python.*api" 2>/dev/null
pkill -f "node proxy-server" 2>/dev/null
sleep 2

echo ""
echo "========================================"
echo "🚀 ЗАПУСК ПРОСТОГО API"
echo "========================================"

# Запускаем простой API
python3 -c "
import http.server
import socketserver
import json
import sys
import datetime

print('🚀 ПРОСТОЙ API ЗАПУЩЕН!')
print('📢 Этот текст ДОЛЖЕН быть виден сразу!')
sys.stdout.flush()

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == '/api/health':
            print('📡 GET /api/health - Обработка запроса')
            sys.stdout.flush()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
            sys.stdout.flush()
    
    def do_POST(self):
        if self.path == '/api/generate-model':
            print('📥 POST /api/generate-model - Получен запрос!')
            sys.stdout.flush()
            
            import json
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            text = data.get('text', '')
            
            print(f'📄 Текст: {text[:50]}...')
            print('🔄 Генерация модели...')
            sys.stdout.flush()
            
            # Простая модель
            model = {
                'model_actions': [{
                    'action_id': 'a00001',
                    'action_name': f'Действие из \"{text[:20]}...\"',
                    'action_links': {'manual': '', 'API': '', 'UI': ''}
                }]
            }
            
            print('🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:')
            print(json.dumps(model, ensure_ascii=False, indent=2))
            print('📊 Статистика:')
            print('• Действий: 1')
            print('• Объектов: 0')
            print('• Связей: 0')
            print('✅ Ответ отправлен')
            sys.stdout.flush()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'model': model}).encode())
            sys.stdout.flush()
    
    def log_message(self, format, *args):
        message = f\"{self.address_string()} - {format % args}\"
        print(f\"🔹 {message}\")
        sys.stdout.flush()

# Ищем свободный порт
for port in range(5001, 5020):
    try:
        server = socketserver.TCPServer(('', port), SimpleHandler)
        print(f'✅ API запущен на порту {port}')
        print(f'📡 GET  http://localhost:{port}/api/health')
        print(f'📡 POST http://localhost:{port}/api/generate-model')
        print('🛑 Ctrl+C для остановки')
        sys.stdout.flush()
        
        # Записываем порт
        with open('api_port.txt', 'w') as f:
            f.write(str(port))
        sys.stdout.flush()
        
        server.serve_forever()
        break
    except OSError:
        continue
" &
API_PID=$!

echo ""
echo "⏳ Запуск API... (3 секунды)"
sleep 3

echo ""
echo "========================================"
echo "🎯 ПРОВЕРКА РАБОТЫ API"
echo "========================================"

# Проверяем порт
if [ -f "api_port.txt" ]; then
    PORT=$(cat api_port.txt)
    echo "✅ API порт: $PORT"
    
    echo ""
    echo "📤 Отправляю тестовый запрос..."
    curl -X POST "http://localhost:$PORT/api/generate-model" \
         -H "Content-Type: application/json" \
         -d '{"text":"Тестовый запрос для проверки логов"}' 2>&1
    
    echo ""
    echo "========================================"
    echo "👀 ЛОГИ API ДОЛЖНЫ БЫТЬ ВЫШЕ!"
    echo "========================================"
    echo ""
    echo "Если видите '📥 POST /api/generate-model' и '🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ' - API работает!"
    echo ""
    echo "🛑 Для остановки: kill $API_PID"
else
    echo "❌ API не запустился"
    kill $API_PID 2>/dev/null
fi