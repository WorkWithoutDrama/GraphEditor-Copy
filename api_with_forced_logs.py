#!/usr/bin/env python3
"""
API с принудительным выводом логов в консоль
"""

import http.server
import socketserver
import json
import os
import sys
import logging
import datetime

# ОТКЛЮЧАЕМ БУФЕРИЗАЦИЮ ПРИ ЗАПУСКЕ
# Это гарантирует, что логи будут видны сразу
os.environ['PYTHONUNBUFFERED'] = '1'

# Настройка логирования с принудительным выводом
class UnbufferedStreamHandler(logging.StreamHandler):
    """Обработчик логов, который принудительно сбрасывает буфер после каждой записи"""
    def emit(self, record):
        super().emit(record)
        self.flush()
        sys.stdout.flush()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        UnbufferedStreamHandler(sys.stdout),  # Используем наш unbuffered handler
        logging.FileHandler('api.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class SimpleAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def _set_cors_headers(self):
        """Устанавливает CORS заголовки"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    
    def do_OPTIONS(self):
        """Обработка CORS preflight запросов"""
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
    
    def do_GET(self):
        if self.path == "/api/health" or self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "api": "available"}).encode())
            sys.stdout.flush()  # Принудительно сбрасываем буфер
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            sys.stdout.flush()  # Принудительно сбрасываем буфер
    
    def do_POST(self):
        if self.path == "/api/generate-model":
            self.handle_generate_model()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            sys.stdout.flush()  # Принудительно сбрасываем буфер
    
    def handle_generate_model(self):
        """Обработка запроса на генерацию модели - с ПРИНУДИТЕЛЬНЫМ выводом логов"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Empty request body")
                sys.stdout.flush()
                return
            
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            text = data.get('text', '')
            
            if not text:
                self.send_error(400, "Missing 'text' parameter")
                sys.stdout.flush()
                return
            
            # ЛОГИРУЕМ ЗАПРОС (с принудительным выводом)
            logger.info("📥 ПОЛУЧЕН ЗАПРОС:")
            logger.info(f"• Текст: {text[:100]}...")
            logger.info(f"• Длина: {len(text)} символов")
            sys.stdout.flush()
            
            # Создаем модель
            logger.info("🔄 ГЕНЕРАЦИЯ МОДЕЛИ...")
            sys.stdout.flush()
            model = self._create_simple_model(text)
            
            # ВЫВОДИМ ПОЛНЫЙ JSON В ЛОГ (с принудительным выводом)
            logger.info("🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
            # Выводим JSON построчно для гарантированного вывода
            json_str = json.dumps(model, ensure_ascii=False, indent=2)
            for line in json_str.split('\n'):
                logger.info(line)
            sys.stdout.flush()
            
            # Статистика
            logger.info("📊 СТАТИСТИКА МОДЕЛИ:")
            logger.info(f"• Действий: {len(model.get('model_actions', []))}")
            logger.info(f"• Объектов: {len(model.get('model_objects', []))}")
            logger.info(f"• Связей: {len(model.get('model_connections', []))}")
            sys.stdout.flush()
            
            # Отправляем ответ
            response = {"success": True, "model": model}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            
            logger.info("✅ ОТВЕТ ОТПРАВЛЕН")
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса: {e}")
            sys.stdout.flush()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }).encode())
            sys.stdout.flush()
    
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
        sys.stdout.flush()

def run_server(port=5001):
    """Запуск сервера с принудительным выводом логов"""
    handler = SimpleAPIHandler
    
    # Ищем свободный порт
    import socket
    for p in range(port, port + 20):
        try:
            server = socketserver.TCPServer(("", p), handler)
            print(f"🚀 API с ПРИНУДИТЕЛЬНЫМИ ЛОГАМИ запущен на порту {p}")
            print(f"📡 Эндпоинт: POST http://localhost:{p}/api/generate-model")
            print(f"🔧 CORS поддержка включена")
            print(f"📋 Логи будут ВИДНЫ в консоли после каждой генерации!")
            print(f"🛑 Для остановки нажмите Ctrl+C")
            sys.stdout.flush()
            
            # Записываем порт в файл
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
    print("=" * 60)
    print("🚀 API С ГАРАНТИРОВАННЫМ ВЫВОДОМ ЛОГОВ")
    print("=" * 60)
    print("✅ Отключена буферизация (PYTHONUNBUFFERED=1)")
    print("✅ Логи выводятся ПОСТРОЧНО после каждой записи")
    print("✅ JSON модели будет ВИДЕН в консоли")
    print("✅ Статистика выводится сразу")
    print("=" * 60)
    sys.stdout.flush()
    
    run_server()