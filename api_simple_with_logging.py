#!/usr/bin/env python3
"""
Упрощенный API с немедленным выводом JSON в логи
"""

import http.server
import socketserver
import json
import os
import sys
import logging
import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

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
            self.handle_generate_model()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def handle_generate_model(self):
        """Обработка запроса на генерацию модели - УПРОЩЕННАЯ ВЕРСИЯ"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Empty request body")
                return
            
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            text = data.get('text', '')
            
            if not text:
                self.send_error(400, "Missing 'text' parameter")
                return
            
            # ЛОГИРУЕМ ЗАПРОС
            logger.info(f"📥 ПОЛУЧЕН ЗАПРОС:")
            logger.info(f"• Текст: {text[:100]}...")
            logger.info(f"• Длина: {len(text)} символов")
            
            # Создаем модель
            logger.info("🔄 ГЕНЕРАЦИЯ МОДЕЛИ...")
            model = self._create_simple_model(text)
            
            # ВЫВОДИМ ПОЛНЫЙ JSON В ЛОГ
            logger.info("🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
            logger.info(json.dumps(model, ensure_ascii=False, indent=2))
            
            # Статистика
            logger.info("📊 СТАТИСТИКА МОДЕЛИ:")
            logger.info(f"• Действий: {len(model.get('model_actions', []))}")
            logger.info(f"• Объектов: {len(model.get('model_objects', []))}")
            logger.info(f"• Связей: {len(model.get('model_connections', []))}")
            
            # Отправляем ответ
            response = {"success": True, "model": model}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            
            logger.info("✅ ОТВЕТ ОТПРАВЛЕН")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }).encode())
    
    def _create_simple_model(self, text: str):
        """Создает простую модель для демонстрации"""
        timestamp = int(datetime.datetime.now().timestamp() * 1000)
        
        # Создаем ID на основе текста и времени
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:6]
        
        model = {
            "model_actions": [
                {
                    "action_id": f"a{timestamp % 100000:05d}",
                    "action_name": f"Действие из '{text[:30]}...'",
                    "action_links": {"manual": "", "API": "", "UI": ""}
                }
            ],
            "model_objects": [
                {
                    "object_id": f"o{text_hash}",
                    "object_name": "Пользователь",
                    "resource_state": [
                        {"state_id": "s00001", "state_name": "неактивен"},
                        {"state_id": "s00002", "state_name": "активен"}
                    ],
                    "object_links": {"manual": "", "API": "", "UI": ""}
                },
                {
                    "object_id": f"o{int(timestamp) % 100000:05d}",
                    "object_name": "Система",
                    "resource_state": [
                        {"state_id": "s00003", "state_name": "ожидает"},
                        {"state_id": "s00004", "state_name": "обработано"}
                    ],
                    "object_links": {"manual": "", "API": "", "UI": ""}
                }
            ],
            "model_connections": [
                {
                    "connection_out": f"o{text_hash}s00001",
                    "connection_in": f"a{timestamp % 100000:05d}"
                },
                {
                    "connection_out": f"a{timestamp % 100000:05d}",
                    "connection_in": f"o{text_hash}s00002"
                }
            ]
        }
        
        return model
    
    def log_message(self, format, *args):
        """Кастомизация логов"""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server(port=5001):
    """Запуск сервера"""
    handler = SimpleAPIHandler
    
    # Ищем свободный порт
    import socket
    for p in range(port, port + 20):
        try:
            server = socketserver.TCPServer(("", p), handler)
            print(f"🚀 API запущен на порту {p}")
            print(f"📡 Эндпоинт: POST http://localhost:{p}/api/generate-model")
            print(f"📋 Логи пишутся в консоль и в файл api.log")
            print(f"🛑 Для остановки нажмите Ctrl+C")
            
            # Записываем порт в файл
            with open('api_port.txt', 'w') as f:
                f.write(str(p))
            
            server.serve_forever()
            break
        except OSError as e:
            if "Address already in use" in str(e):
                continue
            else:
                raise

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ЗАПУСК УПРОЩЕННОГО API С ВЫВОДОМ JSON В ЛОГИ")
    print("=" * 60)
    print("✅ Каждый запрос будет логироваться с полным JSON")
    print("✅ JSON выводится с форматированием (indent=2)")
    print("✅ Статистика выводится в логи")
    print("✅ Логи также пишутся в файл api.log")
    print("=" * 60)
    
    run_server()