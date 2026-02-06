#!/usr/bin/env python3
"""
САМЫЙ ПРОСТОЙ API для тестирования вывода логов
"""

import http.server
import socketserver
import json
import sys
import datetime

# ПРИНУДИТЕЛЬНО ОТКЛЮЧАЕМ ВСЮ БУФЕРИЗАЦИЮ
# 1. Устанавливаем переменную окружения
import os
os.environ['PYTHONUNBUFFERED'] = '1'

# 2. Принудительно сбрасываем буфер sys.stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

print("=" * 60)
print("🚀 ТЕСТОВЫЙ API - ГАРАНТИРОВАННЫЙ ВЫВОД ЛОГОВ")
print("=" * 60)
print("Это сообщение ДОЛЖНО быть видно сразу!")
sys.stdout.flush()

class TestAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Кастомизация логов - выводим ВСЕГДА"""
        message = f"{self.address_string()} - {format % args}"
        print(f"🔹 {message}")
        sys.stdout.flush()
    
    def do_GET(self):
        if self.path == "/api/health":
            print("📡 ОБРАБОТКА GET /api/health")
            sys.stdout.flush()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "api": "test"}).encode())
            sys.stdout.flush()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        if self.path == "/api/generate-model":
            print("📥 ПОЛУЧЕН POST ЗАПРОС /api/generate-model")
            sys.stdout.flush()
            
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                text = data.get('text', '')
                
                print(f"📄 Текст запроса: {text[:50]}...")
                print(f"📏 Длина: {len(text)} символов")
                sys.stdout.flush()
                
                # Создаем тестовую модель
                print("🔄 ГЕНЕРАЦИЯ МОДЕЛИ...")
                sys.stdout.flush()
                
                timestamp = int(datetime.datetime.now().timestamp() * 1000)
                model = {
                    "model_actions": [
                        {
                            "action_id": f"a{timestamp % 100000:05d}",
                            "action_name": f"Тестовое действие из '{text[:20]}...'",
                            "action_links": {"manual": "", "API": "", "UI": ""}
                        }
                    ]
                }
                
                # ВЫВОДИМ JSON - ПОСТРОЧНО И С ПРИНУДИТЕЛЬНЫМ FLUSH
                print("🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
                sys.stdout.flush()
                
                json_str = json.dumps(model, ensure_ascii=False, indent=2)
                for line in json_str.split('\n'):
                    print(line)
                    sys.stdout.flush()
                
                print("📊 СТАТИСТИКА:")
                print(f"• Действий: {len(model.get('model_actions', []))}")
                print(f"• Объектов: {len(model.get('model_objects', []))}")
                print(f"• Связей: {len(model.get('model_connections', []))}")
                sys.stdout.flush()
                
                # Отправляем ответ
                response = {"success": True, "model": model}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
                
                print("✅ ОТВЕТ ОТПРАВЛЕН")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"❌ ОШИБКА: {e}")
                sys.stdout.flush()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

def run_server(port=5001):
    """Запуск тестового сервера"""
    handler = TestAPIHandler
    
    for p in range(port, port + 20):
        try:
            server = socketserver.TCPServer(("", p), handler)
            print(f"✅ ТЕСТОВЫЙ API запущен на порту {p}")
            print(f"📡 GET  http://localhost:{p}/api/health")
            print(f"📡 POST http://localhost:{p}/api/generate-model")
            print("🛑 Для остановки: Ctrl+C")
            sys.stdout.flush()
            
            # Записываем порт
            with open('api_port.txt', 'w') as f:
                f.write(str(p))
            sys.stdout.flush()
            
            server.serve_forever()
            break
        except OSError as e:
            if "Address already in use" in str(e):
                continue
            else:
                raise

if __name__ == "__main__":
    run_server()