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
                
                # 1. Генерируем промпт для LLM
                prompt = self.generate_llm_prompt(text)
                print(f"   📝 Промпт для LLM (первые 200 символов): {prompt[:200]}...")
                
                # 2. Проверяем доступность LLM
                print("   🤖 Проверяю доступность LLM...")
                llm_response = self.query_llm("test")
                
                if not llm_response["success"]:
                    # LLM не доступен - возвращаем ошибку
                    error_msg = "LLM (Ollama) не доступен. Запустите Ollama и модель llama3.2"
                    print(f"   ❌ {error_msg}")
                    
                    # Всегда возвращаем 200 OK, ошибки в JSON
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._set_cors_headers()
                    self.end_headers()
                    
                    error_response = {
                        "success": False,
                        "status": 503,  # HTTP статус в JSON
                        "error": error_msg,
                        "details": "Для анализа ТЗ требуется запущенный Ollama с моделью llama3.2",
                        "help": [
                            "1. Установите Ollama: https://ollama.ai/",
                            "2. Запустите: ollama serve",
                            "3. Скачайте модель: ollama pull llama3.2",
                            "4. Попробуйте снова"
                        ]
                    }
                    
                    self.wfile.write(json.dumps(error_response, indent=2, ensure_ascii=False).encode())
                    return
                
                # 3. LLM доступен - отправляем реальный запрос
                print("   🤖 LLM доступен, отправляю запрос для анализа ТЗ...")
                llm_response = self.query_llm(prompt)
                
                actions_data = []
                
                if llm_response["success"]:
                    print("   ✅ LLM ответил успешно!")
                    print(f"   📄 Ответ LLM (первые 200 символов): {llm_response['response'][:200]}...")
                    
                    # 4. Парсим ответ LLM
                    actions_data = self.parse_llm_response(llm_response["response"])
                    
                    if actions_data:
                        print(f"   📊 LLM нашел {len(actions_data)} действий")
                        
                        # 5. Добавляем каждое действие в модель
                        for i, action_data in enumerate(actions_data):
                            print(f"   🔍 Обработка действия {i+1}/{len(actions_data)}...")
                            success = self.add_action_to_model(action_data, model_name)
                            if not success:
                                print(f"   ❌ Ошибка при обработке действия {i+1}")
                    else:
                        print("   ❌ LLM не вернул корректные действия")
                        
                        # Возвращаем ошибку парсинга (всегда 200 OK)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self._set_cors_headers()
                        self.end_headers()
                        
                        error_response = {
                            "success": False,
                            "status": 400,  # Bad Request в JSON
                            "error": "LLM вернул некорректный формат",
                            "details": "Ollama не смог проанализировать ТЗ и вернул неверный формат",
                            "llm_response_preview": llm_response["response"][:500]
                        }
                        
                        self.wfile.write(json.dumps(error_response, indent=2, ensure_ascii=False).encode())
                        return
                else:
                    print(f"   ❌ Ошибка LLM: {llm_response.get('error', 'неизвестно')}")
                    
                    # Возвращаем ошибку LLM (всегда 200 OK)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._set_cors_headers()
                    self.end_headers()
                    
                    error_response = {
                        "success": False,
                        "status": 500,  # Internal Server Error в JSON
                        "error": "Ошибка LLM",
                        "details": llm_response.get("error", "Неизвестная ошибка LLM")
                    }
                    
                    self.wfile.write(json.dumps(error_response, indent=2, ensure_ascii=False).encode())
                    return
                
                # 5. Загружаем финальную модель для ответа
                model = {
                    "model_actions": [],
                    "model_objects": [],
                    "model_connections": []
                }
                
                filename = f"models/{model_name}.json"
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        model = json.load(f)
                
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
    
    def generate_llm_prompt(self, text):
        """
        Генерирует промпт для LLM (Ollama) для анализа ТЗ
        """
        prompt = (
            "Ты — высококвалифицированный архитектор систем. Твоя задача — "
            "проанализировать предоставленный текст технического задания (ТЗ) и "
            "сформировать список действий системы в виде **JSON-массива**.\n\n"
            "**ФОРМАТ КАЖДОГО ДЕЙСТВИЯ:**\n"
            "{\n"
            "  \"action_actor\": \"пользователь\" | \"система\" | \"администратор\" | \"незарегистрированный пользователь\" | ...,\n"
            "  \"action_action\": \"глагол + объект\" (например: \"создает задачу\", \"изменяет статус\"),\n"
            "  \"action_place\": \"где происходит действие\" (опционально),\n"
            "  \"init_states\": [\n"
            "    {\"object_name\": \"имя объекта\", \"state_name\": \"необходимое состояние\"},\n"
            "    ...\n"
            "  ],\n"
            "  \"final_states\": [\n"
            "    {\"object_name\": \"имя объекта\", \"state_name\": \"результирующее состояние\"},\n"
            "    ...\n"
            "  ]\n"
            "}\n\n"
            "**ПРАВИЛА:**\n"
            "1. action_actor: кто инициирует действие\n"
            "   - 'пользователь' / 'незарегистрированный пользователь' / 'пользователь с ролью администратор' / 'система'\n"
            "2. action_action: глагол + объект (что делается)\n"
            "3. action_place: где происходит (если можно определить)\n"
            "4. init_states: состояния объектов, необходимые для действия\n"
            "5. final_states: состояния объектов после действия\n\n"
            "**ТЕКСТ ТЗ ДЛЯ АНАЛИЗА:**\n"
            f"{text[:2000]}"  # Ограничиваем длину\n\n"
            "**ВЫВЕДИ ТОЛЬКО JSON-МАССИВ БЕЗ КОММЕНТАРИЕВ:**"
        )
        
        return prompt
    
    def query_llm(self, prompt):
        """
        Отправляет запрос к Ollama LLM
        """
        try:
            import requests
            
            ollama_url = "http://localhost:11434/api/generate"
            
            payload = {
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1000
                }
            }
            
            response = requests.post(ollama_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", "")
                }
            else:
                print(f"❌ Ошибка LLM: {response.status_code}")
                return {
                    "success": False,
                    "error": f"LLM ошибка: {response.status_code}"
                }
                
        except Exception as e:
            print(f"❌ Ошибка при запросе к LLM: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def parse_llm_response(self, response):
        """
        Парсит ответ LLM и извлекает массив действий
        """
        try:
            # Убираем возможные markdown обертки
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            
            # Парсим JSON
            actions = json.loads(response)
            
            if isinstance(actions, list):
                print(f"✅ Распарсено {len(actions)} действий из LLM")
                return actions
            else:
                print(f"❌ LLM вернул не массив: {type(actions)}")
                return []
                
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON от LLM: {e}")
            print(f"Ответ LLM: {response[:200]}...")
            return []
        except Exception as e:
            print(f"❌ Ошибка при парсинге LLM ответа: {e}")
            return []
    
    def add_action_to_model(self, action_data, model_name):
        """
        Добавляет действие в модель с правильными ID и структурой
        
        action_data: {
            "action_actor": "пользователь",
            "action_action": "создает задачу",
            "action_place": "главная страница",
            "init_states": [{"object_name": "пользователь", "state_name": "авторизован"}],
            "final_states": [{"object_name": "задача", "state_name": "создана"}]
        }
        """
        try:
            # 1. Загружаем существующую модель или создаем новую
            filename = f"models/{model_name}.json"
            
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    model = json.load(f)
                
                # Извлекаем существующие данные
                existing_actions = model.get("model_actions", [])
                existing_objects = model.get("model_objects", [])
                existing_connections = model.get("model_connections", [])
                
                # Определяем следующий ID действий
                if existing_actions:
                    last_action_id = existing_actions[-1]["action_id"]
                    next_action_num = int(last_action_id[1:]) + 1
                else:
                    next_action_num = 1
            else:
                # Создаем новую модель
                model = {
                    "version": "1.0",
                    "metadata": {
                        "name": model_name,
                        "generated_at": datetime.datetime.now().isoformat(),
                        "source": "api_main.py",
                        "chunks_processed": 1
                    },
                    "model_actions": [],
                    "model_objects": [],
                    "model_connections": []
                }
                existing_actions = []
                existing_objects = []
                existing_connections = []
                next_action_num = 1
            
            # 2. Проверяем, существует ли уже такое действие
            action_id = None
            for existing_action in existing_actions:
                if (existing_action.get("action_actor") == action_data["action_actor"] and
                    existing_action.get("action_action") == action_data["action_action"] and
                    existing_action.get("action_place") == action_data.get("action_place", "")):
                    
                    action_id = existing_action["action_id"]
                    print(f"   🔄 Действие уже существует: {action_id}")
                    break
            
            # 3. Если действие новое, создаем его
            if not action_id:
                action_id = f"a{next_action_num:05d}"
                next_action_num += 1
                
                # Создаем действие с полями для графа
                action_label = f"{action_data['action_actor']} {action_data['action_action']}"
                if action_data.get("action_place"):
                    action_label += f" ({action_data['action_place']})"
                
                new_action = {
                    "action_id": action_id,
                    # Новая структура
                    "action_actor": action_data["action_actor"],
                    "action_action": action_data["action_action"],
                    "action_place": action_data.get("action_place", ""),
                    # Совместимость со старым кодом (для graph-manager.js)
                    "action_name": action_label,  # ← ДЛЯ ГРАФА!
                    "action_links": {
                        "manual": "Из LLM анализа",
                        "API": "",
                        "UI": ""
                    },
                    # Дополнительные поля для графа
                    "graph_data": {
                        "id": action_id,
                        "label": action_label,
                        "type": "action",
                        "actor": action_data["action_actor"],
                        "action": action_data["action_action"],
                        "place": action_data.get("action_place", "")
                    }
                }
                
                existing_actions.append(new_action)
                print(f"   ✅ Создано новое действие: {action_id}")
            
            # 4. Обрабатываем init_states и final_states
            all_state_pairs = []
            
            # Собираем все состояния из action_data
            if "init_states" in action_data:
                for state in action_data["init_states"]:
                    all_state_pairs.append({
                        "type": "init",
                        "object_name": state["object_name"],
                        "state_name": state["state_name"]
                    })
            
            if "final_states" in action_data:
                for state in action_data["final_states"]:
                    all_state_pairs.append({
                        "type": "final",
                        "object_name": state["object_name"],
                        "state_name": state["state_name"]
                    })
            
            # 5. Для каждого состояния находим или создаем объект и состояние
            for state_pair in all_state_pairs:
                obj_name = state_pair["object_name"]
                state_name = state_pair["state_name"]
                
                # Ищем существующий объект
                obj_found = None
                obj_index = -1
                
                for i, obj in enumerate(existing_objects):
                    if obj["object_name"].lower() == obj_name.lower():
                        obj_found = obj
                        obj_index = i
                        break
                
                # Если объект не найден, создаем новый
                if not obj_found:
                    # Определяем следующий ID объекта
                    if existing_objects:
                        last_obj_id = existing_objects[-1]["object_id"]
                        next_obj_num = int(last_obj_id[1:]) + 1
                    else:
                        next_obj_num = 1
                    
                    obj_id = f"o{next_obj_num:05d}"
                    
                    new_obj = {
                        "object_id": obj_id,
                        "object_name": obj_name,
                        "resource_state": []
                    }
                    
                    existing_objects.append(new_obj)
                    obj_found = new_obj
                    obj_index = len(existing_objects) - 1
                    print(f"   ✅ Создан новый объект: {obj_name} ({obj_id})")
                
                # Ищем существующее состояние в объекте
                state_found = False
                state_id = None
                
                for state in obj_found["resource_state"]:
                    if state["state_name"].lower() == state_name.lower():
                        state_found = True
                        state_id = state["state_id"]
                        break
                
                # Если состояние не найдено, создаем новое
                if not state_found:
                    # Определяем следующий ID состояния
                    if obj_found["resource_state"]:
                        last_state_id = obj_found["resource_state"][-1]["state_id"]
                        next_state_num = int(last_state_id[1:]) + 1
                    else:
                        next_state_num = 1
                    
                    state_id = f"s{next_state_num:05d}"
                    
                    new_state = {
                        "state_id": state_id,
                        "state_name": state_name
                    }
                    
                    existing_objects[obj_index]["resource_state"].append(new_state)
                    print(f"   ✅ Добавлено новое состояние: {obj_name}.{state_name} ({state_id})")
                
                # 6. Создаем связь
                connection_id = None
                
                if state_pair["type"] == "init":
                    # init_state → action
                    connection_id = f"c{len(existing_connections) + 1:05d}"
                    connection = {
                        "connection_id": connection_id,
                        "connection_out": f"{obj_found['object_id']}{state_id}",
                        "connection_in": action_id,
                        "description": f"{obj_name} {state_name} → {action_data['action_actor']} {action_data['action_action']}",
                        "type": "triggers"
                    }
                else:  # final
                    # action → final_state
                    connection_id = f"c{len(existing_connections) + 1:05d}"
                    connection = {
                        "connection_id": connection_id,
                        "connection_out": action_id,
                        "connection_in": f"{obj_found['object_id']}{state_id}",
                        "description": f"{action_data['action_actor']} {action_data['action_action']} → {obj_name} {state_name}",
                        "type": "results_in"
                    }
                
                # Проверяем, не существует ли уже такая связь
                connection_exists = False
                for conn in existing_connections:
                    if (conn["connection_out"] == connection["connection_out"] and
                        conn["connection_in"] == connection["connection_in"]):
                        connection_exists = True
                        break
                
                if not connection_exists:
                    existing_connections.append(connection)
                    print(f"   🔗 Создана связь: {connection['description']}")
            
            # 7. Обновляем модель
            model["model_actions"] = existing_actions
            model["model_objects"] = existing_objects
            model["model_connections"] = existing_connections
            
            # 8. Сохраняем модель
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(model, f, ensure_ascii=False, indent=2)
            
            print(f"   💾 Модель обновлена: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при добавлении действия в модель: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def simple_text_analysis(self, text):
        """
        УПРАЗДНЕН - теперь используем LLM анализ
        """
        print("⚠️  simple_text_analysis УПРАЗДНЕН")
        print("   Используйте LLM анализ через generate_llm_prompt()")
        return {
            "model_actions": [],
            "model_objects": [],
            "model_connections": [],
            "analysis_metadata": {
                "analysis_method": "deprecated",
                "warning": "Используйте LLM анализ"
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