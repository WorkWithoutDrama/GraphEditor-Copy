#!/usr/bin/env python3
import http.server
import socketserver
import webbrowser
import os

PORT = 8000

# Меняем рабочую директорию на директорию скрипта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Добавляем CORS заголовки
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
    print(f"\n🌐 Сервер запущен на http://localhost:{PORT}")
    print("📂 Открываю браузер...")
    print("🛑 Для остановки нажмите Ctrl+C\n")
    
    # Открываем браузер
    webbrowser.open(f'http://localhost:{PORT}')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")