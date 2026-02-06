#!/usr/bin/env python3
"""
Тестирование вывода логов из API
"""

import subprocess
import time
import threading
import sys
import os

def read_output(proc, output_lines):
    """Читает вывод из процесса в отдельном потоке"""
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            output_lines.append(line.strip())
            print(f"📤 API: {line.strip()}")

def test_api_logging():
    """Тестирует вывод логов из API"""
    
    print("🧪 ТЕСТИРОВАНИЕ ВЫВОДА ЛОГОВ ИЗ API")
    print("=" * 60)
    
    # Запускаем API
    print("🚀 Запускаю api-fixed-new-structure.py...")
    
    # Используем универсальный запуск
    api_process = subprocess.Popen(
        [sys.executable, 'api-fixed-new-structure.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    output_lines = []
    
    # Запускаем чтение вывода в отдельном потоке
    reader_thread = threading.Thread(target=read_output, args=(api_process, output_lines))
    reader_thread.daemon = True
    reader_thread.start()
    
    # Ждем запуска
    print("⏳ Ожидание запуска API (5 секунд)...")
    time.sleep(5)
    
    # Проверяем, запущен ли API
    if api_process.poll() is not None:
        print("❌ API завершился сразу")
        api_process.wait()
        print("📤 Полный вывод:")
        for line in output_lines:
            print(f"   {line}")
        return False
    
    print("✅ API запущен")
    
    # Теперь отправляем тестовый запрос
    print("\n📤 Отправляю тестовый запрос...")
    
    # Находим порт API
    api_port = None
    for line in output_lines:
        if "Сервер запущен на порту" in line:
            # Ищем число в строке
            import re
            match = re.search(r'порту (\d+)', line)
            if match:
                api_port = match.group(1)
                break
    
    if not api_port:
        # Пробуем прочитать порт из файла
        if os.path.exists('api_port.txt'):
            with open('api_port.txt', 'r') as f:
                api_port = f.read().strip()
    
    if api_port:
        print(f"🔍 Найден порт API: {api_port}")
        
        # Отправляем запрос
        import json
        import urllib.request
        import urllib.error
        
        try:
            data = json.dumps({"text": "Пользователь регистрируется в системе"}).encode('utf-8')
            req = urllib.request.Request(
                f"http://localhost:{api_port}/api/generate-model",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            print("🔄 Отправляю POST запрос...")
            response = urllib.request.urlopen(req, timeout=10)
            result = json.loads(response.read().decode('utf-8'))
            print(f"✅ Ответ получен: успех={result.get('success')}")
            
            # Ждем немного, чтобы логи вывелись
            print("⏳ Ожидание вывода логов (3 секунды)...")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
    else:
        print("⚠️  Не удалось определить порт API")
    
    # Проверяем, были ли логи с JSON
    print("\n📋 ПРОВЕРКА ВЫВОДА ЛОГОВ:")
    
    json_log_found = False
    stats_log_found = False
    
    for line in output_lines:
        if "СГЕНЕРИРОВАННАЯ МОДЕЛЬ" in line:
            print(f"✅ Найден лог: 'СГЕНЕРИРОВАННАЯ МОДЕЛЬ'")
            json_log_found = True
        
        if "СТАТИСТИКА МОДЕЛИ" in line or "Действий:" in line:
            print(f"✅ Найден лог статистики")
            stats_log_found = True
        
        if "model_actions" in line and "model_objects" in line:
            print(f"✅ Найден JSON в логах")
    
    # Выводим последние 10 строк логов
    print("\n📜 ПОСЛЕДНИЕ СТРОКИ ЛОГОВ:")
    for line in output_lines[-10:]:
        print(f"   {line}")
    
    # Останавливаем API
    print("\n🛑 Останавливаю API...")
    api_process.terminate()
    try:
        api_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        api_process.kill()
    
    print("\n" + "=" * 60)
    print("🎯 РЕЗУЛЬТАТЫ:")
    
    if json_log_found:
        print("✅ JSON выводится в логи")
    else:
        print("❌ JSON не найден в логах")
        print("   Возможные причины:")
        print("   1. API не успел обработать запрос")
        print("   2. Логирование отключено")
        print("   3. Ошибка в коде логирования")
    
    if stats_log_found:
        print("✅ Статистика выводится в логи")
    else:
        print("❌ Статистика не найдена в логах")
    
    # Проверяем файл api-fixed-new-structure.py
    print("\n🔍 ПРОВЕРКА КОДА API:")
    
    with open('api-fixed-new-structure.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_logs = [
        'logger.info(f"🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ"',
        'json.dumps(model',
        'ensure_ascii=False',
        'indent=2',
        'СТАТИСТИКА МОДЕЛИ'
    ]
    
    for log in required_logs:
        if log in content:
            print(f"   ✅ '{log}' найден в коде")
        else:
            print(f"   ❌ '{log}' не найден в коде")
    
    print("\n📋 РЕКОМЕНДАЦИИ:")
    print("1. Убедитесь, что api-fixed-new-structure.py содержит логирование")
    print("2. Запустите API отдельно и отправьте запрос")
    print("3. Проверьте вывод в консоли")
    print("4. Если логи не выводятся, проверьте уровень логирования")
    
    return json_log_found and stats_log_found

if __name__ == "__main__":
    test_api_logging()