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
                    
                    # Используем потоковый анализ если LLM недоступен
                    model = self.stream_text_analysis(text, model_name)
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
                            model = self.stream_text_analysis(text, model_name)
                        else:
                            print("🎯 МОДЕЛЬ СГЕНЕРИРОВАНА LLM!")
                            sys.stdout.flush()
                    else:
                        print(f"❌ ОШИБКА LLM: {llm_response['error']}")
                        print("⚠️  Использую упрощенный анализ")
                        sys.stdout.flush()
                        model = self.stream_text_analysis(text, model_name)
                
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
    
    def save_model_to_file(self, model, model_name, append=False):
        """
        Сохраняет модель в файл JSON в папке models/
        
        Args:
            model: словарь с моделью
            model_name: имя модели (имя файла)
            append: если True, добавляет к существующему файлу
        """
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
            
            if append and os.path.exists(filename):
                # Читаем существующую модель
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    
                    # Объединяем данные
                    existing_actions = existing_data.get("model_actions", [])
                    existing_objects = existing_data.get("model_objects", [])
                    existing_connections = existing_data.get("model_connections", [])
                    
                    # Убираем дубликаты по ID
                    new_actions = model.get("model_actions", [])
                    new_objects = model.get("model_objects", [])
                    new_connections = model.get("model_connections", [])
                    
                    # Объединяем уникальные элементы
                    combined_actions = self._merge_unique(existing_actions, new_actions, "action_id")
                    combined_objects = self._merge_unique(existing_objects, new_objects, "object_id")
                    combined_connections = self._merge_unique(existing_connections, new_connections, lambda x: f"{x.get('connection_out')}-{x.get('connection_in')}")
                    
                    # Обновляем метаданные
                    existing_data["metadata"]["updated_at"] = datetime.datetime.now().isoformat()
                    existing_data["metadata"]["chunks_processed"] = existing_data["metadata"].get("chunks_processed", 0) + 1
                    
                    model_with_metadata = {
                        "version": "1.0",
                        "metadata": existing_data["metadata"],
                        "model_actions": combined_actions,
                        "model_objects": combined_objects,
                        "model_connections": combined_connections
                    }
                    
                    print(f"📝 Добавляю к существующей модели (чанков: {existing_data['metadata'].get('chunks_processed', 0)})")
                    
                except Exception as e:
                    print(f"⚠️  Ошибка при чтении существующего файла: {e}")
                    append = False
            
            if not append:
                # Создаем новую модель с метаданными
                model_with_metadata = {
                    "version": "1.0",
                    "metadata": {
                        "name": safe_name,
                        "generated_at": datetime.datetime.now().isoformat(),
                        "source": "api_main.py",
                        "chunks_processed": 1
                    },
                    "model_actions": model.get("model_actions", []),
                    "model_objects": model.get("model_objects", []),
                    "model_connections": model.get("model_connections", [])
                }
            
            # Сохраняем в файл
            mode = "a" if append else "w"
            with open(filename, mode, encoding='utf-8') as f:
                if append:
                    # Перезаписываем весь файл
                    f.seek(0)
                    f.truncate()
                json.dump(model_with_metadata, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Модель сохранена в файл: {filename}")
            print(f"📊 Размер: {os.path.getsize(filename)} байт")
            
            return filename
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении модели: {e}")
            return None

    def _convert_to_enhanced_structure(self, model):
        """Преобразует старую структуру модели в новую улучшенную"""
        print("   🔄 Преобразование структуры модели...")
        
        actions = model.get("model_actions", [])
        enhanced_actions = []
        
        for i, action in enumerate(actions):
            old_name = action.get("action_name", "неизвестное действие")
            
            # Анализируем старое название для извлечения контекста
            old_name_lower = old_name.lower()
            
            # Определяем актора
            action_actor = "Пользователь"  # по умолчанию
            if "администратор" in old_name_lower:
                action_actor = "Администратор"
            elif "исполнитель" in old_name_lower:
                action_actor = "Исполнитель"
            elif "система" in old_name_lower:
                action_actor = "Система"
            
            # Определяем действие
            action_action = old_name_lower
            
            # Определяем место
            action_place = "Система"  # по умолчанию
            if "база данных" in old_name_lower:
                action_place = "База данных"
            elif "страница" in old_name_lower:
                action_place = "Главная страница"
            
            # Создаем улучшенное действие
            enhanced_action = {
                "action_id": action.get("action_id", f"a{i+1:05d}"),
                "action_actor": action_actor,
                "action_action": action_action,
                "action_place": action_place,
                "action_links": action.get("action_links", {"manual": "", "API": "", "UI": ""}),
                "source_line": 0,
                "source_text": old_name
            }
            
            enhanced_actions.append(enhanced_action)
        
        # Обновляем модель
        model["model_actions"] = enhanced_actions
        
        # Обновляем метаданные анализа
        if "analysis_metadata" in model:
            model["analysis_metadata"]["structure_converted"] = True
            model["analysis_metadata"]["converted_at"] = datetime.datetime.now().isoformat()
        
        return model

    def _merge_unique(self, list1, list2, key_func):
        """Объединяет два списка, убирая дубликаты по ключу"""
        if isinstance(key_func, str):
            # Если key_func - это строка, используем ее как ключ
            key_func = lambda x: x.get(key_func)
        
        merged = []
        seen_keys = set()
        
        # Добавляем элементы из первого списка
        for item in list1:
            key = key_func(item)
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(item)
        
        # Добавляем элементы из второго списка
        for item in list2:
            key = key_func(item)
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(item)
        
        return merged

    def enhanced_stream_analysis(self, text, model_name):
        """
        УЛУЧШЕННЫЙ потоковый анализ текста ТЗ с новой структурой
        Минимум 500 символов на чанк, инкрементальное сохранение
        """
        print("🔄 ЗАПУСК УЛУЧШЕННОГО ПОТОКОВОГО АНАЛИЗА ТЗ")
        print(f"📄 Общая длина текста: {len(text)} символов")
        
        # Разбиваем текст на абзацы
        paragraphs = text.split('\n\n')
        print(f"📋 Найдено абзацев: {len(paragraphs)}")
        
        # Объединяем абзацы в чанки (минимум 500 символов)
        chunks = []
        current_chunk = ""
        current_length = 0
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Проверяем, является ли абзац началом новой главы/раздела
            is_new_section = False
            if paragraph and paragraph[0].isdigit() and ('.' in paragraph[:10] or ')' in paragraph[:10]):
                # Номерованный пункт (1., 2., 3. и т.д.)
                is_new_section = True
            elif paragraph.lower().startswith(('глава', 'раздел', 'часть', 'функция', 'требование')):
                is_new_section = True
            
            # Если текущий чанк слишком мал, но это новый раздел - начинаем новый чанк
            if current_length < 500 and is_new_section and current_chunk:
                chunks.append(current_chunk)
                print(f"   📦 Чанк {len(chunks)}: {len(current_chunk)} символов (новый раздел)")
                current_chunk = ""
                current_length = 0
            
            # Добавляем абзац к текущему чанку
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_length += len(paragraph)
            
            # Если достигли минимального размера - сохраняем чанк
            if current_length >= 500:
                chunks.append(current_chunk)
                print(f"   📦 Чанк {len(chunks)}: {current_length} символов")
                current_chunk = ""
                current_length = 0
        
        # Добавляем последний чанк, если он не пустой
        if current_chunk:
            chunks.append(current_chunk)
            print(f"   📦 Чанк {len(chunks)}: {len(current_chunk)} символов (последний)")
        
        print(f"🎯 Итого чанков для обработки: {len(chunks)}")
        
        # Обрабатываем каждый чанк и инкрементально сохраняем
        total_actions = 0
        total_objects = 0
        total_connections = 0
        
        for i, chunk in enumerate(chunks):
            print(f"\n🔍 ОБРАБОТКА ЧАНКА {i+1}/{len(chunks)}:")
            print(f"   📏 Длина: {len(chunk)} символов")
            print(f"   📝 Содержание (первые 100 символов): {chunk[:100]}...")
            
            # Анализируем чанк с УЛУЧШЕННЫМ методом
            chunk_result = self.simple_text_analysis(chunk)
            
            # Проверяем и гарантируем новую структуру
            actions = chunk_result.get("model_actions", [])
            if actions and "action_actor" not in actions[0]:
                print(f"   ⚠️  ПРЕДУПРЕЖДЕНИЕ: Использую преобразование структуры")
                chunk_result = self._convert_to_enhanced_structure(chunk_result)
            
            # Извлекаем статистику
            chunk_actions = len(actions)
            chunk_objects = len(chunk_result.get("model_objects", []))
            chunk_connections = len(chunk_result.get("model_connections", []))
            
            total_actions += chunk_actions
            total_objects += chunk_objects
            total_connections += chunk_connections
            
            print(f"   📊 Результаты чанка: {chunk_actions} действий, {chunk_objects} объектов, {chunk_connections} связей")
            
            # Показываем пример действия, если есть
            if actions:
                first_action = actions[0]
                print(f"   📝 Пример: {first_action.get('action_actor', '?')} {first_action.get('action_action', '?')} {first_action.get('action_place', '?')}")
            
            # Инкрементально сохраняем модель
            append = (i > 0)  # Первый чанк создает файл, остальные добавляют
            saved_filename = self.save_model_to_file(chunk_result, model_name, append=append)
            
            if saved_filename:
                print(f"   💾 Сохранено в: {saved_filename} (чанк {i+1})")
            else:
                print(f"   ❌ Ошибка сохранения чанка {i+1}")
            
            # Небольшая пауза между чанками для наглядности
            if i < len(chunks) - 1:
                print("   ⏳ Переход к следующему чанку...")
        
        print(f"\n✅ УЛУЧШЕННЫЙ ПОТОКОВЫЙ АНАЛИЗ ЗАВЕРШЕН!")
        print(f"📊 ИТОГО ОБРАБОТАНО:")
        print(f"   • Чанков: {len(chunks)}")
        print(f"   • Действий: {total_actions}")
        print(f"   • Объектов: {total_objects}")
        print(f"   • Связей: {total_connections}")
        
        # Читаем финальную модель для возврата
        try:
            if saved_filename and os.path.exists(saved_filename):
                with open(saved_filename, 'r', encoding='utf-8') as f:
                    final_model = json.load(f)
                
                # Добавляем общую статистику
                final_model["metadata"]["total_chunks"] = len(chunks)
                final_model["metadata"]["total_actions"] = total_actions
                final_model["metadata"]["total_objects"] = total_objects
                final_model["metadata"]["total_connections"] = total_connections
                final_model["metadata"]["analysis_method"] = "enhanced_stream_analysis"
                
                # Пересохраняем с обновленными метаданными
                with open(saved_filename, 'w', encoding='utf-8') as f:
                    json.dump(final_model, f, ensure_ascii=False, indent=2)
                
                print(f"\n💾 ФИНАЛЬНАЯ МОДЕЛЬ СОХРАНЕНА: {saved_filename}")
                
                return final_model
        except Exception as e:
            print(f"⚠️  Ошибка чтения финальной модели: {e}")
        
        # Возвращаем последний результат как запасной вариант
        return chunk_result

    def stream_text_analysis(self, text, model_name):
        """Совместимость: вызывает улучшенную версию"""
        return self.enhanced_stream_analysis(text, model_name)

    def enhanced_stream_analysis(self, text, model_name):
        """
        Потоковый анализ текста ТЗ по частям (минимум 500 символов)
        Сохраняет результаты инкрементально
        """
        print("🔄 ЗАПУСК ПОТОКОВОГО АНАЛИЗА ТЗ")
        print(f"📄 Общая длина текста: {len(text)} символов")
        
        # Разбиваем текст на абзацы
        paragraphs = text.split('\n\n')
        print(f"📋 Найдено абзацев: {len(paragraphs)}")
        
        # Объединяем абзацы в чанки (минимум 500 символов)
        chunks = []
        current_chunk = ""
        current_length = 0
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Проверяем, является ли абзац началом новой главы/раздела
            is_new_section = False
            if paragraph and paragraph[0].isdigit() and ('.' in paragraph[:10] or ')' in paragraph[:10]):
                # Номерованный пункт (1., 2., 3. и т.д.)
                is_new_section = True
            elif paragraph.lower().startswith(('глава', 'раздел', 'часть', 'функция', 'требование')):
                is_new_section = True
            
            # Если текущий чанк слишком мал, но это новый раздел - начинаем новый чанк
            if current_length < 500 and is_new_section and current_chunk:
                chunks.append(current_chunk)
                print(f"   📦 Чанк {len(chunks)}: {len(current_chunk)} символов (новый раздел)")
                current_chunk = ""
                current_length = 0
            
            # Добавляем абзац к текущему чанку
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_length += len(paragraph)
            
            # Если достигли минимального размера - сохраняем чанк
            if current_length >= 500:
                chunks.append(current_chunk)
                print(f"   📦 Чанк {len(chunks)}: {current_length} символов")
                current_chunk = ""
                current_length = 0
        
        # Добавляем последний чанк, если он не пустой
        if current_chunk:
            chunks.append(current_chunk)
            print(f"   📦 Чанк {len(chunks)}: {len(current_chunk)} символов (последний)")
        
        print(f"🎯 Итого чанков для обработки: {len(chunks)}")
        
        # Обрабатываем каждый чанк и инкрементально сохраняем
        total_actions = 0
        total_objects = 0
        total_connections = 0
        
        for i, chunk in enumerate(chunks):
            print(f"\n🔍 ОБРАБОТКА ЧАНКА {i+1}/{len(chunks)}:")
            print(f"   📏 Длина: {len(chunk)} символов")
            print(f"   📝 Содержание (первые 100 символов): {chunk[:100]}...")
            
            # Анализируем чанк с УЛУЧШЕННЫМ методом
            chunk_result = self.simple_text_analysis(chunk)
            
            # Проверяем, что результат содержит новую структуру
            if chunk_result.get("model_actions"):
                first_action = chunk_result["model_actions"][0]
                if "action_actor" not in first_action:
                    print(f"   ⚠️  ПРЕДУПРЕЖДЕНИЕ: Результат не содержит улучшенную структуру!")
                    # Принудительно преобразуем к новой структуре
                    self._convert_to_enhanced_structure(chunk_result)
            
            # Извлекаем статистику
            chunk_actions = len(chunk_result.get("model_actions", []))
            chunk_objects = len(chunk_result.get("model_objects", []))
            chunk_connections = len(chunk_result.get("model_connections", []))
            
            total_actions += chunk_actions
            total_objects += chunk_objects
            total_connections += chunk_connections
            
            print(f"   📊 Результаты чанка: {chunk_actions} действий, {chunk_objects} объектов, {chunk_connections} связей")
            
            # Инкрементально сохраняем модель
            append = (i > 0)  # Первый чанк создает файл, остальные добавляют
            saved_filename = self.save_model_to_file(chunk_result, model_name, append=append)
            
            if saved_filename:
                print(f"   💾 Сохранено в: {saved_filename} (чанк {i+1})")
            else:
                print(f"   ❌ Ошибка сохранения чанка {i+1}")
            
            # Небольшая пауза между чанками для наглядности
            if i < len(chunks) - 1:
                print("   ⏳ Переход к следующему чанку...")
        
        print(f"\n✅ ПОТОКОВЫЙ АНАЛИЗ ЗАВЕРШЕН!")
        print(f"📊 ИТОГО ОБРАБОТАНО:")
        print(f"   • Чанков: {len(chunks)}")
        print(f"   • Действий: {total_actions}")
        print(f"   • Объектов: {total_objects}")
        print(f"   • Связей: {total_connections}")
        
        # Читаем финальную модель для возврата
        try:
            if saved_filename and os.path.exists(saved_filename):
                with open(saved_filename, 'r', encoding='utf-8') as f:
                    final_model = json.load(f)
                
                # Добавляем общую статистику
                final_model["metadata"]["total_chunks"] = len(chunks)
                final_model["metadata"]["total_actions"] = total_actions
                final_model["metadata"]["total_objects"] = total_objects
                final_model["metadata"]["total_connections"] = total_connections
                
                # Пересохраняем с обновленными метаданными
                with open(saved_filename, 'w', encoding='utf-8') as f:
                    json.dump(final_model, f, ensure_ascii=False, indent=2)
                
                return final_model
        except Exception as e:
            print(f"⚠️  Ошибка чтения финальной модели: {e}")
        
        # Возвращаем последний результат как запасной вариант
        return chunk_result

"""
Новый метод simple_text_analysis БЕЗ мок-данных
"""

import datetime

def simple_text_analysis(self, text):
    """
    РЕАЛЬНЫЙ анализ текста ТЗ БЕЗ МОК-ДАННЫХ
    
    Возвращает только то, что реально найдено в тексте.
    Если не найдено - возвращает пустые списки.
    """
    print("🔍 ЗАПУСК РЕАЛЬНОГО АНАЛИЗА ТЕКСТА ТЗ (БЕЗ МОК-ДАННЫХ)")
    print(f"📄 Длина текста: {len(text)} символов")
    
    # Результаты анализа
    actions = []
    objects = []
    connections = []
    
    lines = text.split('\n')
    action_counter = 1
    object_counter = 1
    state_counter = 1
    
    # 1. ПОИСК ДЕЙСТВИЙ (только реальные, из текста)
    print("🔍 Поиск РЕАЛЬНЫХ действий в тексте...")
    
    found_actions = []
    action_keywords = [
        'созда', 'добав', 'измен', 'удаля', 'назнача',
        'проверя', 'сохраня', 'отправля', 'получа', 'генер',
        'регистриру', 'анализиру', 'формиру', 'экспортир',
        'импортир', 'управля', 'контролиру', 'отслежива',
        'выполня', 'заверша', 'начина', 'прекраща'
    ]
    
    actor_keywords = [
        'пользователь', 'администратор', 'исполнитель',
        'система', 'разработчик', 'тестировщик',
        'клиент', 'сотрудник', 'менеджер', 'оператор'
    ]
    
    place_keywords = [
        'главная страница', 'панель управления', 'база данных',
        'личный кабинет', 'система', 'интерфейс',
        'админ панель', 'веб-интерфейс', 'мобильное приложение',
        'сервер', 'клиент', 'браузер'
    ]
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        line_lower = line.lower()
        
        # Проверяем, содержит ли строка действие
        contains_action = any(keyword in line_lower for keyword in action_keywords)
        
        if contains_action:
            # Извлекаем контекст
            actor = None
            action = line[:100]  # Берем часть строки
            place = "Система"
            
            # Определяем актора
            for actor_keyword in actor_keywords:
                if actor_keyword in line_lower:
                    actor = actor_keyword.capitalize()
                    break
            
            # Если актор не найден, ищем в контексте
            if not actor:
                # Ищем в предыдущих строках
                for j in range(max(0, i-3), i):
                    prev_line = lines[j].lower() if j < len(lines) else ""
                    for actor_keyword in actor_keywords:
                        if actor_keyword in prev_line:
                            actor = actor_keyword.capitalize()
                            break
                    if actor:
                        break
            
            if not actor:
                actor = "Пользователь"
            
            # Определяем место
            for place_keyword in place_keywords:
                if place_keyword in line_lower:
                    place = place_keyword.capitalize()
                    break
            
            # Создаем действие
            action_id = f"a{action_counter:05d}"
            action_counter += 1
            
            action_data = {
                "action_id": action_id,
                "action_actor": actor,
                "action_action": action[:50],  # Ограничиваем длину
                "action_place": place,
                "action_links": {
                    "manual": f"Из ТЗ: строка {i+1}",
                    "API": "",
                    "UI": ""
                },
                "source_line": i + 1,
                "source_text": line[:100]
            }
            
            found_actions.append(action_data)
            print(f"   ✅ Найдено действие: {actor} {action[:30]}... ({place})")
    
    actions = found_actions
    
    # 2. ПОИСК ОБЪЕКТОВ (только реальные, из текста)
    print("\n🔍 Поиск РЕАЛЬНЫХ объектов в тексте...")
    
    found_objects = []
    object_keywords = [
        'задача', 'документ', 'пользователь', 'система',
        'администратор', 'исполнитель', 'отчет', 'файл',
        'уведомление', 'комментарий', 'статус', 'приоритет',
        'база данных', 'интерфейс', 'клиент', 'сервер'
    ]
    
    # Собираем уникальные объекты из всего текста
    text_lower = text.lower()
    unique_objects = set()
    
    for obj_keyword in object_keywords:
        if obj_keyword in text_lower:
            unique_objects.add(obj_keyword.capitalize())
    
    # Преобразуем в объекты модели
    for obj_name in unique_objects:
        object_id = f"o{object_counter:05d}"
        object_counter += 1
        
        # Определяем возможные состояния на основе типа объекта
        states = []
        
        if obj_name.lower() in ['пользователь', 'администратор', 'исполнитель']:
            states = [
                {"state_id": f"s{state_counter:05d}", "state_name": "неактивен"},
                {"state_id": f"s{state_counter+1:05d}", "state_name": "активен"}
            ]
            state_counter += 2
        elif obj_name.lower() in ['задача', 'документ']:
            states = [
                {"state_id": f"s{state_counter:05d}", "state_name": "не создана"},
                {"state_id": f"s{state_counter+1:05d}", "state_name": "в работе"},
                {"state_id": f"s{state_counter+2:05d}", "state_name": "завершена"}
            ]
            state_counter += 3
        elif obj_name.lower() in ['система', 'база данных']:
            states = [
                {"state_id": f"s{state_counter:05d}", "state_name": "неактивна"},
                {"state_id": f"s{state_counter+1:05d}", "state_name": "активна"}
            ]
            state_counter += 2
        else:
            states = [
                {"state_id": f"s{state_counter:05d}", "state_name": "не создан"},
                {"state_id": f"s{state_counter+1:05d}", "state_name": "создан"}
            ]
            state_counter += 2
        
        obj_data = {
            "object_id": object_id,
            "object_name": obj_name,
            "object_type": obj_name.lower(),
            "resource_state": states,
            "possible_states": [s["state_name"] for s in states]
        }
        
        found_objects.append(obj_data)
        print(f"   ✅ Найден объект: {obj_name}")
    
    objects = found_objects
    
    # 3. СОЗДАНИЕ СВЯЗЕЙ (только если есть и действия, и объекты)
    print("\n🔗 Создание РЕАЛЬНЫХ связей...")
    
    found_connections = []
    
    if actions and objects:
        # Простая логика: связываем действия с объектами на основе контекста
        for action in actions:
            action_id = action["action_id"]
            action_text = action["action_action"].lower()
            
            for obj in objects:
                obj_name = obj["object_name"].lower()
                
                # Если название объекта упоминается в действии
                if obj_name in action_text:
                    # Связываем действие с первым состоянием объекта
                    for state in obj["resource_state"]:
                        connection_id = f"c{len(found_connections)+1:05d}"
                        
                        connection = {
                            "connection_id": connection_id,
                            "connection_out": action_id,
                            "connection_in": f"{obj['object_id']}{state['state_id']}",
                            "description": f"{action['action_actor']} {action['action_action']} → {obj['object_name']} {state['state_name']}",
                            "type": "affects"
                        }
                        
                        found_connections.append(connection)
                        print(f"   🔗 Создана связь: {action['action_actor']} {action['action_action'][:20]}... → {obj['object_name']}")
                        break
                    break
    
    connections = found_connections
    
    # 4. ИТОГОВЫЙ ОТЧЕТ
    print("\n📊 РЕЗУЛЬТАТЫ РЕАЛЬНОГО АНАЛИЗА:")
    print(f"   ✅ Действий найдено: {len(actions)}")
    print(f"   ✅ Объектов найдено: {len(objects)}")
    print(f"   ✅ Связей создано: {len(connections)}")
    
    if len(actions) == 0:
        print("\n⚠️  ВНИМАНИЕ: В тексте не найдено действий!")
        print("   Проверьте, содержит ли ТЗ описания действий (создает, изменяет, удаляет и т.д.)")
    
    # Возвращаем результат
    return {
        "model_actions": actions,
        "model_objects": objects,
        "model_connections": connections,
        "analysis_metadata": {
            "analysis_method": "real_text_analysis",
            "analyzed_at": datetime.datetime.now().isoformat(),
            "text_length": len(text),
            "lines_processed": len(lines),
            "actions_found": len(actions),
            "objects_found": len(objects),
            "connections_created": len(connections),
            "warning": "БЕЗ МОК-ДАННЫХ: все данные извлечены из текста" if actions else "ВНИМАНИЕ: действия не найдены в тексте"
        }
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