#!/usr/bin/env python3
"""
Простейший тест вывода JSON из API
"""

import subprocess
import time
import threading
import sys

def read_output(proc):
    """Читает вывод из процесса"""
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            print(f"API: {line.strip()}")

print("🧪 ЗАПУСК API И ПРОВЕРКА ВЫВОДА JSON")
print("=" * 50)

# Останавливаем старый API
import os
os.system("pkill -f 'python.*api_simple' 2>/dev/null")

# Запускаем API
print("🚀 Запускаю api_simple_with_cors.py...")
proc = subprocess.Popen(
    [sys.executable, 'api_simple_with_cors.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    universal_newlines=True
)

# Запускаем чтение вывода в отдельном потоке
import threading
output_lines = []

def reader():
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            output_lines.append(line.strip())
            print(f"📢 {line.strip()}")

reader_thread = threading.Thread(target=reader)
reader_thread.daemon = True
reader_thread.start()

# Ждем запуска
print("⏳ Ожидание запуска API...")
time.sleep(3)

# Проверяем порт
api_port = None
try:
    with open('api_port.txt', 'r') as f:
        api_port = f.read().strip()
        print(f"✅ API запущен на порту {api_port}")
except:
    print("❌ Не удалось прочитать порт API")

if api_port:
    # Отправляем тестовый запрос
    print("\n📤 Отправляю тестовый запрос...")
    import urllib.request
    import json
    
    try:
        data = json.dumps({'text': 'Тестовый запрос для проверки вывода JSON'}).encode()
        req = urllib.request.Request(
            f'http://localhost:{api_port}/api/generate-model',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        response = urllib.request.urlopen(req, timeout=5)
        result = json.loads(response.read().decode())
        print(f"✅ Запрос отправлен, успех: {result.get('success')}")
        
        # Ждем логи
        print("\n⏳ Ожидание вывода логов (3 секунды)...")
        time.sleep(3)
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")

# Проверяем, были ли логи
print("\n🔍 ПРОВЕРКА ЛОГОВ:")
print("=" * 50)

# Ищем JSON в логах
json_found = False
for line in output_lines:
    if 'СГЕНЕРИРОВАННАЯ МОДЕЛЬ' in line:
        print("✅ 'СГЕНЕРИРОВАННАЯ МОДЕЛЬ' найдено в логах")
        json_found = True
    if 'model_actions' in line and 'model_objects' in line:
        print("✅ JSON модель найдена в логах")

if not json_found:
    print("❌ JSON не найден в логах")
    print("\n📋 ПОСЛЕДНИЕ СТРОКИ ВЫВОДА:")
    for line in output_lines[-20:]:
        print(f"   {line}")

# Останавливаем API
print("\n🛑 Останавливаю API...")
proc.terminate()
try:
    proc.wait(timeout=2)
except:
    proc.kill()

print("\n" + "=" * 50)
if json_found:
    print("🎉 JSON ВЫВОДИТСЯ КОРРЕКТНО!")
    print("Проблема в launch.command - не показывает вывод")
else:
    print("❌ JSON НЕ ВЫВОДИТСЯ ВООБЩЕ")
    print("Проблема в api_simple_with_cors.py")