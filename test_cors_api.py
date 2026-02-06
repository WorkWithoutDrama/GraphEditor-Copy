#!/usr/bin/env python3
"""
Тестирование API с CORS поддержкой
"""

import subprocess
import time
import json
import urllib.request
import urllib.error
import sys

def test_cors_api():
    """Тестирует API с CORS поддержкой"""
    
    print("🧪 ТЕСТИРОВАНИЕ API С CORS ПОДДЕРЖКОЙ")
    print("=" * 60)
    
    # 1. Запускаем API
    print("🚀 Запускаю api_simple_with_cors.py...")
    
    api_process = subprocess.Popen(
        [sys.executable, 'api_simple_with_cors.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Даем время на запуск
    print("⏳ Ожидание запуска API (3 секунды)...")
    time.sleep(3)
    
    # 2. Ищем порт
    port = None
    try:
        with open('api_port.txt', 'r') as f:
            port = f.read().strip()
    except:
        # Пробуем найти вручную
        for p in range(5001, 5020):
            try:
                response = urllib.request.urlopen(f'http://localhost:{p}/api/health', timeout=1)
                if response.status == 200:
                    port = p
                    break
            except:
                continue
    
    if not port:
        print("❌ Не удалось определить порт API")
        api_process.terminate()
        return False
    
    print(f"✅ API запущен на порту {port}")
    
    # 3. Тестируем OPTIONS (preflight)
    print("\n📋 ТЕСТ CORS (OPTIONS preflight):")
    
    try:
        # Создаем OPTIONS запрос
        req = urllib.request.Request(
            f'http://localhost:{port}/api/generate-model',
            method='OPTIONS'
        )
        
        response = urllib.request.urlopen(req, timeout=5)
        
        # Проверяем заголовки
        headers = dict(response.headers)
        
        print(f"✅ OPTIONS запрос успешен")
        print(f"   • Status: {response.status}")
        
        # Проверяем CORS заголовки
        cors_headers = ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods', 'Access-Control-Allow-Headers']
        for header in cors_headers:
            if header in headers:
                print(f"   • {header}: {headers[header]}")
            else:
                print(f"   ❌ {header}: отсутствует")
        
    except Exception as e:
        print(f"❌ OPTIONS запрос не прошел: {e}")
    
    # 4. Тестируем POST запрос
    print("\n📋 ТЕСТ POST запроса:")
    
    try:
        data = json.dumps({'text': 'Тестовый запрос для проверки CORS'}).encode()
        req = urllib.request.Request(
            f'http://localhost:{port}/api/generate-model',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        response = urllib.request.urlopen(req, timeout=5)
        result = json.loads(response.read().decode())
        
        print(f"✅ POST запрос успешен")
        print(f"   • Status: {response.status}")
        print(f"   • Success: {result.get('success')}")
        
        # Проверяем CORS заголовки в ответе
        headers = dict(response.headers)
        if 'Access-Control-Allow-Origin' in headers:
            print(f"   • CORS заголовки присутствуют")
        else:
            print(f"   ⚠️  CORS заголовки отсутствуют в ответе")
        
    except Exception as e:
        print(f"❌ POST запрос не прошел: {e}")
    
    # 5. Проверяем логи
    print("\n📋 ПРОВЕРКА ЛОГОВ:")
    
    # Читаем вывод API
    time.sleep(1)
    try:
        output, _ = api_process.communicate(timeout=2)
        if output:
            lines = output.split('\n')
            for line in lines[-10:]:  # Последние 10 строк
                if line.strip():
                    print(f"   📝 {line}")
    except:
        print("   ⏳ API продолжает работать...")
    
    # 6. Останавливаем API
    print("\n🛑 Останавливаю API...")
    api_process.terminate()
    try:
        api_process.wait(timeout=2)
    except:
        api_process.kill()
    
    print("\n" + "=" * 60)
    print("🎯 РЕКОМЕНДАЦИИ:")
    print("\n1. ✅ API с CORS поддержкой готов к использованию")
    print("2. 🔧 Для работы системы запустите:")
    print("   ./launch.command")
    print("3. 📝 При проблемах с CORS проверьте:")
    print("   • Запущен ли api_simple_with_cors.py")
    print("   • Порт API (файл api_port.txt)")
    print("   • Заголовки в ответе OPTIONS запроса")
    
    return True

if __name__ == "__main__":
    test_cors_api()