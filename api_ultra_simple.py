#!/usr/bin/env python3
"""
Сверхпростой API, который точно работает
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket

class SimpleHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path in ["/api/health", "/api/status"]:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({"status": "ok", "api": "available"})
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == "/api/generate-model":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = json.dumps({
                "success": True,
                "model": {
                    "model_actions": [{"action_id": "a00001", "action_name": "Тест"}],
                    "model_objects": [{"object_id": "o00001", "object_name": "Тест"}],
                    "model_connections": []
                }
            })
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        print(f"📡 {self.address_string()} - {format % args}")

def find_free_port():
    for port in range(5001, 5021):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            sock.close()
            return port
        except:
            continue
    return 5001

def main():
    port = find_free_port()
    print(f"🚀 Запуск API на порту {port}")
    print(f"📡 Эндпоинты:")
    print(f"   • GET  http://localhost:{port}/api/health")
    print(f"   • POST http://localhost:{port}/api/generate-model")
    print(f"🛑 Ctrl+C для остановки")
    
    with open('api_port.txt', 'w') as f:
        f.write(str(port))
    
    server = HTTPServer(('', port), SimpleHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
    finally:
        import os
        if os.path.exists('api_port.txt'):
            os.remove('api_port.txt')

if __name__ == "__main__":
    main()