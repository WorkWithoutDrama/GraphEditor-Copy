#!/usr/bin/env python3
"""
Простой тест соединения
"""

import socket
import subprocess
import time
import os
import sys

def check_port(port):
    """Проверяет, свободен ли порт"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except:
        return False
    finally:
        sock.close()

def main():
    print("🔍 ТЕСТ СИСТЕМЫ")
    print("=" * 50)
    
    # Проверяем порты
    print("📡 Проверка портов:")
    for port in [3000, 5001, 5002, 5003, 5004, 5005]:
        if check_port(port):
            print(f"   ✅ Порт {port}: свободен")
        else:
            print(f"   ❌ Порт {port}: занят")
    
    # Запускаем API
    print("\n🚀 Запуск API...")
    api_proc = subprocess.Popen(
        ['python3', 'api_ultra_simple.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Ждем 3 секунды
    time.sleep(3)
    
    # Проверяем файл порта
    if not os.path.exists('api_port.txt'):
        print("❌ API не создал api_port.txt")
        api_proc.terminate()
        return 1
    
    with open('api_port.txt', 'r') as f:
        api_port = f.read().strip()
    
    print(f"✅ API порт: {api_port}")
    
    # Проверяем API
    print(f"🔧 Проверка API на порту {api_port}...")
    
    import urllib.request
    try:
        response = urllib.request.urlopen(f'http://localhost:{api_port}/api/health', timeout=5)
        if response.status == 200:
            print("✅ API работает!")
            data = response.read().decode('utf-8')
            print(f"   Ответ: {data}")
        else:
            print(f"❌ API ответил с кодом: {response.status}")
            api_proc.terminate()
            return 1
    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")
        api_proc.terminate()
        return 1
    
    # Запускаем прокси
    print("\n🚀 Запуск прокси...")
    
    # Находим node
    node_path = None
    for path in ['/opt/homebrew/bin/node', '/usr/local/bin/node', 'node']:
        try:
            subprocess.run([path, '--version'], capture_output=True, check=True)
            node_path = path
            break
        except:
            continue
    
    if not node_path:
        print("❌ Node.js не найден")
        api_proc.terminate()
        return 1
    
    print(f"🔧 Использую: {node_path}")
    
    proxy_proc = subprocess.Popen(
        [node_path, 'proxy_simple.js'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Ждем 2 секунды
    time.sleep(2)
    
    # Проверяем прокси
    print(f"🔧 Проверка прокси на порту 3000...")
    try:
        response = urllib.request.urlopen('http://localhost:3000/api/health', timeout=5)
        if response.status == 200:
            print("✅ Прокси работает!")
            data = response.read().decode('utf-8')
            print(f"   Ответ через прокси: {data}")
        else:
            print(f"❌ Прокси ответил с кодом: {response.status}")
            api_proc.terminate()
            proxy_proc.terminate()
            return 1
    except Exception as e:
        print(f"❌ Ошибка подключения к прокси: {e}")
        print("📋 Вывод прокси:")
        try:
            output, _ = proxy_proc.communicate(timeout=1)
            print(output)
        except:
            pass
        api_proc.terminate()
        proxy_proc.terminate()
        return 1
    
    print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    print("=" * 50)
    print(f"🌐 Веб-интерфейс: http://localhost:3000")
    print(f"🔧 API: http://localhost:{api_port}")
    
    print("\n🛑 Нажмите Ctrl+C для остановки...")
    
    try:
        # Ждем
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Остановка...")
    
    # Очистка
    api_proc.terminate()
    proxy_proc.terminate()
    if os.path.exists('api_port.txt'):
        os.remove('api_port.txt')
    
    print("✅ Готово")
    return 0

if __name__ == "__main__":
    sys.exit(main())