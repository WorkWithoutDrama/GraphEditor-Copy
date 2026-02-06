#!/usr/bin/env python3
"""Упрощенный тест API генерации"""

import json
import sys

def test_api_response():
    """Тестируем, что возвращает API"""
    
    print("🧪 Проверка API генерации модели")
    print("=" * 50)
    
    # Импортируем напрямую из api.py
    sys.path.insert(0, '.')
    
    try:
        from api import LLMClient, SystemModelHandler
        
        # Тест 1: Проверяем промпт
        print("\n1. Проверка промпта для LLM:")
        client = LLMClient(provider="ollama")
        
        # Получаем промпт (через рефлексию)
        import inspect
        source = inspect.getsource(client._generate_with_ollama)
        
        # Ищем ключевые слова в промпте
        required_keywords = [
            'model_actions',
            'model_objects', 
            'model_connections',
            'action_links',
            'object_links',
            'connection_out',
            'connection_in'
        ]
        
        print("   Ключевые слова в промпте:")
        for keyword in required_keywords:
            if keyword in source:
                print(f"   ✅ {keyword}")
            else:
                print(f"   ❌ {keyword} - ОТСУТСТВУЕТ!")
        
        # Тест 2: Проверяем fallback модель
        print("\n2. Проверка fallback модели:")
        fallback = client._get_fallback_model()
        
        print("   Структура fallback модели:")
        if all(key in fallback for key in ['model_actions', 'model_objects', 'model_connections']):
            print("   ✅ Имеет новую структуру")
            
            # Проверяем поля
            actions = fallback.get('model_actions', [])
            if actions and 'action_links' in actions[0]:
                print("   ✅ Действия имеют action_links")
            else:
                print("   ❌ Действия не имеют action_links")
                
        else:
            print("   ❌ Имеет старую структуру")
            print(f"   Ключи: {list(fallback.keys())}")
        
        # Тест 3: Проверяем валидацию
        print("\n3. Проверка валидации модели:")
        
        # Создаем тестовую модель новой структуры
        test_new_model = {
            "model_actions": [
                {
                    "action_id": "a12345",
                    "action_name": "Тест",
                    "action_links": {"manual": "", "API": "", "UI": ""}
                }
            ],
            "model_objects": [
                {
                    "object_id": "o12345",
                    "object_name": "Тест",
                    "resource_state": [{"state_id": "s00000", "state_name": "null"}],
                    "object_links": {"manual": "", "API": "", "UI": ""}
                }
            ],
            "model_connections": [
                {
                    "connection_out": "a12345",
                    "connection_in": "o12345s12345"
                }
            ]
        }
        
        # Создаем тестовую модель старой структуры
        test_old_model = {
            "Регистрация": {
                "init_states": [],
                "final_states": ["Пользователь: состояние 00000"]
            }
        }
        
        # Проверяем валидацию
        is_new_valid = client._validate_model_structure(test_new_model)
        is_old_valid = client._validate_model_structure(test_old_model)
        
        print(f"   Новая структура валидна: {'✅' if is_new_valid else '❌'}")
        print(f"   Старая структура валидна: {'✅' if is_old_valid else '❌'}")
        
        # Тест 4: Проверяем обработку ответа LLM
        print("\n4. Проверка обработки ответа LLM:")
        
        # Симулируем ответ LLM с новой структурой
        llm_response_new = '{\n  "model_actions": [\n    {\n      "action_id": "a12345",\n      "action_name": "Тест",\n      "action_links": {"manual": "", "API": "", "UI": ""}\n    }\n  ],\n  "model_objects": [\n    {\n      "object_id": "o12345",\n      "object_name": "Тест",\n      "resource_state": [{"state_id": "s00000", "state_name": "null"}],\n      "object_links": {"manual": "", "API": "", "UI": ""}\n    }\n  ],\n  "model_connections": []\n}'
        
        # Симулируем ответ LLM со старой структурой  
        llm_response_old = '{\n  "Регистрация": {\n    "init_states": [],\n    "final_states": ["Пользователь: состояние 00000"]\n  }\n}'
        
        print("   Симуляция ответа LLM:")
        print("   - Новая структура присутствует в промпте")
        print("   - Но LLM может вернуть старую")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_response()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Диагностика завершена")
        print("\n🎯 ВЫВОДЫ:")
        print("1. Промпт ДОЛЖЕН содержать новую структуру")
        print("2. Fallback модель ДОЛЖНА быть новой структуры")
        print("3. Но LLM может игнорировать промпт и возвращать старую структуру")
        print("\n🔧 РЕШЕНИЕ:")
        print("Нужно УСИЛИТЬ промпт и ОБРАБАТЫВАТЬ ответ LLM:")
        print("- Явно требовать новую структуру")
        print("- Отвергать старую структуру")
        print("- Использовать fallback если LLM вернул старое")
    else:
        print("❌ Диагностика не удалась")