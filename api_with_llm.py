#!/usr/bin/env python3
"""
API с интеграцией LLM (Ollama) для генерации моделей
"""

import http.server
import socketserver
import json
import sys
import datetime
import os
import subprocess
import threading
import time

# Принудительно отключаем буферизацию
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

print("=" * 60)
print("🚀 API С LLM - ИНТЕГРАЦИЯ С OLLAMA")
print("=" * 60)
print("Это сообщение ДОЛЖНО быть видно сразу!")
sys.stdout.flush()

class LLMAPIHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Кастомизация логов - выводим ВСЕГДА"""
        message = f"{self.address_string()} - {format % args}"
        print(f"🔹 {message}")
        sys.stdout.flush()
    
    def do_GET(self):
        if self.path == "/api/health":
            print("📡 ОБРАБОТКА GET /api/health")
            sys.stdout.flush()
            
            # Проверяем доступность LLM
            llm_status = self.check_llm_status()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok", 
                "api": "llm",
                "llm_available": llm_status["available"],
                "llm_status": llm_status["status"]
            }).encode())
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
                sys.stdout.flush()
                
                # Проверяем доступность LLM
                llm_status = self.check_llm_status()
                if not llm_status["available"]:
                    print(f"❌ LLM недоступен: {llm_status['status']}")
                    sys.stdout.flush()
                    
                    # Возвращаем ошибку
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": False,
                        "error": f"LLM недоступен: {llm_status['status']}"
                    }).encode())
                    return
                
                print("🔄 ЗАПУСКАЮ LLM ДЛЯ АНАЛИЗА ТЗ...")
                sys.stdout.flush()
                
                # Генерируем промпт
                prompt = self.generate_prompt(text)
                
                print("🤖 ОТПРАВЛЯЮ ЗАПРОС К LLM...")
                print(f"📝 Промпт (первые 500 символов): {prompt[:500]}...")
                sys.stdout.flush()
                
                # Отправляем запрос к LLM
                llm_response = self.query_llm(prompt)
                
                if llm_response["success"]:
                    print("✅ LLM ОТВЕТИЛ УСПЕШНО!")
                    print(f"📄 Ответ LLM (первые 500 символов): {llm_response['response'][:500]}...")
                    sys.stdout.flush()
                    
                    # Парсим и валидируем ответ LLM
                    model = self.parse_llm_response(llm_response["response"])
                    
                    if model:
                        print("🎯 МОДЕЛЬ СГЕНЕРИРОВАНА LLM!")
                        sys.stdout.flush()
                        
                        # Отправляем успешный ответ
                        response = {"success": True, "model": model}
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
                    else:
                        print("❌ НЕ УДАЛОСЬ РАСПАРСИТЬ ОТВЕТ LLM")
                        sys.stdout.flush()
                        
                        # Возвращаем ошибку парсинга
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": False,
                            "error": "Не удалось распарсить ответ LLM"
                        }).encode())
                else:
                    print(f"❌ ОШИБКА LLM: {llm_response['error']}")
                    sys.stdout.flush()
                    
                    # Возвращаем ошибку LLM
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": False,
                        "error": f"Ошибка LLM: {llm_response['error']}"
                    }).encode())
                
                print("✅ ОТВЕТ ОТПРАВЛЕН")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"❌ ОШИБКА: {e}")
                import traceback
                traceback.print_exc()
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
    
    def check_llm_status(self):
        """Проверяет доступность LLM (Ollama)"""
        print("🔍 ПРОВЕРЯЮ ДОСТУПНОСТЬ LLM...")
        sys.stdout.flush()
        
        try:
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
                    print("✅ LLM ДОСТУПЕН (Ollama с llama3.2)")
                    sys.stdout.flush()
                    return {"available": True, "status": "Ollama с моделью llama3.2"}
                else:
                    print("⚠️  Ollama запущен, но модель llama3.2 не найдена")
                    sys.stdout.flush()
                    return {"available": False, "status": "Модель llama3.2 не найдена"}
            else:
                print("❌ Сервер Ollama не отвечает")
                sys.stdout.flush()
                return {"available": False, "status": "Сервер Ollama не запущен"}
                
        except subprocess.TimeoutExpired:
            print("❌ Таймаут проверки LLM")
            sys.stdout.flush()
            return {"available": False, "status": "Таймаут проверки"}
        except Exception as e:
            print(f"❌ Ошибка проверки LLM: {e}")
            sys.stdout.flush()
            return {"available": False, "status": f"Ошибка: {str(e)}"}
    
    def generate_prompt(self, text):
        """Генерирует промпт для LLM на основе ТЗ"""
        prompt_template = """Ты - аналитик процессов. Твоя задача - проанализировать техническое задание и создать формализованную модель процессов.

АНАЛИЗИРУЙ следующее техническое задание:

"""
        prompt_template += text
        prompt_template += """

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
        
        return prompt_template
    
    def query_llm(self, prompt):
        """Отправляет запрос к LLM (Ollama)"""
        print("🤖 ВЫПОЛНЯЮ ЗАПРОС К LLM...")
        sys.stdout.flush()
        
        try:
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
                "-d", json.dumps(request_data)
            ]
            
            print(f"🚀 ЗАПУСКАЮ CURL: {' '.join(curl_command[:10])}...")
            sys.stdout.flush()
            
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=30  # 30 секунд таймаут для LLM
            )
            
            if result.returncode == 0:
                print("✅ LLM ОТВЕТИЛ")
                sys.stdout.flush()
                
                try:
                    response_data = json.loads(result.stdout)
                    if "response" in response_data:
                        return {
                            "success": True,
                            "response": response_data["response"]
                        }
                    else:
                        print(f"❌ Неожиданный формат ответа LLM: {result.stdout[:200]}")
                        sys.stdout.flush()
                        return {
                            "success": False,
                            "error": "Неожиданный формат ответа LLM"
                        }
                except json.JSONDecodeError:
                    print(f"❌ Не удалось распарсить JSON от LLM: {result.stdout[:200]}")
                    sys.stdout.flush()
                    return {
                        "success": False,
                        "error": "Не удалось распарсить JSON от LLM"
                    }
            else:
                print(f"❌ Ошибка curl: {result.stderr}")
                sys.stdout.flush()
                return {
                    "success": False,
                    "error": f"Ошибка выполнения запроса: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            print("❌ Таймаут запроса к LLM (30 секунд)")
            sys.stdout.flush()
            return {
                "success": False,
                "error": "Таймаут запроса к LLM"
            }
        except Exception as e:
            print(f"❌ Ошибка при запросе к LLM: {e}")
            sys.stdout.flush()
            return {
                "success": False,
                "error": f"Ошибка: {str(e)}"
            }
    
    def parse_llm_response(self, response):
        """Парсит и валидирует ответ LLM"""
        print("🔍 ПАРСИНГ ОТВЕТА LLM...")
        sys.stdout.flush()
        
        try:
            # Ищем JSON в ответе
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print("❌ Не найден JSON в ответе LLM")
                print(f"Ответ: {response[:500]}...")
                sys.stdout.flush()
                return None
            
            json_str = response[json_start:json_end]
            model = json.loads(json_str)
            
            # Базовая валидация
            if not all(key in model for key in ["model_actions", "model_objects", "model_connections"]):
                print("❌ Неполная структура JSON")
                sys.stdout.flush()
                return None
            
            print(f"✅ JSON РАСПАРСЕН: {len(model['model_actions'])} действий, {len(model['model_objects'])} объектов, {len(model['model_connections'])} связей")
            sys.stdout.flush()
            
            return model
            
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Ответ: {response[:500]}...")
            sys.stdout.flush()
            return None
        except Exception as e:
            print(f"❌ Ошибка при парсинге: {e}")
            sys.stdout.flush()
            return None

def run_server(port=5001):
    """Запуск сервера с LLM"""
    handler = LLMAPIHandler
    
    for p in range(port, port + 20):
        try:
            server = socketserver.TCPServer(("", p), handler)
            print(f"✅ API С LLM запущен на порту {p}")
            print(f"📡 GET  http://localhost:{p}/api/health")
            print(f"📡 POST http://localhost:{p}/api/generate-model")
            print("🤖 LLM: Интегрирован с Ollama (llama3.2)")
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