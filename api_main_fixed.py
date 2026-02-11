<COMPRESSED>
#!/usr/bin/env python3
"""
Минимальный API сервер для Graph Editor
"""

import http.server
import socketserver
import json
import os
import sys
import logging
import datetime
import time
from urllib.parse import urlparse, parse_qs

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

def write_port_to_file(port):
    """Записывает порт в файл для launch.command"""
    with open("api_port.txt", "w") as f:
        f.write(str(port))

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
            
            response = {
                "status": "healthy",
                "timestamp": datetime.datetime.now().isoformat(),
                "service": "Graph Editor API",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/api/health",
                    "generate": "/api/generate (POST)",
                    "status": "/api/status"
                }
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode())
            logger.info(f"✅ Health check - {datetime.datetime.now()}")
            
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found", "path": self.path}).encode())
    
    def do_POST(self):
        if self.path == "/api/generate-model" or self.path == "/api/generate":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                text = data.get('text', '')
                model_name = data.get('model_name', 'unnamed_model')
                
                print(f"📥 POST /api/generate-model")
                print(f"   📄 Текст: {text[:100]}...")
                print(f"   🏷️  Имя модели: {model_name}")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                
                # Вызываем простой анализ
                model = self.simple_text_analysis(text)
                
                # Сохраняем модель
                if model_name:
                    filename = self.save_model_to_file(model, model_name)
                    if filename:
                        print(f"   💾 Модель сохранена: {filename}")
                
                response = {
                    "success": True,
                    "model": model,
                    "statistics": {
                        "actions": len(model.get("model_actions", [])),
                        "objects": len(model.get("model_objects", [])),
                        "connections": len(model.get("model_connections", []))
                    }
                }
                
                self.wfile.write(json.dumps(response, indent=2, ensure_ascii=False).encode())
                print(f"   ✅ Ответ отправлен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при генерации модели: {str(e)}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "status": "error"}).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found", "path": self.path}).encode())
    
    def log_message(self, format, *args):
        """Переопределяем логирование для вывода в наш логгер"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def simple_text_analysis(self, text):
        """
        ПРОСТОЙ анализ текста ТЗ
        Возвращает структуру с action_name (старый формат)
        """
        print("🔍 АНАЛИЗ ТЕКСТА ТЗ")
        print(f"📄 Длина текста: {len(text)} символов")
        
        # Результаты
        actions = []
        objects = []
        connections = []
        
        lines = text.split('\n')
        action_counter = 1
        object_counter = 1
        
        # 1. Ищем номерированные пункты как действия
        print("🔍 Поиск действий...")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Ищем номерированные пункты (1., 2., 3.)
            if line and line[0].isdigit() and ('.' in line[:3] or ')' in line[:3]):
                # Извлекаем название пункта
                point_text = line.split('.', 1)[-1].split(')', 1)[-1].strip()
                
                if point_text and len(point_text) > 3:  # Минимальная длина
                    action_id = f"a{action_counter:05d}"
                    action_counter += 1
                    
                    action = {
                        "action_id": action_id,
                        "action_name": point_text,
                        "action_links": {
                            "manual": f"Из ТЗ: строка {i+1}",
                            "API": "",
                            "UI": ""
                        }
                    }
                    
                    actions.append(action)
                    print(f"   ✅ Найдено действие: {point_text[:50]}...")
        
        # 2. Ищем объекты
        print("\n🔍 Поиск объектов...")
        
        object_keywords = [
            'пользователь', 'администратор', 'исполнитель', 'система',
            'задача', 'документ', 'отчет', 'файл', 'уведомление',
            'статус', 'приоритет', 'база данных'
        ]
        
        text_lower = text.lower()
        unique_objects = set()
        
        for obj_keyword in object_keywords:
            if obj_keyword in text_lower:
                unique_objects.add(obj_keyword.capitalize())
        
        # Создаем объекты
        for obj_name in unique_objects:
            object_id = f"o{object_counter:05d}"
            object_counter += 1
            
            # Простые состояния
            states = [
                {"state_id": "s00001", "state_name": "неактивен"},
                {"state_id": "s00002", "state_name": "активен"}
            ]
            
            obj = {
                "object_id": object_id,
                "object_name": obj_name,
                "resource_state": states
            }
            
            objects.append(obj)
            print(f"   ✅ Найден объект: {obj_name}")
        
        # 3. Простые связи
        print("\n🔗 Создание связей...")
        
        if actions and objects:
            # Простая логика: связываем действия с объектами
            for i, action in enumerate(actions):
                for j, obj in enumerate(objects):
                    if i < len(objects):  # Простая логика связей
                        connection = {
                            "connection_out": f"{obj['object_id']}s00001",
                            "connection_in": f"{action['action_id']}"
                        }
                        connections.append(connection)
        
        # 4. Итоги
        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"   ✅ Действий: {len(actions)}")
        print(f"   ✅ Объектов: {len(objects)}")
        print(f"   ✅ Связей: {len(connections)}")
        
        # Возвращаем результат
        return {
            "model_actions": actions,
            "model_objects": objects,
            "model_connections": connections,
            "analysis_metadata": {
                "analysis_method": "simple_text_analysis",
                "text_length": len(text),
                "actions_found": len(actions),
                "objects_found": len(objects),
                "connections_created": len(connections)
            }
        }
    
    def save_model_to_file(self, model, model_name):
        """Сохраняет модель в файл JSON"""
        try:
            # Создаем папку models если ее нет
            if not os.path.exists("models"):
                os.makedirs("models")
                print("📁 Создана папка models")
            
            # Формируем полную модель с метаданными
            full_model = {
                "version": "1.0",
                "metadata": {
                    "name": model_name,
                    "generated_at": datetime.datetime.now().isoformat(),
                    "source": "api_main.py",
                    "chunks_processed": 1
                },
                "model_actions": model.get("model_actions", []),
                "model_objects": model.get("model_objects", []),
                "model_connections": model.get("model_connections", [])
            }
            
            # Сохраняем в файл
            filename = f"models/{model_name}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(full_model, f, ensure_ascii=False, indent=2)
            
            print(f"   💾 Модель сохранена: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении модели: {e}")
            return None

def run_server(port=5001):
    """Запуск тестового сервера"""
    handler = SimpleAPIHandler
    
    for p in range(port, port + 20):
        try:
            with socketserver.TCPServer(("0.0.0.0", p), handler) as httpd:
                write_port_to_file(p)
                print(f"🚀 API запущен на порту {p}")
                print(f"🔗 URL: http://localhost:{p}/api/health")
                print("📝 Логи записываются в: api.log")
                print("-" * 50)
                
                httpd.serve_forever()
                break
                
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"   ⚠️  Порт {p} занят, пробую следующий...")
                continue
            else:
                raise e

if __name__ == "__main__":
    print("🚀 ТЕСТОВЫЙ API - ГАРАНТИРОВАННЫЙ ВЫВОД ЛОГОВ")
    print("=" * 50)
    print("Это сообщение ДОЛЖНО быть видно сразу!")
    run_server()
</COMPRESSED>