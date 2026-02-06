#!/usr/bin/env python3
"""Тест генерации модели через API"""

import json
import requests
import sys

def test_api_generation():
    """Тестируем генерацию модели через API"""
    
    print("🧪 Тест генерации модели через API")
    print("=" * 50)
    
    # Тестовый текст
    test_text = "Система регистрации и авторизации пользователей"
    
    print(f"Отправляю запрос с текстом: {test_text}")
    
    try:
        # Отправляем запрос к API
        response = requests.post(
            "http://localhost:5009/api/generate-model",
            json={"text": test_text},
            timeout=30
        )
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Ответ API: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
            
            # Проверяем структуру
            if 'model' in result:
                model = result['model']
                
                print("\n📋 Анализ структуры модели:")
                print("-" * 30)
                
                # Проверяем новую структуру
                has_new_structure = all(key in model for key in ['model_actions', 'model_objects', 'model_connections'])
                has_old_structure = all(key in model for key in ['init_states', 'final_states'])
                
                if has_new_structure:
                    print("✅ НОВАЯ структура обнаружена!")
                    print(f"   Действий: {len(model.get('model_actions', []))}")
                    print(f"   Объектов: {len(model.get('model_objects', []))}")
                    print(f"   Связей: {len(model.get('model_connections', []))}")
                    
                    # Проверяем конкретные поля
                    if model.get('model_actions'):
                        action = model['model_actions'][0]
                        if 'action_id' in action and 'action_name' in action and 'action_links' in action:
                            print("   ✅ Действия имеют правильную структуру")
                        else:
                            print("   ❌ Действия имеют неправильную структуру")
                            
                elif has_old_structure:
                    print("❌ СТАРАЯ структура обнаружена!")
                    print("   API возвращает старый формат")
                    
                    # Показываем пример старой структуры
                    print("\n   Пример старой структуры:")
                    for key in list(model.keys())[:3]:
                        print(f"   - {key}")
                else:
                    print("⚠️  Неизвестная структура")
                    print(f"   Ключи: {list(model.keys())}")
                    
            else:
                print("❌ В ответе нет поля 'model'")
                print(f"   Ответ: {result}")
                
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"   Текст: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")

def test_fallback_model():
    """Тестируем fallback модель"""
    
    print("\n" + "=" * 50)
    print("🧪 Тест fallback модели")
    print("=" * 50)
    
    try:
        # Импортируем LLMClient из api.py
        sys.path.insert(0, '.')
        from api import LLMClient
        
        client = LLMClient(provider="ollama")
        fallback = client._get_fallback_model()
        
        print("Fallback модель:")
        print(json.dumps(fallback, indent=2, ensure_ascii=False))
        
        # Проверяем структуру
        print("\n📋 Структура fallback модели:")
        if all(key in fallback for key in ['model_actions', 'model_objects', 'model_connections']):
            print("✅ Fallback модель имеет НОВУЮ структуру")
        else:
            print("❌ Fallback модель имеет старую структуру")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_api_generation()
    test_fallback_model()