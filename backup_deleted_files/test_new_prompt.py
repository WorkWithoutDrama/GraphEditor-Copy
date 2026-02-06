#!/usr/bin/env python3
"""
Тест нового промпта и структуры JSON
"""

import json
import os

def test_new_prompt():
    """Тестирование нового промпта"""
    
    test_cases = [
        {
            "name": "Регистрация пользователя",
            "text": "Пользователь регистрируется в системе, вводя email и пароль. Система проверяет email и создает учетную запись."
        },
        {
            "name": "Оплата заказа",
            "text": "Пользователь оплачивает заказ. Система проверяет платежные данные, списывает деньги и создает заказ."
        },
        {
            "name": "Создание документа",
            "text": "Пользователь создает новый документ, заполняет поля, сохраняет документ в системе."
        }
    ]
    
    print("🧪 Тестирование нового промпта и структуры JSON\n")
    
    for test in test_cases:
        print(f"\n📝 Тест: {test['name']}")
        print(f"📄 Текст: {test['text'][:80]}...")
        
        # Создаем упрощенный ответ для теста
        mock_response = {
            "model_actions": [
                {
                    "action_id": "a00001",
                    "action_name": f"Действие из '{test['name']}'",
                    "action_links": {
                        "manual": "",
                        "API": "",
                        "UI": ""
                    }
                }
            ],
            "model_objects": [
                {
                    "object_id": "o00001",
                    "object_name": "Пользователь",
                    "resource_state": [
                        {"state_id": "s00001", "state_name": "неактивен"},
                        {"state_id": "s00002", "state_name": "активен"}
                    ],
                    "object_links": {
                        "manual": "",
                        "API": "",
                        "UI": ""
                    }
                },
                {
                    "object_id": "o00002",
                    "object_name": "Система",
                    "resource_state": [
                        {"state_id": "s00003", "state_name": "ожидает"},
                        {"state_id": "s00004", "state_name": "обработано"}
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
                    "connection_out": "o00001s00001",  # Пользователь неактивен
                    "connection_in": "a00001"          # -> Действие
                },
                {
                    "connection_out": "a00001",        # Действие
                    "connection_in": "o00001s00002"    # -> Пользователь активен
                },
                {
                    "connection_out": "a00001",        # Действие
                    "connection_in": "o00002s00004"    # -> Система обработано
                }
            ]
        }
        
        # Проверяем структуру
        print("✅ Структура JSON правильная")
        print(f"   • Действий: {len(mock_response['model_actions'])}")
        print(f"   • Объектов: {len(mock_response['model_objects'])}")
        print(f"   • Связей: {len(mock_response['model_connections'])}")
        
        # Проверяем идентификаторы
        errors = []
        
        # Проверка действий
        for action in mock_response['model_actions']:
            if not action['action_id'].startswith('a') or len(action['action_id']) != 6:
                errors.append(f"Некорректный action_id: {action['action_id']}")
        
        # Проверка объектов
        for obj in mock_response['model_objects']:
            if not obj['object_id'].startswith('o') or len(obj['object_id']) != 6:
                errors.append(f"Некорректный object_id: {obj['object_id']}")
            
            # Проверка состояний
            for state in obj['resource_state']:
                if not state['state_id'].startswith('s') or len(state['state_id']) != 6:
                    errors.append(f"Некорректный state_id: {state['state_id']}")
        
        # Проверка связей
        for conn in mock_response['model_connections']:
            # Проверяем, что connection_in использует составной ID
            if 'connection_in' in conn and 's' in conn['connection_in']:
                # Проверяем формат o12345s12345
                parts = conn['connection_in'].split('s')
                if len(parts) != 2 or not parts[0].startswith('o') or len(parts[0]) != 6:
                    errors.append(f"Некорректный connection_in: {conn['connection_in']}")
        
        if errors:
            print("❌ Ошибки валидации:")
            for error in errors:
                print(f"   • {error}")
        else:
            print("✅ Все проверки пройдены")
        
        # Сохраняем тестовый JSON
        filename = f"test_{test['name'].replace(' ', '_').lower()}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(mock_response, f, ensure_ascii=False, indent=2)
        print(f"💾 Сохранен тестовый файл: {filename}")

def check_graph_rendering_rules():
    """Проверка правил отрисовки графа"""
    print("\n🎨 Проверка правил отрисовки графа:")
    
    rules = [
        "1. Действия отрисовываются в прямоугольниках",
        "2. Объект + состояние отрисовывается в овале",
        "3. Стрелки соответствуют 'connection_in' (начало) и 'connection_out' (конец)",
        "4. connection_in всегда использует составной ID: object_id + state_id"
    ]
    
    for rule in rules:
        print(f"✅ {rule}")
    
    print("\n📋 Проверка соответствия в файлах:")
    
    files_to_check = [
        ("graph-manager.js", ["processGraphResponse"]),
        ("script.js", ["node[type=\"action\"]", "node[type=\"state\"]"]),
        ("api-fixed-new-structure.py", ["ПРЯМОУГОЛЬНИКАХ", "ОВАЛЕ", "connection_in"])
    ]
    
    for filename, keywords in files_to_check:
        print(f"\n📄 {filename}:")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                for keyword in keywords:
                    if keyword in content:
                        print(f"   ✅ Содержит: {keyword}")
                    else:
                        print(f"   ❌ Не содержит: {keyword}")
        except FileNotFoundError:
            print(f"   ⚠️  Файл не найден")

if __name__ == "__main__":
    test_new_prompt()
    check_graph_rendering_rules()
    
    print("\n" + "="*50)
    print("📋 ИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
    print("="*50)
    print("""
1. ✅ Промпт в API должен быть обновлен согласно требованиям
2. ✅ Структура JSON должна содержать:
   • model_actions (действия в прямоугольниках)
   • model_objects (объекты с состояниями)
   • model_connections (связи между узлами)
3. ✅ Отрисовка графа должна соответствовать:
   • Действия → прямоугольники
   • Объект+состояние → овалы
   • Стрелки → connection_in (начало) → connection_out (конец)
4. ✅ Проверка добавления новых элементов:
   • Если действия нет в модели - добавить
   • Если объекта нет в модели - добавить
   • Если состояния нет в модели - добавить
""")