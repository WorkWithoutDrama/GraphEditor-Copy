import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemModelHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/generate-model':
            self.handle_generate_model()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        if self.path == '/api/generate-model' or self.path == '/api/health':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        else:
            self.send_error(404)
    
    def do_GET(self):
        if self.path == '/api/health':
            self.handle_health()
        else:
            self.send_error(404)
    
    def handle_health(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        # Динамический CORS заголовок
        if self.headers.get('Origin'):
            self.send_header('Access-Control-Allow-Origin', self.headers.get('Origin'))
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = json.dumps({'status': 'ok', 'service': 'System Model Generator API'})
        self.wfile.write(response.encode('utf-8'))
    
    def handle_generate_model(self):
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
            
            logger.info(f"Получен запрос на генерацию модели: {text[:100]}...")
            
            # Имитация обработки AI
            time.sleep(1)
            
            # Демонстрационная модель на основе текста
            model = self.generate_demo_model(text)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps({
                'success': True,
                'model': model,
                'message': 'Модель успешно сгенерирована'
            })
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
    
    def generate_demo_model(self, text):
        """Генерирует демонстрационную модель на основе ключевых слов в тексте."""
        model = {}
        
        # Простые правила для демонстрации
        if 'регистрац' in text.lower():
            model["Пользователь регистрируется"] = {
                "init_states": ["Нет сессии"],
                "final_states": ["Пользователь зарегистрирован"]
            }
        
        if 'email' in text.lower() or 'почт' in text.lower():
            model["Система проверяет email"] = {
                "init_states": ["Пользователь зарегистрирован"],
                "final_states": ["Email проверен"]
            }
        
        if 'данн' in text.lower() or 'ввод' in text.lower():
            model["Пользователь вводит данные"] = {
                "init_states": ["Email проверен"],
                "final_states": ["Данные сохранены"]
            }
        
        if 'систем' in text.lower() and 'расчет' in text.lower():
            model["Система производит расчет"] = {
                "init_states": ["Данные сохранены"],
                "final_states": ["Расчет выполнен"]
            }
        
        if 'результат' in text.lower() or 'отображ' in text.lower():
            model["Система отображает результат"] = {
                "init_states": ["Расчет выполнен"],
                "final_states": ["Результат отображен"]
            }
        
        # Если ничего не найдено, создаем базовую модель
        if not model:
            model = {
                "Пользователь выполняет действие": {
                    "init_states": ["Начальное состояние"],
                    "final_states": ["Конечное состояние"]
                }
            }
        
        return model
    
    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

def run_server():
    # Пробуем порты начиная с 5000
    for port in range(5000, 5010):
        try:
            server_address = ('', port)
            httpd = HTTPServer(server_address, SystemModelHandler)
            logger.info(f"Запуск API сервера на порту {port}...")
            
            # Сохраняем порт в файл для прокси
            with open('api_port.txt', 'w') as f:
                f.write(str(port))
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logger.info("Сервер остановлен")
                httpd.server_close()
            return
            
        except OSError as e:
            if 'Address already in use' in str(e):
                logger.info(f"Порт {port} занят, пробую следующий...")
                continue
            else:
                raise
    
    logger.error("Не удалось найти свободный порт (5000-5009)")

if __name__ == '__main__':
    run_server()