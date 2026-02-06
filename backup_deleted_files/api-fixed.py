#!/usr/bin/env python3
"""
AI API Server для Graph Editor
Исправленная версия без синтаксических ошибок в промпте
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
            Словарь с моделью системы
        """
        if self.provider == "ollama":
            return self._generate_with_ollama(text)
        elif self.provider == "deepseek":
            return self._generate_with_deepseek(text)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
    
    def _generate_with_ollama(self, text: str) -> Dict:
        """Генерация модели с использованием Ollama"""
        config = self.config["ollama"]
        
        # Упрощенный промпт без сложных фигурных скобок
        prompt = f"""Ты — архитектор систем. Проанализируй техническое задание и создай модель системы в формате JSON.

ТЕКСТ ТЗ:
{text}

ТРЕБУЕМЫЙ ФОРМАТ:
{{
  "model_actions": [],
  "model_objects": [],
  "model_connections": []
}}

ПРАВИЛА:
1. object_id: "o" + 5 цифр (пример: "o12345")
2. state_id: "s" + 5 цифр (пример: "s00000", "s12345")
3. resource_state: массив состояний
4. action_links и object_links должны содержать ключи: manual, API, UI
   - Эти поля могут быть пустыми строками: ""
   - Пример action_links: {{"manual": "", "API": "", "UI": ""}}
   - Пример object_links: {{"manual": "", "API": "", "UI": ""}}

Пример объекта:
{{
  "object_id": "o12345",
  "object_name": "Пользователь",
  "resource_state": [
    {{"state_id": "s00000", "state_name": "null"}},
    {{"state_id": "s12345", "state_name": "зарегистрирован"}}
  ],
  "object_links": {{
    "manual": "",
    "API": "",
    "UI": ""
  }}
}}

Пример действия:
{{
  "action_id": "a12345",
  "action_name": "Проверить email",
  "action_links": {{
    "manual": "",
    "API": "",
    "UI": ""
  }}
}}

ПРАВИЛА ДЛЯ СВЯЗЕЙ:
5. Каждая связь в model_connections должна содержать ТОЛЬКО:
   - connection_out: ID исходящего узла
   - connection_in: ID входящего узла
   - НЕ используй другие имена полей (не source, target, etc.)
   - Пример связи: {{"connection_out": "a12345", "connection_in": "o12345s12345"}}
   - connection_in использует составной ID: object_id + state_id

Верни только JSON без пояснений."""

        try:
            import urllib.request
            import urllib.error
            
            request_data = json.dumps({
                "model": config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f"{config['base_url']}{config['endpoint']}",
                data=request_data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                response_text = result.get("response", "")
                
                # Извлекаем JSON из ответа
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    try:
                        model = json.loads(json_str)
                        # Проверяем структуру
                        if self._validate_model_structure(model):
                            return model
                        else:
                            logger.error("❌ Неправильная структура модели")
                            return {"error": "Неправильная структура модели"}
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Ошибка парсинга JSON: {e}")
                        logger.error(f"❌ Ответ от Ollama: {response_text[:500]}")
                        return self._get_fallback_model()
                else:
                    logger.error(f"❌ JSON не найден в ответе: {response_text[:200]}")
                    return {"error": "JSON не найден в ответе LLM"}
                
        except urllib.error.URLError as e:
            logger.error(f"❌ Ошибка сети при запросе к Ollama: {e}")
            logger.error(f"❌ URL: {config['base_url']}{config['endpoint']}")
            return self._get_fallback_model()
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при запросе к Ollama: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return self._get_fallback_model()
    
    def _generate_with_deepseek(self, text: str) -> Dict:
        """Генерация модели с использованием DeepSeek"""
        config = self.config["deepseek"]
        api_key = os.environ.get(config["api_key_env"])
        
        if not api_key:
            logger.error(f"❌ API ключ не найден в переменной окружения {config['api_key_env']}")
            return self._get_fallback_model()
        
        # Упрощенный промпт
        prompt = f"""Создай модель системы в формате JSON на основе ТЗ: {text}

Формат: {{
  "model_actions": [],
  "model_objects": [],
  "model_connections": []
}}

Правила:
- object_id: o + 5 цифр
- state_id: s + 5 цифр  
- resource_state: массив
- action_links и object_links должны содержать: manual, API, UI (могут быть пустыми)
- Каждая связь должна содержать ТОЛЬКО: connection_out, connection_in
  - connection_in использует составной ID: object_id + state_id (пример: o12345s12345)
  - НЕ используй другие имена полей (не source, target, etc.)

Верни только JSON."""

        try:
            import urllib.request
            import urllib.error
            
            request_data = json.dumps({
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": "Ты архитектор систем. Создавай модели в JSON формате."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f"{config['base_url']}/chat/completions",
                data=request_data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                response_text = result["choices"][0]["message"]["content"]
                
                # Извлекаем JSON
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    try:
                        model = json.loads(json_str)
                        if self._validate_model_structure(model):
                            return model
                        else:
                            return {"error": "Неправильная структура модели"}
                    except json.JSONDecodeError:
                        return self._get_fallback_model()
                else:
                    return self._get_fallback_model()
                
        except urllib.error.HTTPError as e:
            logger.error(f"Ошибка DeepSeek API: {e.code}")
            return self._get_fallback_model()
        except urllib.error.URLError as e:
            logger.error(f"Ошибка сети при запросе к DeepSeek: {e}")
            return self._get_fallback_model()
        except Exception as e:
            logger.error(f"Ошибка при запросе к DeepSeek: {e}")
            return self._get_fallback_model()
    
    def _validate_model_structure(self, model):
        """
        Проверяет структуру модели в новом формате
        
        Args:
            model: Модель для проверки
            
        Returns:
            bool: True если структура корректна
        """
        try:
            # Базовая проверка - модель должна быть словарем
            if not isinstance(model, dict):
                logger.error("❌ Модель не является словарем")
                return False
            
            # Проверяем наличие обязательных ключей для нового формата
            required_keys = ['model_actions', 'model_objects', 'model_connections']
            for key in required_keys:
                if key not in model:
                    logger.error(f"❌ Модель не содержит обязательного ключа: {key}")
                    return False
                
                # Проверяем, что значения являются списками
                if not isinstance(model[key], list):
                    logger.error(f"❌ Ключ {key} должен быть списком")
                    return False
            
            # Проверяем структуру действий
            for action in model['model_actions']:
                if not isinstance(action, dict):
                    logger.error("❌ Элемент model_actions должен быть словарем")
                    return False
                
                required_action_keys = ['action_id', 'action_name', 'action_links']
                for key in required_action_keys:
                    if key not in action:
                        logger.error(f"❌ Действие не содержит ключа: {key}")
                        return False
                
                # action_links должен быть словарем и содержать определенные ключи
                if not isinstance(action['action_links'], dict):
                    logger.error("❌ action_links должен быть словарем")
                    return False
                
                # Проверяем наличие обязательных ключей в action_links
                required_link_keys = ['manual', 'API', 'UI']
                for key in required_link_keys:
                    if key not in action['action_links']:
                        logger.error(f"❌ action_links не содержит ключа: {key}")
                        return False
            
            # Проверяем структуру объектов
            for obj in model['model_objects']:
                if not isinstance(obj, dict):
                    logger.error("❌ Элемент model_objects должен быть словарем")
                    return False
                
                required_object_keys = ['object_id', 'object_name', 'resource_state', 'object_links']
                for key in required_object_keys:
                    if key not in obj:
                        logger.error(f"❌ Объект не содержит ключа: {key}")
                        return False
                
                # object_links должен быть словарем и содержать определенные ключи
                if not isinstance(obj['object_links'], dict):
                    logger.error("❌ object_links должен быть словарем")
                    return False
                
                # Проверяем наличие обязательных ключей в object_links
                required_link_keys = ['manual', 'API', 'UI']
                for key in required_link_keys:
                    if key not in obj['object_links']:
                        logger.error(f"❌ object_links не содержит ключа: {key}")
                        return False
                
                # Проверяем формат object_id (o + 5 цифр)
                if not re.match(r'^o\d{5}$', obj['object_id']):
                    logger.error(f"❌ object_id должен быть в формате 'o' + 5 цифр: {obj['object_id']}")
                    return False
                
                # Проверяем структуру resource_state (теперь это массив)
                if not isinstance(obj['resource_state'], list):
                    logger.error("❌ resource_state должен быть массивом")
                    return False
                
                # Проверяем структуру object_links
                if not isinstance(obj['object_links'], dict):
                    logger.error("❌ object_links должен быть словарем")
                    return False
                
                # Проверяем каждый элемент массива состояний
                for state in obj['resource_state']:
                    if not isinstance(state, dict):
                        logger.error("❌ Элемент resource_state должен быть словарем")
                        return False
                    
                    required_state_keys = ['state_id', 'state_name']
                    for key in required_state_keys:
                        if key not in state:
                            logger.error(f"❌ Состояние не содержит ключа: {key}")
                            return False
                    
                    # Проверяем формат state_id (s + 5 цифр)
                    if not re.match(r'^s\d{5}$', state['state_id']):
                        logger.error(f"❌ state_id должен быть в формате 's' + 5 цифр: {state['state_id']}")
                        return False
            
            # Проверяем структуру связей
            for connection in model['model_connections']:
                if not isinstance(connection, dict):
                    logger.error("❌ Элемент model_connections должен быть словарем")
                    return False
                
                required_connection_keys = ['connection_out', 'connection_in']
                for key in required_connection_keys:
                    if key not in connection:
                        logger.error(f"❌ Связь не содержит ключа: {key}")
                        return False
            
            logger.info("✅ Структура модели проверена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации модели: {e}")
            return False
    
    def _get_fallback_model(self) -> Dict:
        """Возвращает резервную модель в случае ошибки (в новом формате)"""
        return {
            "model_actions": [
                {
                    "action_id": "a1234567890123",
                    "action_name": "Демо-действие",
                    "action_links": {
                        "manual": "",
                        "API": "",
                        "UI": ""
                    }
                }
            ],
            "model_objects": [
                {
                    "object_id": "o12345",
                    "object_name": "Демо-объект",
                    "resource_state": [
                        {
                            "state_id": "s00000",
                            "state_name": "null"
                        },
                        {
                            "state_id": "s12345",
                            "state_name": "активен"
                        }
                    ],
                    "object_links": {
                        "manual": "",
                        "API": "",
                        "UI": ""
                    }
                }
            ],
            "model_connections": [
                {
                    "connection_out": "a1234567890123",
                    "connection_in": "o12345s12345"
                }
            ]
        }

class SystemModelHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Инициализация LLM клиента с провайдером из переменной окружения
        llm_provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
        self.llm_client = LLMClient(provider=llm_provider)
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        if self.path == '/api/generate-model':
            self.handle_generate_model()
        elif self.path == '/api/set-provider':
            self.handle_set_provider()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def handle_generate_model(self):
        """Обработка запроса на генерацию модели"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            text = data.get('text', '')
            if not text:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Текст не предоставлен'}).encode('utf-8'))
                return
            
            # Генерируем модель с использованием LLM
            model = self.generate_model_with_llm(text)
            
            # Отправляем ответ
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'success': 'error' not in model,
                'model': model
            }
            
            if 'error' in model:
                response['error'] = model['error']
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Некорректный JSON'}).encode('utf-8'))
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def generate_model_with_llm(self, text):
        """Генерирует модель системы с использованием LLM"""
        try:
            # Используем LLM клиент для генерации модели
            result = self.llm_client.generate_model(text)
            
            # Проверяем, не вернул ли LLM ошибку
            if isinstance(result, dict) and 'error' in result:
                logger.error(f"LLM вернул ошибку: {result['error']}")
                # Возвращаем ошибку как есть, чтобы фронтенд мог её показать
                return result
            
            # Проверяем, что результат имеет правильный формат модели
            if not isinstance(result, dict):
                logger.error("LLM вернул некорректный формат модели")
                return self.llm_client._get_fallback_model()
            
            # Проверяем структуру модели
            if 'model_actions' in result:
                # Это новый формат модели
                if not isinstance(result['model_actions'], list):
                    logger.error("model_actions не является списком")
                    return self.llm_client._get_fallback_model()
                logger.info("✅ Получена модель в новом формате")
                return result
            
            # Старый формат
            logger.info("✅ Получена модель в старом формате")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации модели с LLM: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'error': f'Ошибка генерации модели: {str(e)}'}
    
    def handle_set_provider(self):
        """Обработка запроса на смену провайдера LLM"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            provider = data.get('provider', 'ollama')
            os.environ['LLM_PROVIDER'] = provider
            
            # Пересоздаем LLM клиент с новым провайдером
            self.llm_client = LLMClient(provider=provider)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'message': f'Провайдер изменен на {provider}'
            }).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'service': 'System Model Generator API',
                'llm_provider': self.llm_client.provider
            }).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        logger.info(format % args)

def main():
    """Основная функция запуска сервера"""
    port = int(os.environ.get('API_PORT', 5009))
    
    # Записываем порт в файл для прокси
    with open('api_port.txt', 'w') as f:
        f.write(str(port))
    
    handler = SystemModelHandler
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        logger.info(f"🚀 API сервер запущен на порту {port}")
        logger.info(f"📝 LLM провайдер: {os.environ.get('LLM_PROVIDER', 'ollama')}")
        logger.info("🔧 Готов к обработке запросов...")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("🛑 Сервер остановлен")

if __name__ == "__main__":
    main()