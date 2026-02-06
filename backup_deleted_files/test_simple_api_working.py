#!/usr/bin/env python3
"""
Простейший рабочий API для теста
"""

import http.server
import socketserver
import socket
import json
import sys

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

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    
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
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length:
                self.rfile.read(content_length)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            response = {
                "success": True,
                "model": {
                    "model_actions": [{"action_id": "a00001", "action_name": "Тест"}],
                    "model_objects": [{"object_id": "o00001", "object_name": "Тест"}],
                    "model_connections": []
                }
            }
            
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование
        pass

def main():
    port = find_free_port(5001)
    if not port:
        print("❌ Не удалось найти свободный порт")
        sys.exit(1)
    
    print(f"🚀 Запуск тестового API на порту {port}")
    print(f"🔧 Эндпоинты:")
    print(f"   • GET  http://localhost:{port}/api/health")
    print(f"   • GET  http://localhost:{port}/api/status")
    print(f"   • POST http://localhost:{port}/api/generate-model")
    
    with socketserver.TCPServer(("", port), SimpleHandler) as httpd:
        print(f"✅ Сервер запущен. Нажмите Ctrl+C для остановки")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Сервер остановлен")

if __name__ == "__main__":
    main()