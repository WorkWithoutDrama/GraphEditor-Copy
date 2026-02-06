#!/usr/bin/env python3
"""
Немедленный тест генерации JSON через API
"""

import urllib.request
import json
import sys

def test_generate():
    print("🚀 НЕМЕДЛЕННЫЙ ТЕСТ ГЕНЕРАЦИИ JSON")
    print("=" * 60)
    
    # Порт API из файла
    try:
        with open('api_port.txt', 'r') as f:
            api_port = f.read().strip()
    except:
        api_port = "5011"  # Значение по умолчанию из предыдущего вывода
    
    print(f"🔧 API порт: {api_port}")
    
    # Тестовый запрос
    test_text = "Пользователь регистрируется в системе"
    
    try:
        url = f"http://localhost:{api_port}/api/generate-model"
        data = json.dumps({
            "text": test_text,
            "provider": "ollama"
        }).encode('utf-8')
        
        print(f"📤 Отправляю запрос: {test_text}")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        # Таймаут 30 секунд
        import socket
        socket.setdefaulttimeout(30)
        
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                print(f"✅ Ответ получен (статус: {response.status})")
                
                if result.get("success"):
                    model = result.get("model", {})
                    
                    print("\n🎉 СГЕНЕРИРОВАННЫЙ JSON:")
                    print("=" * 60)
                    print(json.dumps(model, ensure_ascii=False, indent=2))
                    print("=" * 60)
                    
                    print(f"\n📊 СТАТИСТИКА:")
                    print(f"   • Действий: {len(model.get('model_actions', []))}")
                    print(f"   • Объектов: {len(model.get('model_objects', []))}")
                    print(f"   • Связей: {len(model.get('model_connections', []))}")
                    
                    # Сохраняем в файл для проверки
                    with open('generated_now.json', 'w', encoding='utf-8') as f:
                        json.dump(model, f, ensure_ascii=False, indent=2)
                    print(f"\n💾 Сохранено в: generated_now.json")
                    
                else:
                    print(f"❌ Ошибка генерации: {result.get('error', 'Неизвестная ошибка')}")
            else:
                print(f"❌ Ошибка API: {response.status}")
                
    except urllib.error.URLError as e:
        print(f"❌ Ошибка сети: {e}")
        print("   Возможно, API сервер не запущен")
        print("   Запустите: python3 api_ultra_simple.py")
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generate()