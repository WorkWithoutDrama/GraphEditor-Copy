#!/usr/bin/env python3
"""
Упрощенный финальный API, который точно работает
"""

import http.server
import socketserver
import socket
import json
import sys
import os

def find_free_port(start_port=5001):
    """Находит свободный порт"""
    port = start_port
    while port < start_port + 20:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            port += 1
        finally:
            sock.close()
    return None

class SimpleAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == "/api/health" or self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "api": "available"}).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        if self.path == "/api/generate-model":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                text = data.get('text', '')
            except:
                text = ''
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Простая тестовая модель
            model = {
                "model_actions": [
                    {
                        "action_id": "a00001",
                        "action_name": f"Действие: {text[:30]}" if text else "Тестовое действие",
                        "action_links": {"manual": "", "API": "", "UI": ""}
                    }
                ],
                "model_objects": [
                    {
                        "object_id": "o00001",
                        "object_name": "Тестовый объект",
                        "resource_state": [
                            {"state_id": "s00001", "state_name": "начальное состояние"},
                            {"state_id": "s00002", "state_name": "конечное состояние"}
                        ],
                        "object_links": {"manual": "", "API": "", "UI": ""}
                    }
                ],
                "model_connections": [
                    {
                        "connection_out": "o00001s00001",
                        "connection_in": "a00001"
                    },
                    {
                        "connection_out": "a00001",
                        "connection_in": "o00001s00002"
                    }
                ]
            }
            
            response = {
                "success": True,
                "model": model
            }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def log_message(self, format, *args):
        # Минимальное логирование
        print(f"📡 {self.address_string()} - {format % args}")

def main():
    # Ищем свободный порт
    port = find_free_port(5001)
    if not port:
        print("❌ Не удалось найти свободный порт")
        sys.exit(1)
    
    # Записываем порт в файл
    with open('api_port.txt', 'w') as f:
        f.write(str(port))
    
    print(f"🚀 API запущен на порту {port}")
    print(f"📡 Записан порт в api_port.txt: {port}")
    print(f"🔧 Эндпоинты:")
    print(f"   • GET  http://localhost:{port}/api/health")
    print(f"   • GET  http://localhost:{port}/api/status")
    print(f"   • POST http://localhost:{port}/api/generate-model")
    print(f"🛑 Для остановки нажмите Ctrl+C")
    
    try:
        with socketserver.TCPServer(("", port), SimpleAPIHandler) as httpd:
            print(f"✅ Сервер запущен")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
    finally:
        if os.path.exists('api_port.txt'):
            os.remove('api_port.txt')

if __name__ == "__main__":
    main()