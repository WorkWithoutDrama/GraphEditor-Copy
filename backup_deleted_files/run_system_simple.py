#!/usr/bin/env python3
"""
Упрощенный запуск системы
"""

import subprocess
import time
import os
import sys
import socket

def find_free_port(start_port=5001):
    """Находит свободный порт"""
    port = start_port
    while port < start_port + 20:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            port += 1
        finally:
            sock.close()
    return None

def main():
    print("🚀 Запуск системы Graph Editor")
    print("=" * 50)
    
    # Останавливаем старые процессы
    print("🔧 Остановка старых процессов...")
    subprocess.run(['pkill', '-f', 'python.*api'], stderr=subprocess.DEVNULL)
    subprocess.run(['pkill', '-f', 'node.*proxy'], stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    # Запускаем API (он сам найдет свободный порт)
    print("🚀 Запуск API...")
    api_proc = subprocess.Popen(
        ['python3', 'api-fixed-new-structure.py'],
        stdout=open('api.log', 'w'),
        stderr=subprocess.STDOUT
    )
    
    # Ждем, пока API запустится и запишет порт
    print("⏳ Ожидание запуска API...")
    time.sleep(3)
    
    # Читаем лог API, чтобы узнать порт
    api_port = None
    try:
        with open('api.log', 'r') as f:
            for line in f:
                if 'Сервер запущен на порту' in line:
                    # Ищем номер порта в строке
                    import re
                    match = re.search(r'на порту (\d+)', line)
                    if match:
                        api_port = int(match.group(1))
                        break
    except FileNotFoundError:
        pass
    
    if not api_port:
        print("❌ Не удалось определить порт API")
        print("📋 Лог API:")
        try:
            with open('api.log', 'r') as f:
                print(f.read())
        except:
            print("Файл лога не найден")
        api_proc.terminate()
        return 1
    
    print(f"✅ API запущен на порту {api_port}")
    
    # Обновляем порт в прокси
    print(f"📝 Обновление прокси для использования порта API: {api_port}")
    
    with open('proxy-server.js', 'r') as f:
        proxy_content = f.read()
    
    # Заменяем порт API в прокси
    import re
    proxy_content = re.sub(
        r'const API_PORT = \d+;',
        f'const API_PORT = {api_port};',
        proxy_content
    )
    
    with open('proxy-server.js', 'w') as f:
        f.write(proxy_content)
    
    # Запускаем прокси на свободном порту
    proxy_port = find_free_port(3000)
    if not proxy_port:
        print("❌ Не удалось найти свободный порт для прокси")
        api_proc.terminate()
        return 1
    
    print(f"🚀 Запуск прокси на порту {proxy_port}...")
    
    # Обновляем порт прокси в файле
    proxy_content = re.sub(
        r'const PROXY_PORT = \d+;',
        f'const PROXY_PORT = {proxy_port};',
        proxy_content
    )
    
    with open('proxy-server.js', 'w') as f:
        f.write(proxy_content)
    
    # Запускаем прокси (используем полный путь к node)
    node_path = '/opt/homebrew/bin/node'
    if not os.path.exists(node_path):
        # Пробуем найти node в PATH
        try:
            node_path = subprocess.check_output(['which', 'node']).decode().strip()
        except:
            print("❌ Node.js не найден. Установите Node.js и добавьте в PATH")
            api_proc.terminate()
            return 1
    
    print(f"🔧 Использую Node.js: {node_path}")
    
    proxy_proc = subprocess.Popen(
        [node_path, 'proxy-server.js'],
        stdout=open('proxy.log', 'w'),
        stderr=subprocess.STDOUT
    )
    
    print(f"✅ Прокси запущен на порту {proxy_port}")
    
    # Ждем запуска прокси
    print("⏳ Ожидание запуска прокси...")
    time.sleep(2)
    
    # Проверяем, что прокси работает
    import urllib.request
    try:
        urllib.request.urlopen(f'http://localhost:{proxy_port}/', timeout=5)
        print(f"✅ Прокси работает на http://localhost:{proxy_port}")
    except:
        print("❌ Прокси не запустился")
        print("📋 Лог прокси:")
        try:
            with open('proxy.log', 'r') as f:
                print(f.read())
        except:
            print("Файл лога не найден")
        api_proc.terminate()
        proxy_proc.terminate()
        return 1
    
    print("\n" + "=" * 50)
    print("🎉 СИСТЕМА УСПЕШНО ЗАПУЩЕНА!")
    print("=" * 50)
    print(f"🌐 Веб-интерфейс: http://localhost:{proxy_port}")
    print(f"🔧 API: http://localhost:{api_port}")
    print("\n📋 ЭНДПОИНТЫ:")
    print(f"   • GET  http://localhost:{api_port}/api/status")
    print(f"   • POST http://localhost:{api_port}/api/generate-model")
    print("\n📁 ЛОГИ:")
    print("   • API: api.log")
    print("   • Прокси: proxy.log")
    print("\n🛑 Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    try:
        # Ждем завершения
        while True:
            time.sleep(1)
            # Проверяем, что процессы еще работают
            if api_proc.poll() is not None:
                print("\n⚠️  API завершился неожиданно")
                break
            if proxy_proc.poll() is not None:
                print("\n⚠️  Прокси завершился неожиданно")
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка системы...")
    
    # Останавливаем процессы
    api_proc.terminate()
    proxy_proc.terminate()
    
    print("✅ Система остановлена")
    return 0

if __name__ == "__main__":
    sys.exit(main())