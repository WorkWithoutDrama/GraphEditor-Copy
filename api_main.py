#!/usr/bin/env python3
"""
САМЫЙ ПРОСТОЙ API для тестирования вывода логов
"""

import http.server
import socketserver
import json
import sys
import datetime

# ПРИНУДИТЕЛЬНО ОТКЛЮЧАЕМ ВСЮ БУФЕРИЗАЦИЮ
# 1. Устанавливаем переменную окружения
import os
os.environ['PYTHONUNBUFFERED'] = '1'

# 2. Принудительно сбрасываем буфер sys.stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

print("=" * 60)
print("🚀 ТЕСТОВЫЙ API - ГАРАНТИРОВАННЫЙ ВЫВОД ЛОГОВ")
print("=" * 60)
print("Это сообщение ДОЛЖНО быть видно сразу!")
sys.stdout.flush()

class TestAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Кастомизация логов - выводим ВСЕГДА"""
        message = f"{self.address_string()} - {format % args}"
        print(f"🔹 {message}")
        sys.stdout.flush()
    
    def do_GET(self):
        if self.path == "/api/health":
            print("📡 ОБРАБОТКА GET /api/health")
            sys.stdout.flush()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "api": "test"}).encode())
            sys.stdout.flush()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        if self.path == "/api/generate-model":
            print("📥 ПОЛУЧЕН POST ЗАПРОС /api/generate-model")
            sys.stdout.flush()
            
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                text = data.get('text', '')
                
                print(f"📄 Текст запроса: {text[:100]}...")
                print(f"📏 Длина: {len(text)} символов")
                
                # Получаем имя модели из запроса
                model_name = data.get('model_name', 'unnamed_model')
                print(f"🏷️  Имя модели: {model_name}")
                sys.stdout.flush()
                
                # Шаг 1: Проверяем доступность LLM
                print("🔍 ПРОВЕРЯЮ ДОСТУПНОСТЬ LLM (Ollama)...")
                sys.stdout.flush()
                
                llm_available, llm_status = self.check_llm_availability()
                
                if not llm_available:
                    print(f"❌ LLM НЕДОСТУПЕН: {llm_status}")
                    print("⚠️  Использую упрощенный анализ текста")
                    sys.stdout.flush()
                    
                    # Используем упрощенный анализ если LLM недоступен
                    model = self.simple_text_analysis(text)
                else:
                    print(f"✅ LLM ДОСТУПЕН: {llm_status}")
                    print("🔄 ЗАПУСКАЮ LLM ДЛЯ АНАЛИЗА ТЗ...")
                    sys.stdout.flush()
                    
                    # Шаг 2: Генерируем промпт для LLM
                    prompt = self.generate_llm_prompt(text)
                    print(f"📝 Промпт для LLM (первые 300 символов): {prompt[:300]}...")
                    sys.stdout.flush()
                    
                    # Шаг 3: Отправляем запрос к LLM
                    print("🤖 ОТПРАВЛЯЮ ЗАПРОС К LLM...")
                    sys.stdout.flush()
                    
                    llm_response = self.query_llm(prompt)
                    
                    if llm_response["success"]:
                        print("✅ LLM ОТВЕТИЛ УСПЕШНО!")
                        print(f"📄 Ответ LLM (первые 300 символов): {llm_response['response'][:300]}...")
                        sys.stdout.flush()
                        
                        # Шаг 4: Парсим ответ LLM
                        model = self.parse_llm_response(llm_response["response"])
                        
                        if not model:
                            print("❌ НЕ УДАЛОСЬ РАСПАРСИТЬ ОТВЕТ LLМ")
                            print("⚠️  Использую упрощенный анализ")
                            sys.stdout.flush()
                            model = self.simple_text_analysis(text)
                        else:
                            print("🎯 МОДЕЛЬ СГЕНЕРИРОВАНА LLM!")
                            sys.stdout.flush()
                    else:
                        print(f"❌ ОШИБКА LLM: {llm_response['error']}")
                        print("⚠️  Использую упрощенный анализ")
                        sys.stdout.flush()
                        model = self.simple_text_analysis(text)
                
                # ВЫВОДИМ JSON - ПОСТРОЧНО И С ПРИНУДИТЕЛЬНЫМ FLUSH
                print("🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
                sys.stdout.flush()
                
                json_str = json.dumps(model, ensure_ascii=False, indent=2)
                for line in json_str.split('\n'):
                    print(line)
                    sys.stdout.flush()
                
                print("📊 СТАТИСТИКА:")
                print(f"• Действий: {len(model.get('model_actions', []))}")
                print(f"• Объектов: {len(model.get('model_objects', []))}")
                print(f"• Связей: {len(model.get('model_connections', []))}")
                sys.stdout.flush()
                
                # Сохраняем модель в файл
                saved_filename = self.save_model_to_file(model, model_name)
                if saved_filename:
                    print(f"💾 Модель сохранена: {saved_filename}")
                    response = {"success": True, "model": model, "saved_to": saved_filename}
                else:
                    print("⚠️  Не удалось сохранить модель")
                    response = {"success": True, "model": model, "save_error": "Не удалось сохранить модель"}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
                
                print("✅ ОТВЕТ ОТПРАВЛЕН")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"❌ ОШИБКА: {e}")
                sys.stdout.flush()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
                
                # ВЫВОДИМ JSON - ПОСТРОЧНО И С ПРИНУДИТЕЛЬНЫМ FLUSH
                print("🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
                sys.stdout.flush()
                
                json_str = json.dumps(model, ensure_ascii=False, indent=2)
                for line in json_str.split('\n'):
                    print(line)
                    sys.stdout.flush()
                
                print("📊 СТАТИСТИКА:")
                print(f"• Действий: {len(model.get('model_actions', []))}")
                print(f"• Объектов: {len(model.get('model_objects', []))}")
                print(f"• Связей: {len(model.get('model_connections', []))}")
                sys.stdout.flush()
                
                # Сохраняем модель в файл
                saved_filename = self.save_model_to_file(model, model_name)
                if saved_filename:
                    print(f"💾 Модель сохранена: {saved_filename}")
                    response = {"success": True, "model": model, "saved_to": saved_filename}
                else:
                    print("⚠️  Не удалось сохранить модель")
                    response = {"success": True, "model": model, "save_error": "Не удалось сохранить модель"}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
                
                print("✅ ОТВЕТ ОТПРАВЛЕН")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"❌ ОШИБКА: {e}")
                sys.stdout.flush()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def check_llm_availability(self):
        """Проверяет доступность LLM (Ollama)"""
        try:
            import subprocess
            # Проверяем, запущен ли сервер Ollama
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Проверяем наличие модели llama3.2
                if "llama3.2" in result.stdout:
                    return True, "Ollama с моделью llama3.2"
                else:
                    return False, "Модель llama3.2 не найдена"
            else:
                return False, "Сервер Ollama не запущен"
                
        except subprocess.TimeoutExpired:
            return False, "Таймаут проверки"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
    
    def generate_llm_prompt(self, text):
        """Генерирует промпт для LLM"""
        prompt = """Ты - аналитик процессов. Твоя задача - проанализировать техническое задание и создать формализованную модель процессов.

АНАЛИЗИРУЙ следующее техническое задание:

"""
        prompt += text
        prompt += """

ИНСТРУКЦИИ ПО АНАЛИЗУ:

1. ИДЕНТИФИЦИРУЙ ДЕЙСТВИЯ:
   - Найдите все ключевые действия/процессы в ТЗ
   - Каждое действие должно иметь уникальный ID в формате "a" + 5 цифр (например: a00001)
   - Название действия должно кратко описывать процесс

2. ИДЕНТИФИЦИРУЙ ОБЪЕКТЫ И ИХ СОСТОЯНИЯ:
   - Найдите все объекты системы (сущности, ресурсы)
   - Для каждого объекта определите возможные состояния
   - Каждый объект должен иметь уникальный ID в формате "o" + 5 цифр (например: o00001)
   - Каждое состояние должно иметь уникальный ID в формате "s" + 5 цифр (например: s00001)
   - Объект+состояние представляется как единое целое (например: "Пользователь: неактивен")

3. ОПРЕДЕЛИ СВЯЗИ:
   - Для каждого действия найдите:
     * Какие объекты в каких состояниях необходимы для выполнения действия (начальные условия)
     * В какие состояния переходят объекты после выполнения действия (конечные условия)
   - Связи имеют формат: "объект+состояние" → "действие" → "объект+состояние"
   - connection_out - ID источника (начальное состояние или действие)
   - connection_in - ID цели (действие или конечное состояние)

4. ФОРМАТ ВЫВОДА:
   - Выведи ТОЛЬКО валидный JSON без дополнительного текста
   - JSON должен содержать три массива: model_actions, model_objects, model_connections
   - Все ID должны быть в правильном формате
   - Если объекта/действия/состояния нет в модели - добавь его

5. ПРИМЕР ДЛЯ ТЗ "Регистрация пользователя":
   - Действие: "Регистрация пользователя" (a00001)
   - Объект: "Пользователь" (o00001) с состояниями: "незарегистрирован" (s00001), "зарегистрирован" (s00002)
   - Связь: o00001s00001 → a00001 → o00001s00002

ВЕРНИ ТОЛЬКО JSON ОТВЕТ:"""
        
        return prompt
    
    def query_llm(self, prompt):
        """Отправляет запрос к LLM (Ollama)"""
        try:
            import subprocess
            import json as json_module
            
            # Подготавливаем запрос к Ollama API
            request_data = {
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2000
                }
            }
            
            # Выполняем запрос через curl
            curl_command = [
                "curl", "-s",
                "-X", "POST",
                "http://localhost:11434/api/generate",
                "-H", "Content-Type: application/json",
                "-d", json_module.dumps(request_data)
            ]
            
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=30  # 30 секунд таймаут для LLM
            )
            
            if result.returncode == 0:
                try:
                    response_data = json_module.loads(result.stdout)
                    if "response" in response_data:
                        return {
                            "success": True,
                            "response": response_data["response"]
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Неожиданный формат ответа LLM"
                        }
                except json_module.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Не удалось распарсить JSON от LLM"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Ошибка выполнения запроса: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Таймаут запроса к LLM"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка: {str(e)}"
            }
    
    def parse_llm_response(self, response):
        """Парсит и валидирует ответ LLM, преобразуя в правильный формат"""
        try:
            # Ищем JSON в ответе
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print("❌ Не найден JSON в ответе LLM")
                print(f"Ответ: {response[:500]}...")
                return None
            
            json_str = response[json_start:json_end]
            llm_model = json.loads(json_str)
            
            print(f"🔍 Парсинг ответа LLM: найдено {len(llm_model.get('model_actions', []))} действий")
            
            # Преобразуем формат LLM в наш формат
            model = self.convert_llm_format(llm_model)
            
            # Базовая валидация
            if not all(key in model for key in ["model_actions", "model_objects", "model_connections"]):
                print(f"❌ Неполная структура после преобразования: {list(model.keys())}")
                return None
            
            print(f"✅ JSON преобразован: {len(model['model_actions'])} действий, {len(model['model_objects'])} объектов, {len(model['model_connections'])} связей")
            
            return model
            
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ: {response[:500]}...")
            return None
        except Exception as e:
            print(f"❌ Ошибка при парсинге: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def convert_llm_format(self, llm_model):
        """Преобразует формат LLM в наш формат"""
        model = {
            "model_actions": [],
            "model_objects": [],
            "model_connections": []
        }
        
        # 1. Преобразуем действия
        if "model_actions" in llm_model:
            for i, action in enumerate(llm_model["model_actions"]):
                # LLM может использовать разные ключи
                action_id = action.get("id") or action.get("action_id") or f"a{i+1:05d}"
                action_name = action.get("name") or action.get("action_name") or f"Действие {i+1}"
                
                # Если ID не в правильном формате, исправляем
                if not action_id.startswith('a'):
                    action_id = f"a{i+1:05d}"
                
                model["model_actions"].append({
                    "action_id": action_id,
                    "action_name": action_name,
                    "action_links": {
                        "manual": "",
                        "API": "",
                        "UI": ""
                    }
                })
        
        # 2. Преобразуем объекты
        if "model_objects" in llm_model:
            for i, obj in enumerate(llm_model["model_objects"]):
                # LLM может использовать разные ключи
                object_id = obj.get("id") or obj.get("object_id") or f"o{i+1:05d}"
                object_name = obj.get("type") or obj.get("object_name") or obj.get("name") or f"Объект {i+1}"
                
                # Если ID не в правильном формате, исправляем
                if not object_id.startswith('o'):
                    object_id = f"o{i+1:05d}"
                
                # Преобразуем состояния
                resource_state = []
                states = obj.get("states") or obj.get("resource_state") or []
                
                if isinstance(states, list):
                    for j, state in enumerate(states):
                        if isinstance(state, dict):
                            # Уже словарь с state_id и state_name
                            state_id = state.get("state_id") or f"s{j+1:05d}"
                            state_name = state.get("state_name") or state.get("name") or f"состояние {j+1}"
                        else:
                            # Просто строка с названием состояния
                            state_id = f"s{j+1:05d}"
                            state_name = str(state)
                        
                        resource_state.append({
                            "state_id": state_id,
                            "state_name": state_name
                        })
                
                # Если нет состояний, добавляем дефолтные
                if not resource_state:
                    resource_state = [
                        {"state_id": "s00001", "state_name": "неактивен"},
                        {"state_id": "s00002", "state_name": "активен"}
                    ]
                
                model["model_objects"].append({
                    "object_id": object_id,
                    "object_name": object_name,
                    "resource_state": resource_state
                })
        
        # 3. Преобразуем связи
        if "model_connections" in llm_model:
            for i, conn in enumerate(llm_model["model_connections"]):
                # LLM может использовать разные ключи
                connection_out = conn.get("connection_out") or conn.get("from") or conn.get("source")
                connection_in = conn.get("connection_in") or conn.get("to") or conn.get("target")
                
                if connection_out and connection_in:
                    # Исправляем ID если нужно
                    if connection_out.startswith('o') and 's' in connection_out and len(connection_out) > 6:
                        # Уже составной ID: o00001s00001
                        pass
                    elif connection_out.startswith('o') and len(connection_out) == 6:
                        # Только object_id, добавляем state_id
                        connection_out = f"{connection_out}s00001"
                    
                    if connection_in.startswith('a') and len(connection_in) == 6:
                        # Действие в правильном формате
                        pass
                    
                    model["model_connections"].append({
                        "connection_out": connection_out,
                        "connection_in": connection_in
                    })
        
        return model
    
    def save_model_to_file(self, model, model_name):
        """Сохраняет модель в файл JSON в папке models/"""
        try:
            # Создаем папку models, если она не существует
            models_dir = "models"
            if not os.path.exists(models_dir):
                os.makedirs(models_dir)
                print(f"📁 Создана папка: {models_dir}")
            
            # Создаем безопасное имя файла
            safe_name = "".join(c for c in model_name if c.isalnum() or c in "_- ").strip()
            if not safe_name:
                safe_name = "unnamed_model"
            
            filename = f"{models_dir}/{safe_name}.json"
            
            # Добавляем метаданные в модель
            model_with_metadata = {
                "version": "1.0",
                "metadata": {
                    "name": safe_name,
                    "generated_at": datetime.datetime.now().isoformat(),
                    "source": "api_main.py"
                },
                "model_actions": model.get("model_actions", []),
                "model_objects": model.get("model_objects", []),
                "model_connections": model.get("model_connections", [])
            }
            
            # Сохраняем в файл
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(model_with_metadata, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Модель сохранена в файл: {filename}")
            print(f"📊 Размер: {os.path.getsize(filename)} байт")
            
            return filename
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении модели: {e}")
            return None

    def simple_text_analysis(self, text):
        """Упрощенный анализ текста (используется если LLM недоступен)"""
        actions = []
        objects = []
        connections = []
        
        # Извлекаем действия из текста (упрощенно)
        action_keywords = ['Регистрация', 'Авторизация', 'Ввод', 'Установка', 'Выбор', 
                         'Расчет', 'Отображение', 'Добавление', 'Удаление', 'Редактирование',
                         'Поиск', 'Просмотр', 'Генерация', 'Разработка', 'Хранение']
        
        lines = text.split('\n')
        action_counter = 1
        object_counter = 1
        
        # Находим уникальные действия
        found_actions = []
        for line in lines:
            line_lower = line.lower()
            for keyword in action_keywords:
                if keyword.lower() in line_lower and keyword not in found_actions:
                    found_actions.append(keyword)
        
        # Создаем действия
        for action_name in found_actions[:5]:  # Максимум 5 действий
            actions.append({
                "action_id": f"a{action_counter:05d}",
                "action_name": f"{action_name}",
                "action_links": {"manual": "", "API": "", "UI": ""}
            })
            action_counter += 1
        
        # Если не нашли действий, создаем тестовое
        if not actions:
            actions = [{
                "action_id": "a00001",
                "action_name": "Регистрация пользователя",
                "action_links": {"manual": "", "API": "", "UI": ""}
            }]
        
        # Создаем объекты на основе текста
        object_keywords = ['пользователь', 'профиль', 'система', 'база данных', 
                         'рецепт', 'продукт', 'план', 'список', 'календарь',
                         'приложение', 'сервер', 'клиент', 'интерфейс']
        
        found_objects = []
        for line in lines:
            line_lower = line.lower()
            for obj_keyword in object_keywords:
                if obj_keyword in line_lower and obj_keyword not in found_objects:
                    found_objects.append(obj_keyword)
        
        # Создаем объекты
        for obj_name in found_objects[:3]:  # Максимум 3 объекта
            objects.append({
                "object_id": f"o{object_counter:05d}",
                "object_name": obj_name.capitalize(),
                "resource_state": [
                    {"state_id": "s00001", "state_name": "неактивен"},
                    {"state_id": "s00002", "state_name": "активен"}
                ]
            })
            object_counter += 1
        
        # Если не нашли объектов, создаем тестовые
        if not objects:
            objects = [
                {
                    "object_id": "o00001",
                    "object_name": "Пользователь",
                    "resource_state": [
                        {"state_id": "s00001", "state_name": "неактивен"},
                        {"state_id": "s00002", "state_name": "активен"}
                    ]
                }
            ]
        
        # Создаем связи между действиями и состояниями объектов
        for action in actions:
            for obj in objects:
                if obj["resource_state"]:
                    connections.append({
                        "connection_out": f"{obj['object_id']}s00001",
                        "connection_in": action["action_id"]
                    })
                    connections.append({
                        "connection_out": action["action_id"],
                        "connection_in": f"{obj['object_id']}s00002"
                    })
        
        return {
            "model_actions": actions,
            "model_objects": objects,
            "model_connections": connections
        }

def run_server(port=5001):
    """Запуск тестового сервера"""
    handler = TestAPIHandler
    
    for p in range(port, port + 20):
        try:
            server = socketserver.TCPServer(("", p), handler)
            print(f"✅ ТЕСТОВЫЙ API запущен на порту {p}")
            print(f"📡 GET  http://localhost:{p}/api/health")
            print(f"📡 POST http://localhost:{p}/api/generate-model")
            print("🛑 Для остановки: Ctrl+C")
            sys.stdout.flush()
            
            # Записываем порт
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
    run_server()