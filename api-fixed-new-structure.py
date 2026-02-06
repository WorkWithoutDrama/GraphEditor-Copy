#!/usr/bin/env python3
"""
AI API Server для Graph Editor
Версия с исправленным промптом согласно требованиям
"""

import http.server
import socketserver
import json
import os
import logging
from typing import Dict, Any
import urllib.request
import urllib.error
import time
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMClient:
    """Клиент для работы с LLM (Ollama/DeepSeek)"""
    
    def __init__(self, provider: str = "ollama"):
        """
        Инициализация LLM клиента
        
        Args:
            provider: Поставщик LLM ("ollama" или "deepseek")
        """
        self.provider = provider.lower()
        
        # Конфигурация для разных провайдеров
        self.config = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama3.2",
                "endpoint": "/api/generate"
            },
            "deepseek": {
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "api_key_env": "DEEPSEEK_API_KEY"
            }
        }
        
        if self.provider not in self.config:
            raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
    
    def generate_model(self, text: str) -> Dict:
        """
        Генерирует модель системы на основе текста ТЗ
        
        Args:
            text: Текст технического задания
            
        Returns:
            Словарь с моделью системы в новом формате
        """
        if self.provider == "ollama":
            return self._generate_with_ollama_fixed(text)
        elif self.provider == "deepseek":
            return self._generate_with_deepseek_fixed(text)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
    
    def _generate_with_ollama_fixed(self, text: str) -> Dict:
        """Генерация модели с использованием Ollama - исправленный промпт"""
        config = self.config["ollama"]
        
        # ИСПРАВЛЕННЫЙ ПРОМПТ согласно требованиям
        prompt = f"""Ты — архитектор систем. Проанализируй описание действия и создай модель в формате JSON.

ТЕКСТ ОПИСАНИЯ:
{text}

ТРЕБОВАНИЯ:
1. Найди ОДНО основное действие в описании
2. Определи список начальных условий (объекты и их состояния), необходимых для выполнения действия
3. Определи список конечных условий (объекты и их состояния), наступающих после выполнения действия
4. Если действия, объекта или его состояния еще нет в модели - добавь их
5. Сформируй "model_connections" для связей между действиями и состояниями

ФОРМАТ JSON:
{{
  "model_actions": [
    {{
      "action_id": "a12345",
      "action_name": "Название действия",
      "action_links": {{
        "manual": "",
        "API": "",
        "UI": ""
      }}
    }}
  ],
  "model_objects": [
    {{
      "object_id": "o12345",
      "object_name": "Название объекта",
      "resource_state": [
        {{"state_id": "s00000", "state_name": "null"}},
        {{"state_id": "s12345", "state_name": "состояние объекта"}}
      ],
      "object_links": {{
        "manual": "",
        "API": "",
        "UI": ""
      }}
    }}
  ],
  "model_connections": [
    {{
      "connection_out": "идентификатор_источника",
      "connection_in": "идентификатор_цели"
    }}
  ]
}}

ПРАВИЛА ДЛЯ ОТРИСОВКИ ГРАФА:
1. Действия отрисовываются в ПРЯМОУГОЛЬНИКАХ
2. Объект + состояние отрисовывается в ОВАЛЕ
3. Стрелки соответствуют "connection_in" (начало) и "connection_out" (конец)
4. connection_in всегда использует составной ID: object_id + state_id (пример: o12345s12345)

ИДЕНТИФИКАТОРЫ:
1. action_id: "a" + 5 цифр (пример: "a12345")
2. object_id: "o" + 5 цифр (пример: "o12345")
3. state_id: "s" + 5 цифр (пример: "s12345")

ПРИМЕР ДЛЯ "Пользователь регистрируется в системе":
{{
  "model_actions": [
    {{
      "action_id": "a00001",
      "action_name": "Регистрация пользователя",
      "action_links": {{"manual": "", "API": "", "UI": ""}}
    }}
  ],
  "model_objects": [
    {{
      "object_id": "o00001",
      "object_name": "Пользователь",
      "resource_state": [
        {{"state_id": "s00000", "state_name": "null"}},
        {{"state_id": "s00001", "state_name": "незарегистрирован"}},
        {{"state_id": "s00002", "state_name": "зарегистрирован"}}
      ],
      "object_links": {{"manual": "", "API": "", "UI": ""}}
    }},
    {{
      "object_id": "o00002",
      "object_name": "Система",
      "resource_state": [
        {{"state_id": "s00000", "state_name": "null"}},
        {{"state_id": "s00003", "state_name": "ожидает регистрации"}},
        {{"state_id": "s00004", "state_name": "пользователь зарегистрирован"}}
      ],
      "object_links": {{"manual": "", "API": "", "UI": ""}}
    }}
  ],
  "model_connections": [
    {{
      "connection_out": "o00001s00001",
      "connection_in": "a00001"
    }},
    {{
      "connection_out": "a00001",
      "connection_in": "o00001s00002"
    }},
    {{
      "connection_out": "a00001",
      "connection_in": "o00002s00004"
    }}
  ]
}}

Верни только JSON без пояснений."""

        try:
            url = f"{config['base_url']}{config['endpoint']}"
            data = {
                "model": config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Извлекаем JSON из ответа LLM
                response_text = result.get("response", "")
                
                # Пытаемся найти JSON в ответе
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        model = json.loads(json_match.group())
                        return {"success": True, "model": model}
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON: {e}")
                        return {"success": False, "error": f"Ошибка парсинга JSON: {e}"}
                else:
                    # Если JSON не найден, возвращаем как есть
                    try:
                        model = json.loads(response_text)
                        return {"success": True, "model": model}
                    except:
                        return {"success": False, "error": "LLM не вернул валидный JSON"}
                        
        except urllib.error.URLError as e:
            logger.error(f"Ошибка соединения с Ollama: {e}")
            return {"success": False, "error": f"Ошибка соединения с Ollama: {e}"}
        except Exception as e:
            logger.error(f"Ошибка при генерации модели: {e}")
            return {"success": False, "error": f"Ошибка при генерации модели: {e}"}
    
    def _generate_with_deepseek_fixed(self, text: str) -> Dict:
        """Генерация модели с использованием DeepSeek - исправленный промпт"""
        config = self.config["deepseek"]
        
        # Исправленный промпт для DeepSeek
        prompt = f"""Ты — архитектор систем. Проанализируй описание действия и создай модель в формате JSON.

Текст: {text}

Верни только JSON в формате:
{{
  "model_actions": [],
  "model_objects": [],
  "model_connections": []
}}

Правила:
1. Найди основное действие
2. Определи начальные и конечные условия (объекты + состояния)
3. Добавь недостающие объекты/состояния
4. connection_in использует формат: object_id + state_id
"""
        
        try:
            import os
            api_key = os.environ.get(config["api_key_env"])
            if not api_key:
                raise ValueError(f"Не установлен API ключ для DeepSeek в переменной {config['api_key_env']}")
            
            url = f"{config['base_url']}/chat/completions"
            data = {
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": "Ты помощник, который создает модели систем в формате JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result["choices"][0]["message"]["content"]
                
                # Пытаемся найти JSON в ответе
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        model = json.loads(json_match.group())
                        return {"success": True, "model": model}
                    except json.JSONDecodeError as e:
                        return {"success": False, "error": f"Ошибка парсинга JSON: {e}"}
                else:
                    return {"success": False, "error": "LLM не вернул валидный JSON"}
                    
        except Exception as e:
            logger.error(f"Ошибка при генерации модели DeepSeek: {e}")
            return {"success": False, "error": f"Ошибка при генерации модели: {e}"}

class ModelHandler(http.server.BaseHTTPRequestHandler):
    """Обработчик HTTP запросов"""
    
    def do_OPTIONS(self):
        """Обработка CORS preflight запросов"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == "/api/status":
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
        """Обработка POST запросов"""
        if self.path == "/api/generate-model":
            self.handle_generate_model()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def handle_generate_model(self):
        """Обработка запроса на генерацию модели"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Empty request body")
                return
                
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            text = data.get('text', '')
            provider = data.get('provider', 'ollama')
            
            if not text:
                self.send_error(400, "Missing 'text' parameter")
                return
            
            # Создаем клиент LLM
            llm_client = LLMClient(provider=provider)
            
            # Генерируем модель
            result = llm_client.generate_model(text)
            
            # Отправляем ответ
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            logger.error(f"Ошибка обработки запроса: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }).encode())
    
    def log_message(self, format, *args):
        """Кастомизация логов"""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server(port=5001):
    """Запуск сервера"""
    handler = ModelHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logger.info(f"Сервер запущен на порту {port}")
        print(f"🚀 AI API Server запущен: http://localhost:{port}")
        print(f"📝 API Endpoint: POST http://localhost:{port}/api/generate-model")
        print(f"📡 Status: GET http://localhost:{port}/api/status")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен")
            print("\n👋 Сервер остановлен")

if __name__ == "__main__":
    # Определяем порт
    port = 5001
    while True:
        try:
            run_server(port)
            break
        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"Порт {port} занят, пробую порт {port + 1}")
                port += 1
            else:
                raise