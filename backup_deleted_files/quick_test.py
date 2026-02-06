#!/usr/bin/env python3
"""
Быстрый тест генерации модели
"""

import json
import urllib.request

# Простой запрос
text = "Пользователь регистрируется в системе"

print(f"📝 Текст: {text}")
print("📤 Отправляю запрос...")

try:
    url = "http://localhost:5005/api/generate-model"
    data = json.dumps({"text": text, "provider": "ollama"}).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode('utf-8'))
        
        print(f"✅ Статус: {response.status}")
        print(f"✅ Успех: {result.get('success')}")
        
        if result.get('success'):
            model = result.get('model', {})
            print("\n📊 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
            print(json.dumps(model, ensure_ascii=False, indent=2))
            
            # Анализ структуры
            print("\n🔍 АНАЛИЗ СТРУКТУРЫ:")
            
            # Проверяем действия
            actions = model.get('model_actions', [])
            print(f"   Действий: {len(actions)}")
            for action in actions:
                print(f"   • {action.get('action_name')} (ID: {action.get('action_id')})")
            
            # Проверяем объекты
            objects = model.get('model_objects', [])
            print(f"\n   Объектов: {len(objects)}")
            for obj in objects:
                print(f"   • {obj.get('object_name')} (ID: {obj.get('object_id')})")
                states = obj.get('resource_state', [])
                for state in states:
                    if state.get('state_name') != 'null':
                        print(f"     ◦ {state.get('state_name')} (ID: {state.get('state_id')})")
            
            # Проверяем связи
            connections = model.get('model_connections', [])
            print(f"\n   Связей: {len(connections)}")
            for conn in connections:
                print(f"   • {conn.get('connection_out')} → {conn.get('connection_in')}")
                
except Exception as e:
    print(f"❌ Ошибка: {e}")