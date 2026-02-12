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
                
                # 2. Проверяем доступность LLM (проверяем эндпоинт здоровья Ollama)
                print("   🤖 Проверяю доступность Ollama...")
                
                try:
                    import urllib.request
                    import socket
                    # Пробуем подключиться к Ollama health endpoint
                    req = urllib.request.Request("http://localhost:11434/api/tags")
                    # Устанавливаем timeout через socket
                    socket.setdefaulttimeout(5)
                    try:
                        with urllib.request.urlopen(req) as response:
                            # Если дошли сюда - Ollama доступен
                            print("   ✅ Ollama доступен")
                    finally:
                        # Всегда сбрасываем timeout
                        socket.setdefaulttimeout(None)
                except Exception as e:
                    # Ollama не доступен - возвращаем ошибку
                    error_msg = f"Ollama не доступен: {e}"
                    print(f"   ❌ {error_msg}")
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._set_cors_headers()
                    self.end_headers()
                    
                    error_response = {
                        "success": False,
                        "status": 503,
                        "error": "Ollama не доступен",
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
                print("   🤖 Отправляю запрос к LLM для анализа ТЗ...")
                print(f"   📄 Промпт для LLM (первые 500 символов):\n{prompt[:500]}...")
                llm_response = self.query_llm(prompt)
                
                actions_data = []
                
                if llm_response["success"]:
                    print("   ✅ LLM ответил успешно!")
                    print(f"   📄 Ответ LLM (первые 500 символов):\n{llm_response['response'][:500]}...")
                    print(f"   📏 Длина ответа LLM: {len(llm_response['response'])} символов")
                    
                    # 4. Парсим ответ LLM
                    actions_data = self.parse_llm_response(llm_response["response"])
                    
                    print(f"   📊 Результат парсинга: {len(actions_data)} действий")
                    
                    if actions_data:
                        print(f"   📋 LLM нашел {len(actions_data)} действий")
                        
                        # 5. Добавляем каждое действие в модель
                        for i, action_data in enumerate(actions_data):
                            print(f"   🔍 Обработка действия {i+1}/{len(actions_data)}...")
                            success = self.add_action_to_model(action_data, model_name)
                            if not success:
                                print(f"   ❌ Ошибка при обработке действия {i+1}")
                    else:
                        print("   ❌ LLM не вернул корректные действия")
                        print("   ℹ️  Возвращаю пустую модель")
                        
                        # Возвращаем успешный ответ с пустой моделью
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self._set_cors_headers()
                        self.end_headers()
                        
                        # Пустая модель
                        empty_model = {
                            "model_actions": [],
                            "model_objects": [],
                            "model_connections": []
                        }
                        
                        success_response = {
                            "success": True,
                            "model": empty_model,
                            "note": "LLM не смог извлечь действия из документа"
                        }
                        
                        self.wfile.write(json.dumps(success_response, indent=2, ensure_ascii=False).encode())
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
            "Анализируй текст ТЗ и верни JSON-массив действий. Каждое действие — объект в массиве.\n"
            "Каждый объект - это конкретная одна цель, конкретного действующего лица в конкретном месте системе\n"
            "Формат каждого объекта: {\"action_actor\": \"кто\", \"action_action\": \"что делает(глагол в настоящем времени + объект из ТЗ   - Примеры: 'создает контакт', 'редактирует документ', 'отправляет уведомление' )\", \"action_place\": \"где (Пример: на главной странице, на форме редактирования )\", \"init_states\": [(начальные состояния объектов перед действием   - Пример: [{\"object_name\": \"контакт\", \"state_name\": \"не существует\"}]  )], \"final_states\": [конечные состояния объектов после действия  - Пример: [{\"object_name\": \"контакт\", \"state_name\": \"создан\"}] ]}\n"
            "action_action должен быть строкой: 'глагол + объект'.\n"
            "init_states/final_states: массив объектов {\"object_name\": \"...\", \"state_name\": \"...\"}.\n"
            "Верни ТОЛЬКО JSON-массив без комментариев.\n\n"
            "Текст ТЗ:\n"
            f"{text[:1500]}"
            "\n\n"
            "JSON-массив действий:"
        )
        
        return prompt
    
    def query_llm(self, prompt):
        """
        Отправляет запрос к Ollama LLM (без внешних зависимостей)
        """
        try:
            # Используем встроенные модули
            import urllib.request
            import json as json_module
            
            ollama_url = "http://localhost:11434/api/generate"
            
            payload = {
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2000  # Увеличили для больших ответов
                }
            }
            
            # Создаем HTTP запрос
            data = json_module.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                ollama_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            # Отправляем запрос
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                result = json_module.loads(response_data)
                
                return {
                    "success": True,
                    "response": result.get("response", "")
                }
                
        except urllib.error.URLError as e:
            # Ollama не запущен или недоступен
            print(f"❌ Ollama недоступен: {e}")
            return {
                "success": False,
                "error": f"Ollama недоступен: {e}"
            }
        except Exception as e:
            print(f"❌ Ошибка при запросе к LLM: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fix_incomplete_json(self, json_str):
        """
        Пытается исправить неполный JSON от LLM
        """
        json_str = json_str.strip()
        
        # Если начинается с [, но не заканчивается ], добавляем ]
        if json_str.startswith('[') and not json_str.endswith(']'):
            # Ищем последнюю завершенную структуру
            brackets = 1
            last_good_index = len(json_str) - 1
            
            # Идем с конца и ищем где закрывается массив
            for i in range(len(json_str) - 1, 0, -1):
                if json_str[i] == '[':
                    brackets -= 1
                elif json_str[i] == ']':
                    brackets += 1
                
                if brackets == 0:
                    # Нашли закрывающую скобку
                    last_good_index = i
                    break
            
            # Обрезаем до последней хорошей позиции и добавляем закрывающую скобку
            if last_good_index < len(json_str) - 1:
                fixed = json_str[:last_good_index + 1] + ']'
                print(f"   🔧 Обрезал неполный JSON, добавил закрывающую ]")
                return fixed
            else:
                # Просто добавляем закрывающую скобку
                fixed = json_str + ']'
                print(f"   🔧 Добавил закрывающую ] в конец JSON")
                return fixed
        
        return json_str
    
    def _normalize_action_data(self, action_data):
        """
        Нормализует данные действия из разных форматов LLM
        """
        normalized = {}
        
        # Маппинг возможных ключей от LLM
        key_mappings = {
            "actor": "action_actor",
            "action": "action_action",
            "place": "action_place",
            "location": "action_place",
            "init_state": "init_states",
            "final_state": "final_states",
            "initial_states": "init_states",
            "final_states": "final_states"
        }
        
        # Нормализуем ключи
        for key, value in action_data.items():
            if key in key_mappings:
                normalized[key_mappings[key]] = value
            else:
                normalized[key] = value
        
        # Гарантируем обязательные поля
        if "action_actor" not in normalized:
            # Пробуем извлечь из других полей или ставим по умолчанию
            if "actor" in normalized:
                normalized["action_actor"] = normalized["actor"]
            else:
                normalized["action_actor"] = "пользователь"
        
        if "action_action" not in normalized:
            if "action" in normalized:
                normalized["action_action"] = normalized["action"]
            elif "description" in normalized:
                normalized["action_action"] = normalized["description"]
            else:
                # Пробуем создать из других полей
                normalized["action_action"] = "выполняет действие"
        
        # Преобразуем action_action из объекта в строку, если нужно
        if isinstance(normalized.get("action_action"), dict):
            action_obj = normalized["action_action"]
            if "object_name" in action_obj and "state_name" in action_obj:
                # Преобразуем объект вида {"object_name": "контакт", "state_name": "создать"}
                # в строку "создает контакт"
                object_name = action_obj["object_name"]
                state_name = action_obj["state_name"]
                
                # Простое преобразование: используем state_name как глагол
                normalized["action_action"] = f"{state_name} {object_name}"
                print(f"   🔧 Преобразовал объект action_action в строку: {normalized['action_action']}")
            else:
                # Если непонятный формат, создаем строку из JSON
                normalized["action_action"] = json.dumps(action_obj, ensure_ascii=False)
                print(f"   ⚠️  action_action в непонятном формате, преобразовал в JSON строку")
        
        # Гарантируем массивы состояний
        if "init_states" not in normalized:
            normalized["init_states"] = []
        if "final_states" not in normalized:
            normalized["final_states"] = []
        
        return normalized
    
    def parse_llm_response(self, response):
        """
        Парсит ответ LLM и извлекает массив действий
        """
        try:
            print(f"🔄 Начинаю парсинг ответа LLM...")
            print(f"📏 Длина ответа для парсинга: {len(response)} символов")
            print(f"📄 Начало ответа (первые 300 символов):\n{response[:300]}...")
            
            # Убираем возможные markdown обертки
            response = response.strip()
            if response.startswith('```json'):
                print(f"✅ Обнаружен формат ```json, удаляю обертку")
                response = response[7:]
            if response.startswith('```'):
                print(f"✅ Обнаружен формат ```, удаляю обертку")
                response = response[3:]
            if response.endswith('```'):
                print(f"✅ Обнаружен закрывающий ```, удаляю")
                response = response[:-3]
            
            # Парсим JSON
            print(f"🔄 Пытаюсь распарсить JSON...")
            data = json.loads(response)
            print(f"✅ JSON успешно распарсен, тип данных: {type(data)}")
            
            # Проверяем разные форматы ответов LLM
            if isinstance(data, list):
                # Формат 1: массив действий
                print(f"✅ Распарсено {len(data)} действий из LLM (формат: массив)")
                if data:
                    print(f"   Первое действие: {json.dumps(data[0], ensure_ascii=False)[:100]}...")
                return data
            elif isinstance(data, dict):
                print(f"ℹ️  LLM вернул объект, проверяю структуру...")
                # Формат 2: объект с полями
                if "action_actor" in data and "action_action" in data:
                    print(f"✅ Найдены поля action_actor и action_action")
                    # Преобразуем в массив действий
                    actions = []
                    if isinstance(data["action_actor"], list) and isinstance(data["action_action"], list):
                        # Создаем действия на основе actor и action
                        for i in range(min(len(data["action_actor"]), len(data["action_action"]))):
                            action = {
                                "actor": data["action_actor"][i] if i < len(data["action_actor"]) else "неизвестно",
                                "action": data["action_action"][i] if i < len(data["action_action"]) else "действие",
                                "place": "система",
                                "init_states": [],
                                "final_states": []
                            }
                            actions.append(action)
                        
                        print(f"✅ Распарсено {len(actions)} действий из LLM (формат: объект -> преобразован)")
                        return actions
                
                # Проверяем другие возможные структуры
                print(f"⚠️  LLM вернул объект с ключами: {list(data.keys())}")
                
                # Пробуем найти массив действий в разных полях
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        # Проверяем, является ли это массивом действий
                        first_item = value[0]
                        if isinstance(first_item, dict):
                            # Проверяем различные форматы действий
                            if ("action_actor" in first_item or "actor" in first_item or 
                                "action_action" in first_item or "action" in first_item):
                                print(f"✅ Найден массив действий в поле '{key}': {len(value)} элементов")
                                return value
                            # Проверяем вложенные структуры
                            for sub_key, sub_value in first_item.items():
                                if isinstance(sub_value, list) and len(sub_value) > 0:
                                    sub_first = sub_value[0]
                                    if isinstance(sub_first, dict) and ("action_actor" in sub_first or "actor" in sub_first):
                                        print(f"✅ Найден вложенный массив действий в '{key}.{sub_key}': {len(sub_value)} элементов")
                                        return sub_value
                
                # Если не нашли напрямую, ищем любые массивы объектов
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        print(f"⚠️  Найден массив в поле '{key}' (не проверена структура): {len(value)} элементов")
                        print(f"   Первый элемент: {json.dumps(value[0], ensure_ascii=False)[:100]}...")
                        # Возвращаем даже если структура не идеальная
                        return value
                
                print(f"❌ LLM вернул объект без узнаваемой структуры действий")
                return []
            else:
                print(f"❌ LLM вернул нераспознанный формат: {type(data)}")
                return []
                
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON от LLM: {e}")
            print(f"Ответ LLM (первые 500 символов): {response[:500]}...")
            print(f"Ответ LLM (последние 200 символов): ...{response[-200:] if len(response) > 200 else response}")
            
            # Пытаемся "починить" неполный JSON
            try:
                # Ищем и закрываем незакрытые массивы/объекты
                fixed_response = self._fix_incomplete_json(response)
                print(f"🔄 Пытаюсь исправить JSON...")
                data = json.loads(fixed_response)
                
                if isinstance(data, list):
                    print(f"✅ Удалось исправить JSON, найдено {len(data)} действий")
                    return data
                else:
                    print(f"❌ Исправленный JSON не является массивом")
                    return []
            except Exception as fix_error:
                print(f"❌ Не удалось исправить JSON: {fix_error}")
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
            
            # 2. Логируем полученные данные
            print(f"   🔍 Получены данные действия:")
            print(f"   Keys: {list(action_data.keys())}")
            print(f"   Data: {json.dumps(action_data, ensure_ascii=False)[:200]}...")
            
            # 3. Нормализуем ключи (обрабатываем разные форматы от LLM)
            normalized_data = self._normalize_action_data(action_data)
            print(f"   🔧 Нормализованные данные: {json.dumps(normalized_data, ensure_ascii=False)[:200]}...")
            
            # 4. Проверяем, существует ли уже такое действие
            action_id = None
            for existing_action in existing_actions:
                if (existing_action.get("action_actor") == normalized_data["action_actor"] and
                    existing_action.get("action_action") == normalized_data["action_action"] and
                    existing_action.get("action_place") == normalized_data.get("action_place", "")):
                    
                    action_id = existing_action["action_id"]
                    print(f"   🔄 Действие уже существует: {action_id}")
                    break
            
            # 5. Если действие новое, создаем его
            if not action_id:
                action_id = f"a{next_action_num:05d}"
                next_action_num += 1
                
                # Создаем действие с полями для графа
                action_label = f"{normalized_data['action_actor']} {normalized_data['action_action']}"
                if normalized_data.get("action_place"):
                    action_label += f" ({normalized_data['action_place']})"
                
                new_action = {
                    "action_id": action_id,
                    # Новая структура
                    "action_actor": normalized_data["action_actor"],
                    "action_action": normalized_data["action_action"],
                    "action_place": normalized_data.get("action_place", ""),
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
                        "actor": normalized_data["action_actor"],
                        "action": normalized_data["action_action"],
                        "place": normalized_data.get("action_place", "")
                    }
                }
                
                existing_actions.append(new_action)
                print(f"   ✅ Создано новое действие: {action_id}")
            
            # 4. Обрабатываем init_states и final_states
            all_state_pairs = []
            
            # Собираем все состояния из normalized_data
            if "init_states" in normalized_data and normalized_data["init_states"]:
                for state in normalized_data["init_states"]:
                    all_state_pairs.append({
                        "type": "init",
                        "object_name": state.get("object_name", "объект"),
                        "state_name": state.get("state_name", "начальное состояние")
                    })
                print(f"   📋 Найдено {len(normalized_data['init_states'])} начальных состояний")
            
            if "final_states" in normalized_data and normalized_data["final_states"]:
                for state in normalized_data["final_states"]:
                    all_state_pairs.append({
                        "type": "final",
                        "object_name": state.get("object_name", "объект"),
                        "state_name": state.get("state_name", "конечное состояние")
                    })
                print(f"   📋 Найдено {len(normalized_data['final_states'])} конечных состояний")
            
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