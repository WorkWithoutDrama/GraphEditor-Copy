#!/usr/bin/env python3
"""
Упрощенный API для тестирования
"""

import http.server
import socketserver
import json
import sys

PORT = 5001

class SimpleAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == "/api/status":
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
            post_data = self.rfile.read(content_length)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Возвращаем тестовую модель
            test_model = {
                "model_actions": [
                    {
                        "action_id": "a00001",
                        "action_name": "Тестовое действие",
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
                "model": test_model
            }
            
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

def run_server():
    with socketserver.TCPServer(("", PORT), SimpleAPIHandler) as httpd:
        print(f"🚀 API запущен на порту {PORT}")
        print(f"📡 URL: http://localhost:{PORT}")
        print(f"🔧 Эндпоинты:")
        print(f"   • GET  /api/status")
        print(f"   • POST /api/generate-model")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Сервер остановлен")

if __name__ == "__main__":
    try:
        run_server()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Порт {PORT} занят")
            print("💡 Попробуйте другой порт:")
            print("   python3 test_simple_api.py --port 5002")
        else:
            raise