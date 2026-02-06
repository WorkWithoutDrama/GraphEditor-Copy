#!/usr/bin/env python3
"""Тест валидации модели с пустыми action_links и object_links"""

import json

# Имитируем валидацию из api.py
def validate_model_structure(model):
    """Упрощенная версия валидации из api.py"""
    
    # Проверяем действия
    for action in model.get('model_actions', []):
        required_action_keys = ['action_id', 'action_name', 'action_links']
        for key in required_action_keys:
            if key not in action:
                print(f"❌ Действие не содержит ключа: {key}")
                return False
        
        # Проверяем action_links
        if not isinstance(action['action_links'], dict):
            print("❌ action_links должен быть словарем")
            return False
        
        # Проверяем наличие обязательных ключей в action_links
        required_link_keys = ['manual', 'API', 'UI']
        for key in required_link_keys:
            if key not in action['action_links']:
                print(f"❌ action_links не содержит ключа: {key}")
                return False
    
    # Проверяем объекты
    for obj in model.get('model_objects', []):
        required_object_keys = ['object_id', 'object_name', 'resource_state', 'object_links']
        for key in required_object_keys:
            if key not in obj:
                print(f"❌ Объект не содержит ключа: {key}")
                return False
        
        # Проверяем object_links
        if not isinstance(obj['object_links'], dict):
            print("❌ object_links должен быть словарем")
            return False
        
        # Проверяем наличие обязательных ключей в object_links
        required_link_keys = ['manual', 'API', 'UI']
        for key in required_link_keys:
            if key not in obj['object_links']:
                print(f"❌ object_links не содержит ключа: {key}")
                return False
    
    return True

# Тест 1: Правильная модель с пустыми полями
test_model_1 = {
    "model_actions": [
        {
            "action_id": "a1234567890123",
            "action_name": "Тестовое действие",
            "action_links": {
                "manual": "",
                "API": "",
                "UI": ""
            }
        }
    ],
    "model_objects": [
        {
            "object_id": "o12345",
            "object_name": "Тестовый объект",
            "resource_state": [
                {"state_id": "s00000", "state_name": "null"},
                {"state_id": "s12345", "state_name": "активен"}
            ],
            "object_links": {
                "manual": "",
                "API": "",
                "UI": ""
            }
        }
    ],
    "model_connections": [
        {
            "connection_out": "a1234567890123",
            "connection_in": "o12345s12345"
        }
    ]
}

# Тест 2: Модель без action_links (должна не пройти)
test_model_2 = {
    "model_actions": [
        {
            "action_id": "a1234567890123",
            "action_name": "Тестовое действие"
            # Нет action_links
        }
    ],
    "model_objects": [
        {
            "object_id": "o12345",
            "object_name": "Тестовый объект",
            "resource_state": [
                {"state_id": "s00000", "state_name": "null"}
            ],
            "object_links": {
                "manual": "",
                "API": "",
                "UI": ""
            }
        }
    ],
    "model_connections": []
}

# Тест 3: Модель с неполным action_links (должна не пройти)
test_model_3 = {
    "model_actions": [
        {
            "action_id": "a1234567890123",
            "action_name": "Тестовое действие",
            "action_links": {
                "manual": "",
                "API": ""
                # Нет UI
            }
        }
    ],
    "model_objects": [
        {
            "object_id": "o12345",
            "object_name": "Тестовый объект",
            "resource_state": [
                {"state_id": "s00000", "state_name": "null"}
            ],
            "object_links": {
                "manual": "",
                "API": "",
                "UI": ""
            }
        }
    ],
    "model_connections": []
}

print("🧪 Тестирование валидации модели")
print("=" * 50)

print("\nТест 1: Правильная модель с пустыми полями")
if validate_model_structure(test_model_1):
    print("✅ Тест пройден")
else:
    print("❌ Тест не пройден")

print("\nТест 2: Модель без action_links")
if not validate_model_structure(test_model_2):
    print("✅ Тест пройден (ожидалась ошибка)")
else:
    print("❌ Тест не пройден (ожидалась ошибка)")

print("\nТест 3: Модель с неполным action_links")
if not validate_model_structure(test_model_3):
    print("✅ Тест пройден (ожидалась ошибка)")
else:
    print("❌ Тест не пройден (ожидалась ошибка)")

print("\n" + "=" * 50)
print("Пример правильной модели:")
print(json.dumps(test_model_1, indent=2, ensure_ascii=False))