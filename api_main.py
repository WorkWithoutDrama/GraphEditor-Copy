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

    def simple_text_analysis(self, text):
        """Улучшенный анализ текста ТЗ с детализированной структурой"""
        print("🔍 ЗАПУСК УЛУЧШЕННОГО АНАЛИЗА ТЕКСТА ТЗ")
        print(f"📄 Длина текста: {len(text)} символов")
        
        actions = []
        objects = []
        connections = []
        
        lines = text.split('\n')
        action_counter = 1
        object_counter = 1
        state_counter = 1
        
        # Словари для анализа контекста
        actors = {
            'пользователь': 'Пользователь',
            'администратор': 'Администратор', 
            'исполнитель': 'Исполнитель',
            'система': 'Система',
            'разработчик': 'Разработчик',
            'тестировщик': 'Тестировщик'
        }
        
        actions_dict = {
            'созда': ('создает', 'создать', 'создание'),
            'добав': ('добавляет', 'добавить', 'добавление'),
            'измен': ('изменяет', 'изменить', 'изменение'),
            'удаля': ('удаляет', 'удалить', 'удаление'),
            'назнача': ('назначает', 'назначить', 'назначение'),
            'проверя': ('проверяет', 'проверить', 'проверка'),
            'сохраня': ('сохраняет', 'сохранить', 'сохранение'),
            'отправля': ('отправляет', 'отправить', 'отправка'),
            'получа': ('получает', 'получить', 'получение'),
            'генер': ('генерирует', 'генерировать', 'генерация')
        }
        
        places = {
            'главная страница': 'Главная страница',
            'панель управления': 'Панель управления',
            'база данных': 'База данных',
            'личный кабинет': 'Личный кабинет',
            'система': 'Система',
            'интерфейс': 'Интерфейс',
            'админ панель': 'Админ панель'
        }
        
        # 1. Поиск и анализ действий с контекстом
        print("🔍 Поиск действий с контекстом...")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Анализ номерированных пунктов
            if line[0].isdigit() and ('.' in line[:3] or ')' in line[:3]):
                # Извлекаем текст пункта
                point_text = line.split('.', 1)[-1].split(')', 1)[-1].strip()
                
                # Определяем актора (кто выполняет действие)
                action_actor = "Пользователь"  # значение по умолчанию
                for actor_key, actor_name in actors.items():
                    if actor_key in line_lower:
                        action_actor = actor_name
                        break
                
                # Определяем действие (что делает)
                action_action = point_text.lower()
                for action_key, action_variants in actions_dict.items():
                    if any(variant in line_lower for variant in action_variants):
                        # Берем первое совпадение
                        for variant in action_variants:
                            if variant in line_lower:
                                action_action = variant
                                break
                        break
                
                # Определяем место (где происходит)
                action_place = "Система"  # значение по умолчанию
                for place_key, place_name in places.items():
                    if place_key in line_lower:
                        action_place = place_name
                        break
                
                # Создаем детализированное действие
                action_id = f"a{action_counter:05d}"
                action_counter += 1
                
                actions.append({
                    "action_id": action_id,
                    "action_actor": action_actor,
                    "action_action": action_action,
                    "action_place": action_place,
                    "action_links": {
                        "manual": f"Из ТЗ: строка {i+1}",
                        "API": "",
                        "UI": ""
                    },
                    "source_line": i + 1,
                    "source_text": line[:100]
                })
                
                print(f"   ✅ Действие: {action_actor} {action_action} {action_place}")
            
            # Анализ неформатированных действий
            elif any(keyword in line_lower for keyword in ['требуется', 'нужно', 'должен', 'следует', 'может']):
                # Определяем актора
                action_actor = "Пользователь"
                for actor_key, actor_name in actors.items():
                    if actor_key in line_lower:
                        action_actor = actor_name
                        break
                
                # Определяем действие
                action_action = "выполняет действие"
                words = line_lower.split()
                for j, word in enumerate(words):
                    if word in ['требуется', 'нужно', 'должен', 'следует', 'может'] and j + 1 < len(words):
                        # Берем следующие 2-3 слова как действие
                        action_words = words[j+1:j+4]
                        action_action = ' '.join(action_words)
                        break
                
                # Определяем место
                action_place = "Система"
                for place_key, place_name in places.items():
                    if place_key in line_lower:
                        action_place = place_name
                        break
                
                # Создаем действие
                action_id = f"a{action_counter:05d}"
                action_counter += 1
                
                actions.append({
                    "action_id": action_id,
                    "action_actor": action_actor,
                    "action_action": action_action,
                    "action_place": action_place,
                    "action_links": {
                        "manual": f"Из ТЗ: строка {i+1}",
                        "API": "",
                        "UI": ""
                    },
                    "source_line": i + 1,
                    "source_text": line[:100]
                })
                
                print(f"   ✅ Действие: {action_actor} {action_action} {action_place}")
        
        # 2. Поиск и классификация объектов
        print("\n🔍 Поиск и классификация объектов...")
        
        object_types = {
            'пользователь': {
                'name': 'Пользователь',
                'states': ['неактивен', 'активен', 'зарегистрирован', 'авторизован']
            },
            'администратор': {
                'name': 'Администратор',
                'states': ['не назначен', 'назначен', 'активен']
            },
            'исполнитель': {
                'name': 'Исполнитель',
                'states': ['свободен', 'назначен', 'работает', 'завершил']
            },
            'задача': {
                'name': 'Задача',
                'states': ['новая', 'в работе', 'на проверке', 'завершена', 'отменена']
            },
            'система': {
                'name': 'Система',
                'states': ['неактивна', 'активна', 'в работе', 'остановлена']
            },
            'база данных': {
                'name': 'База данных',
                'states': ['не создана', 'создана', 'обновляется', 'доступна']
            },
            'файл': {
                'name': 'Файл',
                'states': ['не загружен', 'загружен', 'обрабатывается', 'готов']
            },
            'отчет': {
                'name': 'Отчет',
                'states': ['не создан', 'создается', 'готов', 'отправлен']
            },
            'уведомление': {
                'name': 'Уведомление',
                'states': ['не отправлено', 'отправлено', 'прочитано', 'обработано']
            }
        }
        
        found_objects = {}
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            for obj_type, obj_info in object_types.items():
                if obj_type in line_lower:
                    if obj_type not in found_objects:
                        found_objects[obj_type] = {
                            'lines': [],
                            'states': obj_info['states'],
                            'name': obj_info['name']
                        }
                    found_objects[obj_type]['lines'].append(i + 1)
        
        # Создаем объекты с состояниями
        for obj_type, obj_data in found_objects.items():
            object_id = f"o{object_counter:05d}"
            object_counter += 1
            
            # Создаем состояния объекта
            states = []
            for j, state_name in enumerate(obj_data['states'], 1):
                states.append({
                    "state_id": f"s{j:05d}",
                    "state_name": state_name
                })
            
            objects.append({
                "object_id": object_id,
                "object_name": obj_data['name'],
                "object_type": obj_type,
                "resource_state": states,
                "found_in_lines": obj_data['lines'],
                "possible_states": obj_data['states']
            })
            
            print(f"   ✅ Объект: {obj_data['name']} (тип: {obj_type}, строки: {obj_data['lines']})")
        
        # 3. Создание связей между действиями и объектами
        print("\n🔍 Создание контекстных связей...")
        
        for action in actions:
            action_line = action.get('source_line', 0)
            action_actor = action.get('action_actor', '')
            action_action = action.get('action_action', '')
            
            # Ищем объекты, связанные с этим действием
            for obj in objects:
                obj_lines = obj.get('found_in_lines', [])
                
                # Проверяем, упоминается ли объект в той же строке или рядом
                for obj_line in obj_lines:
                    if abs(obj_line - action_line) <= 2:  # В пределах 2 строк
                        # Определяем подходящие состояния для связи
                        obj_states = obj.get('resource_state', [])
                        
                        # Связь: объект в начальном состоянии -> действие
                        for state in obj_states:
                            state_name = state.get('state_name', '').lower()
                            
                            # Определяем, является ли состояние "начальным"
                            if any(start_word in state_name for start_word in ['не', 'новая', 'свободен', 'неактивен']):
                                connections.append({
                                    "connection_out": f"{obj['object_id']}{state['state_id']}",
                                    "connection_in": action["action_id"],
                                    "description": f"{obj['object_name']} {state['state_name']} -> {action_actor} {action_action}",
                                    "type": "triggers"
                                })
                            # Определяем, является ли состояние "конечным"
                            elif any(end_word in state_name for end_word in ['создан', 'активен', 'готов', 'завершен']):
                                connections.append({
                                    "connection_out": action["action_id"],
                                    "connection_in": f"{obj['object_id']}{state['state_id']}",
                                    "description": f"{action_actor} {action_action} -> {obj['object_name']} {state['state_name']}",
                                    "type": "results_in"
                                })
        
        # 4. Если действий мало, создаем базовую структуру
        if len(actions) < 2:
            print("⚠️  Создаю базовую структуру...")
            
            # Базовые действия из заголовка
            title = ""
            for line in lines:
                if "техническое задание" in line.lower() or "тз" in line.lower():
                    title = line.strip()
                    break
            
            if not title and lines:
                title = lines[0]
            
            # Создаем базовое действие
            if title:
                actions = [{
                    "action_id": "a00001",
                    "action_actor": "Разработчик",
                    "action_action": "разрабатывает систему",
                    "action_place": "Система",
                    "action_links": {
                        "manual": f"Из ТЗ: {title[:50]}...",
                        "API": "",
                        "UI": ""
                    },
                    "source_line": 1,
                    "source_text": title[:100]
                }]
            
            # Создаем базовые объекты
            if not objects:
                objects = [
                    {
                        "object_id": "o00001",
                        "object_name": "Система",
                        "object_type": "система",
                        "resource_state": [
                            {"state_id": "s00001", "state_name": "не разработана"},
                            {"state_id": "s00002", "state_name": "в разработке"},
                            {"state_id": "s00003", "state_name": "разработана"}
                        ],
                        "possible_states": ["не разработана", "в разработке", "разработана"]
                    },
                    {
                        "object_id": "o00002",
                        "object_name": "Пользователь",
                        "object_type": "пользователь",
                        "resource_state": [
                            {"state_id": "s00001", "state_name": "не зарегистрирован"},
                            {"state_id": "s00002", "state_name": "зарегистрирован"},
                            {"state_id": "s00003", "state_name": "активен"}
                        ],
                        "possible_states": ["не зарегистрирован", "зарегистрирован", "активен"]
                    }
                ]
                
                # Базовые связи
                connections = [
                    {
                        "connection_out": "o00001s00001",
                        "connection_in": "a00001",
                        "description": "Система не разработана -> Разработчик разрабатывает систему",
                        "type": "triggers"
                    },
                    {
                        "connection_out": "a00001",
                        "connection_in": "o00001s00003",
                        "description": "Разработчик разрабатывает систему -> Система разработана",
                        "type": "results_in"
                    }
                ]
        
        print(f"\n📊 РЕЗУЛЬТАТЫ УЛУЧШЕННОГО АНАЛИЗА:")
        print(f"   • Действий: {len(actions)}")
        print(f"   • Объектов: {len(objects)}")
        print(f"   • Связей: {len(connections)}")
        
        if actions:
            print(f"\n📝 ПРИМЕРЫ ДЕЙСТВИЙ:")
            for action in actions[:3]:  # Первые 3 действия
                print(f"   • {action['action_actor']} {action['action_action']} {action['action_place']}")
        
        if objects:
            print(f"\n🏛️  ПРИМЕРЫ ОБЪЕКТОВ:")
            for obj in objects[:3]:  # Первые 3 объекта
                states = [s['state_name'] for s in obj.get('resource_state', [])[:2]]
                print(f"   • {obj['object_name']} (состояния: {', '.join(states)}...)")
        
        return {
            "model_actions": actions,
            "model_objects": objects,
            "model_connections": connections,
            "analysis_metadata": {
                "total_lines": len(lines),
                "found_actions": len(actions),
                "found_objects": len(objects),
                "found_connections": len(connections),
                "analysis_method": "enhanced_text_analysis",
                "timestamp": datetime.datetime.now().isoformat()
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