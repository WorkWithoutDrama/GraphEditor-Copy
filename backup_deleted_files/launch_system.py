#!/usr/bin/env python3
"""
Простой скрипт для запуска системы
"""

import subprocess
import time
import os
import sys

def main():
    print("🚀 ЗАПУСК СИСТЕМЫ GRAPH EDITOR")
    print("=" * 50)
    
    # Останавливаем старые процессы
    print("🔧 Остановка старых процессов...")
    subprocess.run(['pkill', '-f', 'python.*api'], stderr=subprocess.DEVNULL)
    subprocess.run(['pkill', '-f', 'node.*proxy'], stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    # Удаляем старый файл порта
    if os.path.exists('api_port.txt'):
        os.remove('api_port.txt')
    
    # Запускаем API
    print("🚀 Запуск API...")
    api_proc = subprocess.Popen(
        ['python3', 'api.py'],
        stdout=open('api.log', 'w'),
        stderr=subprocess.STDOUT
    )
    
    # Ждем, пока API запустится и создаст файл с портом
    print("⏳ Ожидание запуска API...")
    
    max_wait = 10
    api_port = None
    for i in range(max_wait):
        if os.path.exists('api_port.txt'):
            try:
                with open('api_port.txt', 'r') as f:
                    api_port = f.read().strip()
                if api_port:
                    break
            except:
                pass
        time.sleep(1)
    
    if not api_port:
        print("❌ API не запустился за отведенное время")
        print("📋 Лог API:")
        try:
            with open('api.log', 'r') as f:
                print(f.read())
        except:
            print("Файл лога не найден")
        api_proc.terminate()
        return 1
    
    print(f"✅ API запущен на порту {api_port}")
    
    # Запускаем прокси
    print("🚀 Запуск прокси...")
    
    # Проверяем наличие node
    node_path = None
    possible_paths = ['/opt/homebrew/bin/node', '/usr/local/bin/node', 'node']
    
    for path in possible_paths:
        try:
            subprocess.run([path, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            node_path = path
            break
        except (FileNotFoundError, PermissionError):
            continue
    
    if not node_path:
        print("❌ Node.js не найден. Установите Node.js")
        api_proc.terminate()
        return 1
    
    print(f"🔧 Использую Node.js: {node_path}")
    
    proxy_proc = subprocess.Popen(
        [node_path, 'proxy-server.js'],
        stdout=open('proxy.log', 'w'),
        stderr=subprocess.STDOUT
    )
    
    print("⏳ Ожидание запуска прокси...")
    time.sleep(2)
    
    # Проверяем прокси
    print("🔧 Проверка работы системы...")
    time.sleep(1)
    
    # Показываем логи
    print("\n📋 ЛОГИ СИСТЕМЫ:")
    print("-" * 50)
    
    try:
        with open('api.log', 'r') as f:
            api_log = f.read().strip()
            if api_log:
                print("API лог:")
                print(api_log)
                print()
    except:
        pass
    
    try:
        with open('proxy.log', 'r') as f:
            proxy_log = f.read().strip()
            if proxy_log:
                print("Прокси лог:")
                print(proxy_log)
                print()
    except:
        pass
    
    print("-" * 50)
    
    # Определяем порт прокси из лога
    proxy_port = 3000  # По умолчанию
    
    try:
        with open('proxy.log', 'r') as f:
            for line in f:
                if 'Прокси сервер запущен на порту' in line:
                    import re
                    match = re.search(r'на порту (\d+)', line)
                    if match:
                        proxy_port = match.group(1)
                    break
    except:
        pass
    
    print(f"\n🎉 СИСТЕМА ЗАПУЩЕНА!")
    print("=" * 50)
    print(f"🌐 Веб-интерфейс: http://localhost:{proxy_port}")
    print(f"🔧 API: http://localhost:{api_port}")
    print("\n📋 ЭНДПОИНТЫ:")
    print(f"   • Веб-интерфейс: http://localhost:{proxy_port}")
    print(f"   • API статус: http://localhost:{api_port}/api/status")
    print(f"   • API здоровье: http://localhost:{api_port}/api/health")
    print(f"   • API генерация: http://localhost:{api_port}/api/generate-model")
    print("\n📁 ЛОГИ:")
    print("   • API: tail -f api.log")
    print("   • Прокси: tail -f proxy.log")
    print("\n🛑 Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    try:
        # Ждем завершения
        while True:
            time.sleep(1)
            if api_proc.poll() is not None:
                print("\n⚠️  API завершился")
                break
            if proxy_proc.poll() is not None:
                print("\n⚠️  Прокси завершился")
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка системы...")
    
    # Останавливаем процессы
    api_proc.terminate()
    proxy_proc.terminate()
    
    # Удаляем файл порта
    if os.path.exists('api_port.txt'):
        os.remove('api_port.txt')
    
    print("✅ Система остановлена")
    return 0

if __name__ == "__main__":
    sys.exit(main())