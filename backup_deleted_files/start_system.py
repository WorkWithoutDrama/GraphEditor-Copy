#!/usr/bin/env python3
"""
Автоматический запуск системы с поиском свободных портов
"""

import socket
import subprocess
import time
import os
import sys
import atexit
import signal

def find_free_port(start_port=5001):
    """Находит свободный порт начиная с start_port"""
    port = start_port
    max_port = start_port + 20
    
    while port <= max_port:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            port += 1
            continue
        finally:
            sock.close()
    
    raise RuntimeError(f"Не удалось найти свободный порт в диапазоне {start_port}-{max_port}")

def update_api_port(port):
    """Обновляет порт в API файле"""
    with open('api-fixed-new-structure.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ищем и заменяем порт в функции run_server
    import re
    new_content = re.sub(r'def run_server\(port=\d+\):', f'def run_server(port={port}):', content)
    
    with open('api-fixed-new-structure.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Обновлен порт API: {port}")

def update_proxy_ports(proxy_port, api_port):
    """Обновляет порты в прокси файле"""
    with open('proxy-server.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем PROXY_PORT
    import re
    content = re.sub(r'const PROXY_PORT = \d+;', f'const PROXY_PORT = {proxy_port};', content)
    # Заменяем API_PORT
    content = re.sub(r'const API_PORT = \d+;', f'const API_PORT = {api_port};', content)
    
    with open('proxy-server.js', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Обновлены порты прокси: прокси={proxy_port}, API={api_port}")

def check_service_running(port, timeout=10):
    """Проверяет, запущен ли сервис на порту"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1)
            sock.connect(('localhost', port))
            sock.close()
            return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
        finally:
            sock.close()
    return False

def cleanup(processes):
    """Очистка процессов при завершении"""
    print("\n🛑 Остановка процессов...")
    for proc in processes:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

def main():
    print("🚀 ЗАПУСК СИСТЕМЫ GRAPH EDITOR")
    print("=" * 50)
    
    processes = []
    
    # Гарантируем очистку при завершении
    def cleanup_handler(signum=None, frame=None):
        cleanup(processes)
        sys.exit(0)
    
    atexit.register(cleanup_handler)
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    # Останавливаем старые процессы
    print("🔧 Остановка старых процессов...")
    subprocess.run(['pkill', '-f', 'python.*api'], stderr=subprocess.DEVNULL)
    subprocess.run(['pkill', '-f', 'node.*proxy'], stderr=subprocess.DEVNULL)
    
    # Ищем свободные порты
    print("🔍 Поиск свободных портов...")
    
    try:
        api_port = find_free_port(5001)
        print(f"✅ Найден свободный порт для API: {api_port}")
        
        proxy_port = find_free_port(3000)
        print(f"✅ Найден свободный порт для прокси: {proxy_port}")
        
        # Обновляем порты в файлах
        update_api_port(api_port)
        update_proxy_ports(proxy_port, api_port)
        
        # Запускаем API
        print(f"\n🚀 Запуск API на порту {api_port}...")
        api_proc = subprocess.Popen(
            ['python3', 'api-fixed-new-structure.py'],
            stdout=open('api.log', 'w'),
            stderr=subprocess.STDOUT
        )
        processes.append(api_proc)
        print(f"✅ API запущен (PID: {api_proc.pid})")
        
        # Ждем запуска API
        print("⏳ Ожидание запуска API...")
        time.sleep(3)
        
        if not check_service_running(api_port, timeout=10):
            print("❌ API не запустился. Проверьте api.log")
            with open('api.log', 'r') as f:
                print(f.read())
            cleanup_handler()
            return 1
        
        print(f"✅ API работает на http://localhost:{api_port}")
        
        # Запускаем прокси
        print(f"\n🚀 Запуск прокси на порту {proxy_port}...")
        proxy_proc = subprocess.Popen(
            ['node', 'proxy-server.js'],
            stdout=open('proxy.log', 'w'),
            stderr=subprocess.STDOUT
        )
        processes.append(proxy_proc)
        print(f"✅ Прокси запущен (PID: {proxy_proc.pid})")
        
        # Ждем запуска прокси
        print("⏳ Ожидание запуска прокси...")
        time.sleep(2)
        
        if not check_service_running(proxy_port, timeout=10):
            print("❌ Прокси не запустился. Проверьте proxy.log")
            with open('proxy.log', 'r') as f:
                print(f.read())
            cleanup_handler()
            return 1
        
        print(f"✅ Прокси работает на http://localhost:{proxy_port}")
        
        # Выводим информацию
        print("\n" + "=" * 50)
        print("🎉 СИСТЕМА УСПЕШНО ЗАПУЩЕНА!")
        print("=" * 50)
        print(f"🌐 Прокси (веб-интерфейс): http://localhost:{proxy_port}")
        print(f"🔧 API: http://localhost:{api_port}")
        print("\n📋 ЭНДПОИНТЫ API:")
        print(f"   • GET  http://localhost:{api_port}/api/status")
        print(f"   • GET  http://localhost:{api_port}/api/health")
        print(f"   • POST http://localhost:{api_port}/api/generate-model")
        print("\n📁 ЛОГИ:")
        print("   • API: api.log")
        print("   • Прокси: proxy.log")
        print("\n🛑 Для остановки нажмите Ctrl+C")
        print("=" * 50)
        
        # Ждем завершения
        try:
            while True:
                time.sleep(1)
                # Проверяем, что процессы еще работают
                for i, proc in enumerate(processes):
                    if proc.poll() is not None:
                        print(f"\n⚠️  Процесс {i+1} завершился неожиданно")
                        cleanup_handler()
                        return 1
        except KeyboardInterrupt:
            print("\n\n🛑 Получен сигнал прерывания...")
            cleanup_handler()
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        cleanup_handler()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())